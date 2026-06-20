"""Auth routes for Day Shift Marketplace."""
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import aiofiles

from .deps import (
    get_conn, hash_password, verify_password, create_token, get_current_user,
    UPLOAD_DIR, MAX_IMAGE_BYTES,
)
from .models import RegisterBody, LoginBody, ForgotPasswordBody, ResetPasswordBody, ChangePasswordBody
from .email_utils import send_verification_email, send_password_reset_email

api = APIRouter()

limiter = Limiter(key_func=get_remote_address)


def _get_base_url_from_request(request: Request) -> str:
    """Derive the public base URL from the request for email links."""
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    if custom_domain:
        return f"https://{custom_domain}"
    origin = request.headers.get("origin") or request.headers.get("referer", "")
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        return f"{parsed.scheme}://{parsed.netloc}"
    return "https://dayshift.app"


def _validate_password(password: str) -> None:
    """Enforce minimum password strength: 8+ chars, at least 1 letter and 1 number."""
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if not re.search(r"[a-zA-Z]", password):
        raise HTTPException(400, "Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        raise HTTPException(400, "Password must contain at least one number")


def _verify_recaptcha(token: str) -> None:
    """Verify reCAPTCHA token. Skips if RECAPTCHA_SECRET_KEY not configured."""
    secret = os.environ.get("RECAPTCHA_SECRET_KEY")
    if not secret or not token:
        # If no secret configured, skip verification (dev mode)
        if not secret:
            return
        raise HTTPException(400, "reCAPTCHA verification required")
    try:
        import httpx
        resp = httpx.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": token},
            timeout=10,
        )
        result = resp.json()
        if not result.get("success"):
            raise HTTPException(400, "reCAPTCHA verification failed")
    except HTTPException:
        raise
    except Exception:
        # If reCAPTCHA service is down, don't block registration
        pass


@api.post("/auth/register")
@limiter.limit("5/minute")
async def register(
    request: Request,  # required by slowapi for rate limiting
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("worker"),
    image: UploadFile = File(...),
    terms_accepted: str = Form(...),
    privacy_accepted: str = Form(...),
    marketing_opt_in: str = Form(...),
    recaptcha_token: str = Form(""),
    promo_code: str = Form(""),
):
    # reCAPTCHA verification
    _verify_recaptcha(recaptcha_token)

    # Normalize email
    email = email.strip().lower()

    _validate_password(password)
    if role not in ("worker", "employer", "advertiser"):
        raise HTTPException(400, "role must be 'worker', 'employer', or 'advertiser'")
    if not image or not image.filename:
        raise HTTPException(400, "Profile image is required")

    # Parse booleans from form
    def to_bool(v: str) -> bool:
        return str(v).lower() in ("true", "1", "yes", "on")

    if not (to_bool(terms_accepted) and to_bool(privacy_accepted)):
        raise HTTPException(400, "You must accept Terms of Use and Privacy Policy.")

    # Save image first
    ext = Path(image.filename).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(400, "Image must be jpg, png, gif, or webp")
    filename = f"avatar_{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    content = await image.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(400, f"Image exceeds {MAX_IMAGE_BYTES // (1024*1024)}MB limit")
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)
    avatar_url = f"/api/media/{filename}"

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Generate email verification token
        verify_token = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role, avatar_url, email_verified, email_verify_token, is_advertiser, advertiser_agreement_accepted) VALUES (%s, %s, %s, %s, %s, FALSE, %s, %s, %s) RETURNING *",
            (name, email, hash_password(password), role, avatar_url, verify_token, role == "advertiser", role == "advertiser"),
        )
        user = dict(cur.fetchone())
        conn.commit()

        # ── Promo code redemption ──
        promo_applied = None
        if promo_code and promo_code.strip():
            pc = promo_code.strip().upper()
            cur.execute(
                """SELECT * FROM promo_codes WHERE code = %s AND is_active = TRUE""",
                (pc,),
            )
            promo = cur.fetchone()
            if promo:
                promo = dict(promo)
                # Check expiry
                if promo["expires_at"] and promo["expires_at"] < datetime.now(timezone.utc):
                    promo_applied = {"code": pc, "status": "expired"}
                # Check max redemptions
                elif promo["max_redemptions"] > 0 and promo["redeemed_count"] >= promo["max_redemptions"]:
                    promo_applied = {"code": pc, "status": "maxed_out"}
                else:
                    # Redeem
                    cur.execute(
                        """INSERT INTO promo_redemptions (promo_code_id, user_id) VALUES (%s, %s)
                           ON CONFLICT (user_id, promo_code_id) DO NOTHING
                           RETURNING id""",
                        (promo["id"], user["id"]),
                    )
                    redemption = cur.fetchone()
                    if redemption:
                        cur.execute(
                            "UPDATE promo_codes SET redeemed_count = redeemed_count + 1 WHERE id = %s",
                            (promo["id"],),
                        )
                        promo_applied = {
                            "code": pc,
                            "status": "redeemed",
                            "boost_tier": promo["boost_tier"],
                            "boost_days": promo["boost_days"],
                            "discount_percent": promo["discount_percent"],
                            "source": promo["source"],
                        }
                    else:
                        promo_applied = {"code": pc, "status": "already_redeemed"}
                conn.commit()
    except Exception as e:
        conn.rollback()
        dest.unlink(missing_ok=True)
        if "unique" in str(e).lower():
            raise HTTPException(400, "Email already registered")
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    # Send verification email (non-blocking — don't fail registration if email fails)
    base_url = _get_base_url_from_request(request)
    send_verification_email(email, name, verify_token, base_url)

    token = create_token(user["id"])
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token"):
        user.pop(f, None)
    return {"token": token, "user": user, "promo": promo_applied}


