"""Advertiser routes for Day Shift Marketplace."""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Request

from .deps import get_conn, get_current_user, get_optional_user
from .models import TIERS, AD_TIERS, BoostBody

api = APIRouter()


@api.post("/advertiser/agreement")
def accept_advertiser_agreement(current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET advertiser_agreement_accepted = TRUE, is_advertiser = TRUE WHERE id = %s RETURNING id",
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
                        "description": f"{tier_info['duration_days']}-day visibility boost on Day Shift",
                    },
                    "unit_amount": tier_info["price"] * 100,  # Stripe uses cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{origin}/boost?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{origin}/boost?canceled=1",
            customer_email=None,  # Don't prefill — let customer enter their own
            metadata={
                "boost_id": boost["id"],
                "user_id": current_user["id"],
                "video_id": body.video_id,
                "tier": body.tier,
            },
        )
    except Exception as e:
        print(f"[Stripe] checkout.session.create failed: {e}")
        # Clean up the pending boost record since payment failed
        cur.execute("DELETE FROM post_boosts WHERE id = %s", (boost["id"],))
        conn.commit()
        cur.close()
        conn.close()
        raise HTTPException(500, f"Payment processing failed: {str(e)[:200]}")

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


@api.post("/advertiser/free-boost/{video_id}")
def create_free_promo_boost(video_id: int, current_user=Depends(get_current_user)):
    """Apply a free boost using a redeemed promo code."""
    conn = get_conn()
    cur = conn.cursor()

    # Verify video belongs to user
    cur.execute("SELECT user_id, title FROM videos WHERE id = %s", (video_id,))
    vid = cur.fetchone()
    if not vid:
        cur.close()
        conn.close()
        raise HTTPException(404, "Post not found")
    if vid["user_id"] != current_user["id"]:
        cur.close()
        conn.close()
        raise HTTPException(403, "Can only boost your own posts")

    # Check for existing active boost
    cur.execute("SELECT id FROM post_boosts WHERE video_id = %s AND status = 'active' AND end_date > NOW()", (video_id,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(400, "This post already has an active boost")

    # Check for unused promo redemption with boost_tier
    cur.execute(
        """SELECT pr.id as redemption_id, pr.boost_used, pc.code, pc.boost_tier, pc.boost_days
           FROM promo_redemptions pr
           JOIN promo_codes pc ON pr.promo_code_id = pc.id
           WHERE pr.user_id = %s AND pc.boost_tier IS NOT NULL AND pc.boost_tier != ''
           AND (pr.boost_used IS NULL OR pr.boost_used = FALSE)
           ORDER BY pr.redeemed_at ASC
           LIMIT 1""",
        (current_user["id"],),
    )
    redemption = cur.fetchone()
    if not redemption:
        # Fallback: check for welcome boost (new user signup bonus)
        cur.execute("SELECT welcome_boost_available FROM users WHERE id = %s", (current_user["id"],))
        user_row = cur.fetchone()
        if user_row and user_row["welcome_boost_available"]:
            tier = "boost"
            tier_info = TIERS.get(tier, TIERS["boost"])
            duration = 7  # 1 week welcome boost
            now = datetime.now(timezone.utc)
            end = now + timedelta(days=duration)
            cur.execute(
                """INSERT INTO post_boosts (video_id, user_id, tier, status, payment_status, admin_approved, start_date, end_date, stripe_session_id)
                   VALUES (%s, %s, %s, 'active', 'paid', TRUE, %s, %s, %s) RETURNING *""",
                (video_id, current_user["id"], tier, now, end, "WELCOME"),
            )
            boost = dict(cur.fetchone())
            cur.execute("UPDATE users SET welcome_boost_available = FALSE WHERE id = %s", (current_user["id"],))
            conn.commit()
            cur.close()
            conn.close()
            for k in ("created_at", "start_date", "end_date"):
                if boost.get(k):
                    boost[k] = boost[k].isoformat()
            return {
                "ok": True,
                "message": f"Welcome boost activated! Your post is boosted for {duration} days.",
                "boost": boost,
            }
        cur.close()
        conn.close()
        raise HTTPException(400, "No free boost available. Sign up with a promo code to get one!")

    redemption = dict(redemption)
    tier = redemption["boost_tier"]
    tier_info = TIERS.get(tier, TIERS["boost"])
    duration = redemption["boost_days"] or tier_info["duration_days"]

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=duration)

    # Create and activate the free boost
    cur.execute(
        """INSERT INTO post_boosts (video_id, user_id, tier, status, payment_status, admin_approved, start_date, end_date, stripe_session_id)
           VALUES (%s, %s, %s, 'active', 'paid', TRUE, %s, %s, %s) RETURNING *""",
        (video_id, current_user["id"], tier, now, end, f"PROMO:{redemption['code']}"),
    )
    boost = dict(cur.fetchone())

    # Mark redemption as used
    cur.execute(
        "UPDATE promo_redemptions SET boost_used = TRUE WHERE id = %s",
        (redemption["redemption_id"],),
    )
    conn.commit()
    cur.close()
    conn.close()

    for k in ("created_at", "start_date", "end_date"):
        if boost.get(k):
            boost[k] = boost[k].isoformat()

    return {
        "ok": True,
        "message": f"Free {tier_info['name']} boost activated for {duration} days!",
        "boost": boost,
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


@api.get("/advertiser/analytics")
def get_analytics(current_user=Depends(get_current_user)):
    # Gate: admins always get access; subscribers need premium/enterprise
    conn = get_conn()
    cur = conn.cursor()
    is_admin = current_user.get("is_admin", False)
    if not is_admin:
        cur.execute(
            """SELECT tier, status FROM advertiser_subscriptions
               WHERE user_id = %s AND status = 'active'
               ORDER BY created_at DESC LIMIT 1""",
            (current_user["id"],),
        )
        sub = cur.fetchone()
        if not sub or sub["tier"] not in ("premium", "enterprise"):
            cur.close()
            conn.close()
            raise HTTPException(403, "Full analytics requires a Premium or Enterprise advertising subscription")
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


# ── Advertising Subscription Routes ──────────────────────────────────────────

@api.get("/advertiser/ad-tiers")
def list_ad_tiers():
    """Public tier definitions for advertising subscriptions."""
    return AD_TIERS


@api.get("/advertiser/subscription-status")
def get_ad_subscription_status(current_user=Depends(get_current_user)):
    """Check if user has an active advertising subscription."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM advertiser_subscriptions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1""",
        (current_user["id"],),
    )
    sub = cur.fetchone()
    cur.close()
    conn.close()
    if not sub:
        return {"active": False, "tier": None}
    return {
        "active": sub.get("tier") in ("business", "premium", "enterprise") and sub.get("status", "active") == "active",
        "tier": sub.get("tier"),
        "boosts_per_month": AD_TIERS.get(sub.get("tier", ""), {}).get("boosts_per_month", 0),
    }
