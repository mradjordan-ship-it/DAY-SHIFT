"""Auth routes for Day Shift Marketplace."""
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
from .models import RegisterBody, LoginBody, ForgotPasswordBody, ResetPasswordBody
from .email_utils import send_verification_email, send_password_reset_email

api = APIRouter()

limiter = Limiter(key_func=get_remote_address)


def _get_base_url_from_request(request: Request) -> str:
    """Derive the public base URL from the request for email links."""
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN") if (os := __import__("os")) else None
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
):
    # reCAPTCHA verification
    _verify_recaptcha(recaptcha_token)

    # Normalize email
    email = email.strip().lower()

    _validate_password(password)
    if role not in ("worker", "employer"):
        raise HTTPException(400, "role must be 'worker' or 'employer'")
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
            "INSERT INTO users (name, email, password_hash, role, avatar_url, email_verified, email_verify_token) VALUES (%s, %s, %s, %s, %s, FALSE, %s) RETURNING *",
            (name, email, hash_password(password), role, avatar_url, verify_token),
        )
        user = dict(cur.fetchone())
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
    return {"token": token, "user": user}


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
        raise HTTPException(403, f"Account suspended: {user['suspension_reason'] or 'Violation of community guidelines'}")

    token = create_token(user["id"])
    user = dict(user)
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token"):
        user.pop(f, None)
    return {"token": token, "user": user}


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