@api.post("/auth/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginBody):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (body.email.strip().lower(),))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    if user["is_suspended"]:
        # Check if suspension expired
        if user.get("suspension_expires_at") and user["suspension_expires_at"] < datetime.now(timezone.utc):
            conn2 = get_conn()
            cur2 = conn2.cursor()
            cur2.execute(
                "UPDATE users SET is_suspended=FALSE, suspension_reason=NULL, suspension_expires_at=NULL WHERE id=%s",
                (user["id"],),
            )
            conn2.commit()
            cur2.close()
            conn2.close()
            # Refetch
            conn3 = get_conn()
            cur3 = conn3.cursor()
            cur3.execute("SELECT * FROM users WHERE id = %s", (user["id"],))
            user = cur3.fetchone()
            cur3.close()
            conn3.close()
        else:
            # Include appeal info so frontend can show appeal option
            appeal = None
            try:
                conn2 = get_conn()
                cur2 = conn2.cursor()
                cur2.execute(
                    "SELECT id, status FROM appeals WHERE user_id=%s ORDER BY created_at DESC LIMIT 1",
                    (user["id"],),
                )
                app_row = cur2.fetchone()
                if app_row:
                    appeal = {"id": app_row["id"], "status": app_row["status"]}
                cur2.close()
                conn2.close()
            except Exception:
                pass
            raise HTTPException(403, detail={
                "message": f"Account suspended: {user['suspension_reason'] or 'Violation of community guidelines'}",
                "suspension_reason": user["suspension_reason"] or "",
                "has_pending_appeal": appeal and appeal["status"] == "pending",
            })

    token = create_token(user["id"])
    user = dict(user)
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token"):
        user.pop(f, None)
    return {"token": token, "user": user}


@api.post("/appeals/guest")
@limiter.limit("3/minute")
def guest_appeal(request: Request, body: dict):
    """Allow a suspended user to submit an appeal using email/password (no JWT needed)."""
    from .deps import verify_password
    email = (body.get("email") or "").strip()
    password = body.get("password", "")
    reason = (body.get("reason") or "").strip()

    if not email or not password:
        raise HTTPException(400, "Email and password are required")
    if len(reason) < 20:
        raise HTTPException(400, "Please provide more detail (at least 20 characters)")
    if len(reason) > 2000:
        raise HTTPException(400, "Appeal too long (max 2000 characters)")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    if not user["is_suspended"]:
        raise HTTPException(400, "Account is not suspended")

    # Now submit appeal (reuse the regular endpoint logic)
    from .deps import get_conn
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM appeals WHERE user_id=%s AND status='pending'", (user["id"],))
        if cur.fetchone():
            raise HTTPException(400, "You already have a pending appeal")

        cur.execute(
            """INSERT INTO appeals (user_id, reason) VALUES (%s, %s) RETURNING *""",
            (user["id"], reason),
        )
        appeal = dict(cur.fetchone())
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error")
    finally:
        cur.close()
        conn.close()

    # Notify admins
    try:
        from .push import send_push_to_users
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE is_admin = TRUE")
        admin_ids = [r["id"] for r in cur.fetchall()]
        cur.close()
        conn.close()
        if admin_ids:
            send_push_to_users(admin_ids, "New Appeal", f"Appeal from {user['name']}", "/admin")
    except Exception:
        pass

    if appeal.get("created_at"):
        appeal["created_at"] = appeal["created_at"].isoformat()
    return appeal


@api.post("/auth/forgot-password")
@limiter.limit("3/minute")
def forgot_password(body: ForgotPasswordBody, request: Request):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE email = %s", (body.email,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        # Return success anyway to prevent email enumeration
        return {"ok": True, "message": "If that email is registered, a reset link was created."}

    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    
    cur.execute(
        "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s",
        (token, expires, user["id"])
    )
    conn.commit()
    cur.close()
    conn.close()

    # Send the reset link via email
    base_url = _get_base_url_from_request(request)
    send_password_reset_email(body.email, token, base_url)

    return {
        "ok": True,
        "message": "If that email is registered, a reset link has been sent.",
    }


@api.post("/auth/change-password")
@limiter.limit("5/minute")
def change_password(body: ChangePasswordBody, request: Request, current_user=Depends(get_current_user)):
    _validate_password(body.new_password)
    
    if not verify_password(body.current_password, current_user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    
    if body.current_password == body.new_password:
        raise HTTPException(400, "New password must be different from current password")
    
    new_hash = hash_password(body.new_password)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, current_user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    
    return {"ok": True, "message": "Password updated successfully"}


@api.post("/auth/reset-password")
@limiter.limit("5/minute")
def reset_password(body: ResetPasswordBody, request: Request):
    _validate_password(body.new_password)
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(
        "SELECT id, reset_token_expires FROM users WHERE reset_token = %s", 
        (body.token,)
    )
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(400, "Invalid or expired token")
        
    # Check expiry (make sure we handle timezone-aware vs naive properly)
    from datetime import timezone
    now = datetime.now(timezone.utc)
    # PostGres TIMESTAMPTZ comes back as a timezone-aware datetime in UTC
    # Since now is naive, we can just strip the tzinfo from the DB response for comparison
    expires_naive = user["reset_token_expires"].replace(tzinfo=None) if user["reset_token_expires"] else datetime.min
    
    if expires_naive < now:
        cur.close()
        conn.close()
        raise HTTPException(400, "Token has expired")
        
    hashed = hash_password(body.new_password)
    cur.execute(
        "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL WHERE id = %s",
        (hashed, user["id"])
    )
    conn.commit()
    cur.close()
    conn.close()
    
    return {"ok": True}


@api.get("/auth/me")
def me(current_user=Depends(get_current_user)):
    user = dict(current_user)
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token"):
        user.pop(f, None)
    return user


@api.post("/auth/onboard")
def onboard(body: dict, current_user=Depends(get_current_user)):
    allowed = {"role", "location", "cuisine_type", "experience_level", "hours", "bio"}
    updates = {k: v for k, v in body.items() if k in allowed and v}
    if not updates:
        updates["onboarded"] = True
    else:
        updates["onboarded"] = True
    conn = get_conn()
    cur = conn.cursor()
    try:
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(
            f"UPDATE users SET {set_clause} WHERE id = %s RETURNING *",
            list(updates.values()) + [current_user["id"]],
        )
        conn.commit()
        updated = dict(cur.fetchone())
    finally:
        cur.close()
        conn.close()
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token"):
        updated.pop(f, None)
    return updated


# ── Email Verification ────────────────────────────────────────────────────────

@api.post("/auth/verify-email")
@limiter.limit("10/minute")
def verify_email(body: dict, request: Request):
    """Verify a user's email using the token from the verification link."""
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(400, "Verification token is required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, name, email, email_verify_token FROM users WHERE email_verify_token = %s",
            (token,),
        )
        user = cur.fetchone()
        if not user:
            raise HTTPException(400, "Invalid or expired verification token")

        # Mark as verified and clear the token
        cur.execute(
            "UPDATE users SET email_verified = TRUE, email_verify_token = NULL WHERE id = %s RETURNING *",
            (user["id"],),
        )
        updated = dict(cur.fetchone())
        conn.commit()
    finally:
        cur.close()
        conn.close()

    # Return a fresh token so the user is auto-logged in
    jwt_token = create_token(updated["id"])
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token"):
        updated.pop(f, None)
    return {"ok": True, "token": jwt_token, "user": updated}


@api.post("/auth/resend-verification")
@limiter.limit("3/minute")
def resend_verification(body: dict, request: Request):
    """Resend a verification email to the given address."""
    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Email is required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, name, email_verified FROM users WHERE email = %s",
            (email,),
        )
        user = cur.fetchone()
        if not user:
            # Don't reveal whether email exists
            return {"ok": True, "message": "If that email is registered and unverified, a new verification link has been sent."}
        if user["email_verified"]:
            return {"ok": True, "message": "Email is already verified. You can sign in."}

        # Generate a new token (invalidates any previous one)
        new_token = str(uuid.uuid4())
        cur.execute(
            "UPDATE users SET email_verify_token = %s WHERE id = %s",
            (new_token, user["id"]),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    base_url = _get_base_url_from_request(request)
    send_verification_email(email, user["name"], new_token, base_url)

    return {"ok": True, "message": "If that email is registered and unverified, a new verification link has been sent."}


# ── Promo code endpoints ──

@api.get("/promo/validate/{code}")
def validate_promo_code(code: str):
    """Check if a promo code is valid (for showing preview on signup form)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM promo_codes WHERE code = %s AND is_active = TRUE", (code.upper(),))
    promo = cur.fetchone()
    cur.close()
    conn.close()
    if not promo:
        return {"valid": False}
    promo = dict(promo)
    return {
        "valid": True,
        "code": promo["code"],
        "description": promo["description"],
        "boost_tier": promo["boost_tier"],
        "boost_days": promo["boost_days"],
        "discount_percent": promo["discount_percent"],
        "source": promo["source"],
    }


@api.get("/promo/my-redemption")
def get_my_promo_redemption(current_user=Depends(get_current_user)):
    """Get the current user's promo code redemption (for applying free boost)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT pr.*, pc.code, pc.boost_tier, pc.boost_days, pc.discount_percent, pc.source, pc.description
           FROM promo_redemptions pr
           JOIN promo_codes pc ON pr.promo_code_id = pc.id
           WHERE pr.user_id = %s
           ORDER BY pr.redeemed_at DESC""",
        (current_user["id"],),
    )
    redemption = cur.fetchone()
    cur.close()
    conn.close()
    if not redemption:
        return {"redeemed": False}
    return {"redeemed": True, **dict(redemption)}
