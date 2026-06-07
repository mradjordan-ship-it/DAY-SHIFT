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

    event = None
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            # Without webhook secret, at least validate it's proper JSON with a known event type
            import json
            event = json.loads(payload)
            if not isinstance(event, dict) or "type" not in event or "data" not in event:
                raise HTTPException(400, "Invalid webhook payload")
            # Only process known event types
            allowed_types = {"checkout.session.completed", "payment_intent.succeeded", "payment_intent.payment_failed"}
            if event.get("type") not in allowed_types:
                return {"received": True, "ignored": True}
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    except Exception as e:
        raise HTTPException(400, f"Webhook error: {str(e)}")

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
            if boost_id:
                conn = get_conn()
                cur = conn.cursor()
                tier_info = TIERS.get(tier, TIERS["boost"])
                duration_days = tier_info["duration_days"]
                cur.execute(
                    """UPDATE post_boosts 
                       SET payment_status = 'paid', 
                           stripe_payment_intent_id = %s,
                           status = 'active',
                           admin_approved = TRUE,
                           start_date = NOW(),
                           end_date = NOW() + INTERVAL '%s days'
                       WHERE id = %s""",
                    (payment_intent_id, duration_days, int(boost_id)),
                )
                conn.commit()
                cur.close()
                conn.close()

    return {"received": True}
