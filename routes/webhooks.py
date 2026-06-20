"""Webhook routes for Day Shift Marketplace."""
import os

from fastapi import APIRouter, HTTPException, Request

from .deps import get_conn
from .models import TIERS

api = APIRouter()


@api.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for payment confirmation."""
    import stripe
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if webhook_secret and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception:
            raise HTTPException(400, "Webhook verification failed")
    elif not webhook_secret:
        # No webhook secret configured — reject in production, allow in dev
        if os.environ.get("WORKSHOP_CUSTOM_DOMAIN"):
            raise HTTPException(500, "Webhook secret not configured")
        # Dev mode: parse payload directly
        try:
            event = stripe.Event.construct_from(await request.json(), stripe.api_key)
        except Exception:
            raise HTTPException(400, "Invalid payload")
    else:
        raise HTTPException(400, "Missing stripe-signature header")

    # Handle checkout.session.completed
    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {}) or {}
        payment_intent_id = session.get("payment_intent")
        tip_type = metadata.get("type")

        if tip_type == "tip":
            session_id = session.get("id")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE tips SET status = 'completed' WHERE stripe_session_id = %s AND status = 'pending'",
                (session_id,),
            )
            conn.commit()
            cur.close()
            conn.close()
        else:
            boost_id = metadata.get("boost_id")
            tier = metadata.get("tier")
            user_id = metadata.get("user_id")
            # Advertising subscription checkout
            if session.get("mode") == "subscription" and user_id and tier:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute(
                    """UPDATE advertiser_subscriptions 
                       SET status = 'active', start_date = NOW(),
                           stripe_session_id = %s
                       WHERE user_id = %s AND tier = %s AND status = 'pending'
                       ORDER BY created_at DESC LIMIT 1""",
                    (session.get("id"), int(user_id), tier),
                )
                # Mark user as advertiser
                cur.execute(
                    "UPDATE users SET is_advertiser = TRUE WHERE id = %s",
                    (int(user_id),),
                )
                conn.commit()
                cur.close()
                conn.close()
            elif boost_id:
                conn = get_conn()
                cur = conn.cursor()
                tier_info = TIERS.get(tier, TIERS["boost"])
                duration_days = int(tier_info["duration_days"])
                interval_clause = f"INTERVAL '{duration_days} days'"
                cur.execute(
                    f"""UPDATE post_boosts 
                       SET payment_status = 'paid', 
                           stripe_payment_intent_id = %s,
                           status = 'active',
                           admin_approved = TRUE,
                           start_date = NOW(),
                           end_date = NOW() + {interval_clause}
                       WHERE id = %s""",
                    (payment_intent_id, int(boost_id)),
                )
                conn.commit()
                cur.close()
                conn.close()

    # Handle subscription cancellation/expiration
    if event.get("type") in ("customer.subscription.deleted", "customer.subscription.updated"):
        sub_obj = event["data"]["object"]
        sub_status = sub_obj.get("status")
        if sub_status in ("canceled", "unpaid", "incomplete_expired"):
            stripe_sub_id = sub_obj.get("id")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE advertiser_subscriptions SET status = 'cancelled' WHERE stripe_session_id = %s",
                (stripe_sub_id,),
            )
            conn.commit()
            cur.close()
            conn.close()

    return {"received": True}
