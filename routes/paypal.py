"""PayPal payment routes for Day Shift Marketplace.

Handles: post boosts and advertising subscriptions.
Runs alongside Stripe during migration — remove Stripe code once PayPal is verified.

Uses PayPal Orders API v2 (not legacy checkout).
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Request

from .deps import get_conn, get_current_user, require_admin

logger = logging.getLogger(__name__)
api = APIRouter()

# ── PayPal config ────────────────────────────────────────────────────────
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")

# Determine base URL for return/cancel URLs
def _get_base_url(request: Request = None) -> str:
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    if custom_domain:
        return f"https://{custom_domain}"
    if request:
        return request.headers.get("origin") or "https://day-shift.workshop.build"
    return "https://day-shift.workshop.build"


def _paypal_client():
    """Return a configured PayPal client (live or sandbox)."""
    from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment

    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(500, "PayPal is not configured")

    # Use live mode by default; switch to sandbox for testing
    mode = os.environ.get("PAYPAL_MODE", "sandbox")
    if mode == "sandbox":
        environment = SandboxEnvironment(client_id=PAYPAL_CLIENT_ID, client_secret=PAYPAL_CLIENT_SECRET)
    else:
        environment = LiveEnvironment(client_id=PAYPAL_CLIENT_ID, client_secret=PAYPAL_CLIENT_SECRET)

    return PayPalHttpClient(environment)


def _build_order_request(amount_usd: str, description: str, success_url: str, cancel_url: str, custom_id: str = None) -> dict:
    """Build a PayPal Orders v2 create order request body."""
    request_body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": custom_id or f"ds_{os.urandom(4).hex()}",
            "description": description,
            "amount": {
                "currency_code": "USD",
                "value": amount_usd,
            },
        }],
        "application_context": {
            "brand_name": "Day Shift",
            "landing_page": "NO_PREFERENCE",
            "user_action": "PAY_NOW",
            "return_url": success_url,
            "cancel_url": cancel_url,
        },
    }
    return request_body


# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════
# POST BOOSTS
# ══════════════════════════════════════════════════════════════════════

@api.post("/paypal/boosts/checkout")
def create_boost_checkout_paypal(body: dict, request: Request, current_user=Depends(get_current_user)):
    """Create a PayPal Order for a post boost."""
    from .advertiser import TIERS, BoostBody  # reuse existing tier definitions

    tier = body.get("tier")
    video_id = body.get("video_id")
    if tier not in TIERS:
        raise HTTPException(400, f"Invalid tier. Choose from: {list(TIERS.keys())}")

    tier_info = TIERS[tier]
    price = tier_info["price"]
    origin = _get_base_url(request)

    # Verify video ownership
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, title FROM videos WHERE id = %s", (video_id,))
    vid = cur.fetchone()
    if not vid:
        raise HTTPException(404, "Post not found")
    if vid["user_id"] != current_user["id"]:
        raise HTTPException(403, "Can only boost your own posts")

    # Check existing active boost
    cur.execute(
        "SELECT id FROM post_boosts WHERE video_id = %s AND status = 'active' AND end_date > NOW()",
        (video_id,),
    )
    if cur.fetchone():
        raise HTTPException(400, "This post already has an active boost")

    # Create boost record
    try:
        cur.execute(
            """INSERT INTO post_boosts (video_id, user_id, tier, status, payment_status)
               VALUES (%s, %s, %s, 'pending', 'unpaid') RETURNING *""",
            (video_id, current_user["id"], tier),
        )
        boost = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(500, "Internal error — please try again")

    # Create PayPal Order
    from paypalcheckoutsdk.orders import OrdersCreateRequest

    req = OrdersCreateRequest()
    req.prefer('return=representation')
    req.request_body(_build_order_request(
        amount_usd=f"{price:.2f}",
        description=f"{tier_info['name']} Boost — {vid['title'] or 'Your Post'} ({tier_info['duration_days']}-day visibility)",
        success_url=f"{origin}/boost?success=1&paypal=1&boost_id={boost['id']}",
        cancel_url=f"{origin}/boost?canceled=1&paypal=1",
        custom_id=f"boost_{boost['id']}",
    ))

    try:
        client = _paypal_client()
        response = client.execute(req)
        order = result_to_dict(response)
    except Exception as e:
        logger.error(f"[PayPal] Boost checkout failed: {e}")
        # Clean up pending boost
        cur2 = get_conn().cursor()
        cur2.execute("DELETE FROM post_boosts WHERE id = %s", (boost["id"],))
        get_conn().commit()
        cur2.close()
        raise HTTPException(500, f"Payment processing failed: {str(e)[:200]}")

    # Store PayPal order ID on boost
    cur.execute(
        "UPDATE post_boosts SET paypal_order_id = %s WHERE id = %s",
        (order["id"], boost["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()

    # Extract approval URL
    approval_url = None
    for link in order.get("links", []):
        if link.get("rel") == "approve":
            approval_url = link.get("href")
            break

    return {
        "id": boost["id"],
        "tier": tier,
        "price": price,
        "paypal_approval_url": approval_url,
        "paypal_order_id": order["id"],
    }


# ══════════════════════════════════════════════════════════════════════
# ADVERTISER SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════════════════

@api.post("/paypal/subscriptions/checkout")
def create_subscription_checkout_paypal(body: dict, request: Request, current_user=Depends(get_current_user)):
    """Create a PayPal Order for an advertiser subscription (one-time first month).

    Note: PayPal subscriptions use the Subscriptions API, but for simplicity we start
    with one-time orders and can migrate to recurring later.
    """
    from .advertiser import AD_TIERS

    tier = body.get("tier")
    if tier not in AD_TIERS:
        raise HTTPException(400, f"Invalid tier. Choose from: {list(AD_TIERS.keys())}")

    tier_info = AD_TIERS[tier]
    price = tier_info["price"]
    origin = _get_base_url(request)

    # Record pending subscription
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO advertiser_subscriptions (user_id, tier, status)
           VALUES (%s, %s, 'pending') RETURNING *""",
        (current_user["id"], tier),
    )
    sub = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    # Create PayPal Order for first month
    from paypalcheckoutsdk.orders import OrdersCreateRequest

    req = OrdersCreateRequest()
    req.prefer('return=representation')
    req.request_body(_build_order_request(
        amount_usd=f"{price:.2f}",
        description=f"Day Shift — {tier_info['name']} Advertising (first month)",
        success_url=f"{origin}/advertise?success=1&paypal=1&sub_id={sub['id']}",
        cancel_url=f"{origin}/advertise?canceled=1&paypal=1",
        custom_id=f"sub_{sub['id']}",
    ))

    try:
        client = _paypal_client()
        response = client.execute(req)
        order = result_to_dict(response)
    except Exception as e:
        logger.error(f"[PayPal] Subscription checkout failed: {e}")
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE advertiser_subscriptions SET status = 'failed' WHERE id = %s", (sub["id"],))
        conn.commit()
        cur.close()
        conn.close()
        raise HTTPException(500, f"PayPal checkout error: {str(e)}")

    # Store PayPal order ID
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE advertiser_subscriptions SET paypal_order_id = %s WHERE id = %s",
        (order["id"], sub["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()

    approval_url = None
    for link in order.get("links", []):
        if link.get("rel") == "approve":
            approval_url = link.get("href")
            break

    return {
        "paypal_approval_url": approval_url,
        "paypal_order_id": order["id"],
        "subscription_id": sub["id"],
    }


# ══════════════════════════════════════════════════════════════════════
# CAPTURE (execute after user approves at PayPal)
# ══════════════════════════════════════════════════════════════════════

@api.post("/paypal/capture/{order_id}")
def capture_paypal_order(order_id: str, current_user=Depends(get_current_user)):
    """Capture a PayPal order after user approves it.

    Called by frontend after redirect from PayPal with token.
    """
    from paypalcheckoutsdk.orders import OrdersCaptureRequest

    req = OrdersCaptureRequest(order_id)
    req.prefer('return=representation')

    try:
        client = _paypal_client()
        response = client.execute(req)
        order = result_to_dict(response)
    except Exception as e:
        logger.error(f"[PayPal] Capture failed for {order_id}: {e}")
        raise HTTPException(500, "Failed to capture payment.")

    status = order.get("status")
    if status not in ("COMPLETED", "APPROVED"):
        logger.warning(f"[PayPal] Unexpected status after capture: {status}")
        return {"status": status.lower(), "order_id": order_id}

    # Update the relevant record based on custom_id / reference
    ref = (order.get("purchase_units") or [{}])[0].get("reference_id", "") or ""
    conn = get_conn()
    cur = conn.cursor()

    # Determine what type of payment this was — verify ownership
    if ref.startswith("boost_"):
        boost_id = ref.replace("boost_", "")
        cur.execute("SELECT user_id FROM post_boosts WHERE id = %s", (boost_id,))
        boost_owner = cur.fetchone()
        if not boost_owner:
            raise HTTPException(404, "Boost not found")
        if boost_owner["user_id"] != current_user["id"]:
            raise HTTPException(403, "This boost does not belong to your account")
        duration_days = 30  # default
        cur.execute(
            f"""UPDATE post_boosts SET payment_status = 'paid', status = 'active',
                paypal_order_id = %s, start_date = NOW(),
                end_date = NOW() + INTERVAL '{duration_days} days'
               WHERE id = %s OR paypal_order_id = %s""",
            (order_id, boost_id, order_id),
        )

    elif ref.startswith("sub_"):
        sub_id = ref.replace("sub_", "")
        cur.execute("SELECT advertiser_id FROM advertiser_subscriptions WHERE id = %s", (sub_id,))
        sub_owner = cur.fetchone()
        if not sub_owner:
            raise HTTPException(404, "Subscription not found")
        if sub_owner["advertiser_id"] != current_user["id"]:
            raise HTTPException(403, "This subscription does not belong to your account")
        cur.execute(
            "UPDATE advertiser_subscriptions SET status = 'active', paypal_order_id = %s WHERE id = %s OR paypal_order_id = %s",
            (order_id, sub_id, order_id),
        )

    else:
        logger.info(f"[PayPL] Captured unknown reference: {ref}")

    conn.commit()
    cur.close()
    conn.close()

    return {
        "status": "completed",
        "order_id": order_id,
        "payer": (order.get("payer") or {}).get("email_address", {}).get("value", ""),
    }


# ══════════════════════════════════════════════════════════════════════
# WEBHOOK (IPN-style listener for PayPal events)
# ══════════════════════════════════════════════════════════════════════

@api.post("/webhooks/paypal")
async def paypal_webhook(request: Request):
    """Receive PayPal webhook notifications (payment completed, etc.)."""
    body = await request.body()
    raw = body.decode("utf-8")

    # Verify webhook signature (optional but recommended)
    # For now, log and process the event
    try:
        data = raw if isinstance(raw, dict) else {}
        logger.info(f"[PayPal Webhook] Received event: {data}")
    except Exception:
        pass

    # TODO: Add webhook verification + event-specific handling
    return {"received": True}


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def result_to_dict(response) -> dict:
    """Convert PayPal SDK response object to plain dict."""
    if hasattr(response, 'result'):
        r = response.result
        if hasattr(r, 'to_dict'):
            return r.to_dict()
        # Sandbox Result objects have .dict attribute (returns actual dict)
        if hasattr(r, 'dict') and isinstance(r.dict, dict):
            return r.dict
        # Fallback: build dict from known attributes
        if hasattr(r, 'id'):
            d = {'id': r.id, 'status': getattr(r, 'status', None), 'intent': getattr(r, 'intent', None)}
            if hasattr(r, 'links'):
                d['links'] = [{'rel': l.rel, 'href': l.href, 'method': getattr(l, 'method', None)} for l in r.links]
            if hasattr(r, 'purchase_units'):
                d['purchase_units'] = r.purchase_units
            return d
        return {"raw": str(r)}
    if isinstance(response, dict):
        return response
    return {"raw": str(response)}
