"""Tip / donation routes for Day Shift Marketplace."""
import os
from fastapi import APIRouter, HTTPException, Depends, Request

from .deps import get_conn, get_current_user, require_admin

api = APIRouter()

STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY")


@api.post("/tips/checkout")
def create_tip_checkout(body: dict, request: Request, current_user=Depends(get_current_user)):
    """Create a Stripe Checkout session for a tip."""
    if not STRIPE_SECRET:
        raise HTTPException(500, "Stripe is not configured")

    amount = body.get("amount", 0)
    if not isinstance(amount, (int, float)) or amount < 100:
        raise HTTPException(400, "Minimum tip is $1")
    message = body.get("message", "")

    import stripe
    stripe.api_key = STRIPE_SECRET

    origin = request.headers.get("origin") or "https://day-shift.workshop.build"
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    if custom_domain:
        origin = f"https://{custom_domain}"
    amount_dollars = amount / 100

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Day Shift Tip — ${amount_dollars:.2f}",
                        "description": "Support the Day Shift community" + (f": {message[:60]}" if message else ""),
                    },
                    "unit_amount": amount,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{origin}/sponsor?tip_success=1",
            cancel_url=f"{origin}/sponsor?tip_canceled=1",
            metadata={
                "type": "tip",
                "user_id": current_user["id"],
                "amount": str(amount),
                "message": message[:200] if message else "",
            },
        )
    except Exception as e:
        raise HTTPException(500, f"Stripe error: {str(e)}")

    # Record the tip as pending
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tips (user_id, amount, name, email, message, status, stripe_session_id) VALUES (%s, %s, %s, %s, %s, 'pending', %s) RETURNING *",
        (current_user["id"], amount, current_user["name"], current_user["email"], message, session.id),
    )
    tip = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    if tip.get("created_at"):
        tip["created_at"] = tip["created_at"].isoformat()

    return {
        "id": tip["id"],
        "amount": amount,
        "stripe_checkout_url": session.url,
        "stripe_session_id": session.id,
    }


@api.post("/tips")
def create_tip(body: dict, current_user=Depends(get_current_user)):
    amount = body.get("amount", 0)
    if not isinstance(amount, (int, float)) or amount < 100:
        raise HTTPException(400, "Minimum tip is $1")
    message = body.get("message", "")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tips (user_id, amount, name, email, message, status) VALUES (%s, %s, %s, %s, %s, 'pending') RETURNING *",
        (current_user["id"], amount, current_user["name"], current_user["email"], message),
    )
    tip = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    if tip.get("created_at"):
        tip["created_at"] = tip["created_at"].isoformat()
    return tip


@api.post("/tips/guest")
def create_guest_tip(body: dict):
    amount = body.get("amount", 0)
    if not isinstance(amount, (int, float)) or amount < 100:
        raise HTTPException(400, "Minimum tip is $1")
    name = body.get("name", "")
    email = body.get("email", "")
    message = body.get("message", "")
    if not email:
        raise HTTPException(400, "Email is required")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tips (user_id, amount, name, email, message, status) VALUES (NULL, %s, %s, %s, %s, 'pending') RETURNING *",
        (amount, name, email, message),
    )
    tip = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    if tip.get("created_at"):
        tip["created_at"] = tip["created_at"].isoformat()
    return tip


@api.get("/admin/tips")
def admin_list_tips(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tips ORDER BY created_at DESC")
    tips = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for t in tips:
        if t.get("created_at"):
            t["created_at"] = t["created_at"].isoformat()
    return tips


@api.patch("/admin/tips/{tip_id}")
def admin_update_tip(tip_id: int, body: dict, admin=Depends(require_admin)):
    allowed = {"status"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, "No valid fields")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tips WHERE id=%s", (tip_id,))
    if not cur.fetchone():
        raise HTTPException(404, "Tip not found")
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    cur.execute(f"UPDATE tips SET {set_clause} WHERE id=%s RETURNING *", list(updates.values()) + [tip_id])
    tip = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    return tip
