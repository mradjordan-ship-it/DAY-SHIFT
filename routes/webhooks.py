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
            if boost_id:
                conn = get_conn()
                cur = conn.cursor()
                tier_info = TIERS.get(tier, TIERS["boost"])
                duration_days = int(tier_info["duration_days"])
                # INTERVAL cannot use %s parameter inside a string literal,
                # so we build the interval clause with a validated integer
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

    return {"received": True}
