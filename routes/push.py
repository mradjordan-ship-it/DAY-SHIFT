"""Push notification routes and utilities for Day Shift Marketplace."""
import os
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from pywebpush import webpush, WebPushException

from .deps import get_conn, get_current_user

logger = logging.getLogger(__name__)

api = APIRouter()

# ── VAPID Configuration ──────────────────────────────────────────────────────
VAPID_PRIVATE_KEY_PATH = Path("vapid_keys/private.key")
VAPID_PRIVATE_KEY = VAPID_PRIVATE_KEY_PATH.read_text() if VAPID_PRIVATE_KEY_PATH.exists() else os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS = {"sub": "mailto:contact@dayshiftnow.me"}


class PushSubscriptionBody(BaseModel):
    endpoint: str
    keys: dict  # {"p256dh": "...", "auth": "..."}


# ── API: Register / update push subscription ─────────────────────────────────

@api.post("/push/subscribe")
def subscribe(body: PushSubscriptionBody, current_user=Depends(get_current_user)):
    """Register a push subscription for the current user."""
    p256dh = body.keys.get("p256dh", "")
    auth_key = body.keys.get("auth", "")
    if not body.endpoint or not p256dh or not auth_key:
        raise HTTPException(400, "endpoint, p256dh, and auth keys are required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Upsert: if this user+endpoint combo exists, update the keys
        cur.execute(
            """
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth_key)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, endpoint) DO UPDATE SET p256dh = EXCLUDED.p256dh, auth_key = EXCLUDED.auth_key
            RETURNING id
            """,
            (current_user["id"], body.endpoint, p256dh, auth_key),
        )
        conn.commit()
        sub_id = cur.fetchone()["id"]
    finally:
        cur.close()
        conn.close()

    return {"ok": True, "id": sub_id}


@api.post("/push/unsubscribe")
def unsubscribe(body: dict, current_user=Depends(get_current_user)):
    """Remove a push subscription."""
    endpoint = body.get("endpoint", "")
    if not endpoint:
        raise HTTPException(400, "endpoint is required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM push_subscriptions WHERE user_id = %s AND endpoint = %s",
            (current_user["id"], endpoint),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {"ok": True}


@api.get("/push/vapid-key")
def get_vapid_key():
    """Return the VAPID public key for the frontend to use for push subscription."""
    pub_key_path = Path("vapid_keys/public.key")
    if pub_key_path.exists():
        # Parse the PEM file to get raw base64
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from py_vapid import Vapid
        try:
            v = Vapid.from_file("vapid_keys/private.key")
            raw = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
            import base64
            return {"key": base64.b64encode(raw).decode()}
        except Exception:
            pass
    # Fallback to env var
    key = os.environ.get("VAPID_PUBLIC_KEY", "")
    return {"key": key}


# ── Server-side: send push notification to a user ────────────────────────────

def send_push_to_user(user_id: int, title: str, body: str, url: str = "/") -> int:
    """Send a push notification to all subscriptions for a given user.
    
    Returns the number of successful sends. Removes invalid subscriptions.
    """
    if not VAPID_PRIVATE_KEY:
        logger.info(f"[Push] No VAPID key — skipping push to user {user_id}")
        return 0

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, endpoint, p256dh, auth_key FROM push_subscriptions WHERE user_id = %s", (user_id,))
    subs = cur.fetchall()

    if not subs:
        cur.close()
        conn.close()
        return 0

    payload = json.dumps({"title": title, "body": body, "url": url})
    sent = 0
    stale_ids = []

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth_key"]},
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
                ttl=86400,  # 24 hours
            )
            sent += 1
        except WebPushException as e:
            logger.warning(f"[Push] Failed for sub {sub['id']}: {e}")
            # If the subscription is gone (410), mark for deletion
            if hasattr(e, 'response') and e.response and e.response.status_code in (404, 410):
                stale_ids.append(sub["id"])
        except Exception as e:
            logger.error(f"[Push] Unexpected error for sub {sub['id']}: {e}")

    # Clean up stale subscriptions
    if stale_ids:
        cur.execute("DELETE FROM push_subscriptions WHERE id = ANY(%s)", (stale_ids,))
        conn.commit()

    cur.close()
    conn.close()
    return sent


def send_push_to_users(user_ids: list[int], title: str, body: str, url: str = "/") -> int:
    """Send a push notification to multiple users."""
    total = 0
    for uid in user_ids:
        total += send_push_to_user(uid, title, body, url)
    return total
