"""Advertiser routes for Day Shift Marketplace."""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Request

from .deps import get_conn, get_current_user, get_optional_user
from .models import TIERS, BoostBody

api = APIRouter()


@api.post("/advertiser/agreement")
def accept_advertiser_agreement(current_user=Depends(get_current_user)):
    if not current_user.get("is_advertiser"):
        raise HTTPException(403, "Not an advertiser")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET advertiser_agreement_accepted = TRUE WHERE id = %s RETURNING id",
        (current_user["id"],),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True, "advertiser_agreement_accepted": True}


@api.get("/advertiser/tiers")
def list_tiers():
    """Public tier definitions — visible to all."""
    return TIERS


@api.get("/advertiser/subscription")
def get_subscription(current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM advertiser_subscriptions WHERE user_id = %s", (current_user["id"],))
    sub = cur.fetchone()
    if not sub:
        # Auto-create free tier
        cur.execute("INSERT INTO advertiser_subscriptions (user_id, tier, free_boost_used) VALUES (%s, 'free', FALSE) RETURNING *",
                    (current_user["id"],))
        sub = cur.fetchone()
        conn.commit()
    conn.commit()
    cur.close()
    conn.close()
    result = dict(sub)
    if result.get("start_date"): result["start_date"] = result["start_date"].isoformat()
    if result.get("end_date"): result["end_date"] = result["end_date"].isoformat()
    if result.get("created_at"): result["created_at"] = result["created_at"].isoformat()
    result["tiers"] = TIERS
    return result


@api.get("/advertiser/boosts")
def list_boosts(current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT pb.*, v.title as video_title, v.thumbnail_url
           FROM post_boosts pb
           LEFT JOIN videos v ON pb.video_id = v.id
           WHERE pb.user_id = %s
           ORDER BY pb.created_at DESC""",
        (current_user["id"],),
    )
    boosts = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for b in boosts:
        for k in ("created_at", "start_date", "end_date"):
            if b.get(k): b[k] = b[k].isoformat()
    return boosts


@api.post("/advertiser/boosts")
def create_boost(body: BoostBody, request: Request, current_user=Depends(get_current_user)):
    import stripe
    if not current_user.get("is_advertiser"):
        raise HTTPException(403, "You must be an advertiser to boost posts")
    if body.tier not in TIERS:
        raise HTTPException(400, f"Invalid tier. Choose from: {list(TIERS.keys())}")

    conn = get_conn()
    cur = conn.cursor()

    # Verify the video belongs to this user
    cur.execute("SELECT user_id, title FROM videos WHERE id = %s", (body.video_id,))
    vid = cur.fetchone()
    if not vid:
        raise HTTPException(404, "Post not found")
    if vid["user_id"] != current_user["id"]:
        raise HTTPException(403, "Can only boost your own posts")

    # Check for existing active boost on this post
    cur.execute("SELECT id FROM post_boosts WHERE video_id = %s AND status = 'active' AND end_date > NOW()", (body.video_id,))
    if cur.fetchone():
        raise HTTPException(400, "This post already has an active boost")

    tier_info = TIERS[body.tier]

    # Create boost record
    try:
        cur.execute(
            """INSERT INTO post_boosts (video_id, user_id, tier, status, payment_status)
               VALUES (%s, %s, %s, 'pending', 'unpaid') RETURNING *""",
            (body.video_id, current_user["id"], body.tier),
        )
        boost = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(500, "Internal error — please try again")

    # Get the origin for Stripe success/cancel URLs
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    origin = f"https://{custom_domain}" if custom_domain else (request.headers.get("origin") or "https://day-shift.workshop.build")

    # Create Stripe Checkout Session
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"{tier_info['name']} Boost — {vid['title'] or 'Your Post'}",
                        "description": f"{tier_info['duration']} visibility boost on Day Shift",
                    },
                    "unit_amount": tier_info["price"] * 100,  # Stripe uses cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{origin}/boost?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/boost?canceled=1",
            metadata={
                "boost_id": boost["id"],
                "user_id": current_user["id"],
                "video_id": body.video_id,
                "tier": body.tier,
            },
        )
    except Exception as e:
        cur.close()
        conn.close()
        raise HTTPException(500, "Payment processing failed. Please try again.")

    # Store Stripe session ID
    cur.execute(
        "UPDATE post_boosts SET stripe_session_id = %s WHERE id = %s",
        (checkout_session.id, boost["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "id": boost["id"],
        "tier": body.tier,
        "price": tier_info["price"],
        "stripe_checkout_url": checkout_session.url,
        "stripe_session_id": checkout_session.id,
    }


@api.get("/advertiser/boosts/{boost_id}/status")
def get_boost_payment_status(boost_id: int, current_user=Depends(get_current_user)):
    """Check boost payment status after Stripe redirect."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM post_boosts WHERE id = %s AND user_id = %s", (boost_id, current_user["id"]))
    boost = cur.fetchone()
    cur.close()
    conn.close()
    if not boost:
        raise HTTPException(404, "Boost not found")
    boost = dict(boost)
    if boost.get("created_at"):
        boost["created_at"] = boost["created_at"].isoformat()
    return boost


@api.delete("/advertiser/boosts/{boost_id}")
def cancel_boost(boost_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM post_boosts WHERE id = %s AND user_id = %s", (boost_id, current_user["id"]))
    boost = cur.fetchone()
    if not boost:
        raise HTTPException(404, "Boost not found")
    boost = dict(boost)
    if boost["status"] not in ("pending",):
        raise HTTPException(400, "Can only cancel pending boosts")
    cur.execute("UPDATE post_boosts SET status = 'rejected' WHERE id = %s", (boost_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}


@api.post("/advertiser/portal")
def customer_portal(request: Request, current_user=Depends(get_current_user)):
    """Create a Stripe Customer Portal session for managing payment methods."""
    if not os.environ.get("STRIPE_SECRET_KEY"):
        raise HTTPException(500, "Stripe is not configured")
    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    origin = f"https://{custom_domain}" if custom_domain else (request.headers.get("origin") or "https://day-shift.workshop.build")

    try:
        session = stripe.billing_portal.Session.create(
            customer=None,  # No customer ID stored yet — could be added later
            return_url=f"{origin}/profile",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(500, f"Stripe portal error: {str(e)}")


@api.get("/advertiser/analytics")
def get_analytics(current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    uid = current_user["id"]
    # Overall stats
    cur.execute(
        """SELECT COALESCE(SUM(views), 0) as total_views,
                  COALESCE(SUM(profile_clicks), 0) as total_clicks,
                  COALESCE(SUM(match_requests), 0) as total_matches
           FROM post_analytics pa
           JOIN videos v ON pa.video_id = v.id
           WHERE v.user_id = %s""",
        (uid,),
    )
    stats = dict(cur.fetchone())

    # Active boosts
    cur.execute(
        """SELECT pb.*, v.title as video_title
           FROM post_boosts pb JOIN videos v ON pb.video_id = v.id
           WHERE pb.user_id = %s AND pb.status = 'active' AND pb.end_date > NOW()""",
        (uid,),
    )
    active_boosts = [dict(r) for r in cur.fetchall()]
    for b in active_boosts:
        for k in ("start_date", "end_date", "created_at"):
            if b.get(k): b[k] = b[k].isoformat()

    # Per-post stats (last 30 days)
    cur.execute(
        """SELECT v.id as video_id, v.title, v.thumbnail_url,
                  COALESCE(SUM(pa.views), 0) as views,
                  COALESCE(SUM(pa.profile_clicks), 0) as clicks,
                  COALESCE(SUM(pa.match_requests), 0) as matches
           FROM videos v
           LEFT JOIN post_analytics pa ON pa.video_id = v.id AND pa.date > NOW() - INTERVAL '30 days'
           WHERE v.user_id = %s
           GROUP BY v.id
           ORDER BY views DESC""",
        (uid,),
    )
    per_post = [dict(r) for r in cur.fetchall()]

    cur.close()
    conn.close()
    return {
        "total_views": stats["total_views"],
        "total_clicks": stats["total_clicks"],
        "total_matches": stats["total_matches"],
        "active_boosts": active_boosts,
        "per_post": per_post,
    }


@api.post("/advertiser/analytics/view")
def track_view(body: dict, current_user=Depends(get_optional_user)):
    video_id = body.get("video_id")
    if not video_id:
        return {"ok": True}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO post_analytics (video_id, date, views)
        VALUES (%s, CURRENT_DATE, 1)
        ON CONFLICT (video_id, date) DO UPDATE SET views = post_analytics.views + 1
    """, (video_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}


@api.post("/advertiser/analytics/click")
def track_click(body: dict, current_user=Depends(get_optional_user)):
    video_id = body.get("video_id")
    if not video_id:
        return {"ok": True}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO post_analytics (video_id, date, profile_clicks)
        VALUES (%s, CURRENT_DATE, 1)
        ON CONFLICT (video_id, date) DO UPDATE SET profile_clicks = post_analytics.profile_clicks + 1
    """, (video_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}


@api.post("/advertiser/analytics/match")
def track_match_analytics(body: dict, current_user=Depends(get_current_user)):
    video_id = body.get("video_id")
    if not video_id:
        return {"ok": True}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO post_analytics (video_id, date, match_requests)
        VALUES (%s, CURRENT_DATE, 1)
        ON CONFLICT (video_id, date) DO UPDATE SET match_requests = post_analytics.match_requests + 1
    """, (video_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}
