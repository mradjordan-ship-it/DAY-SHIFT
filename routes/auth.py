"""Auth routes for Day Shift Marketplace."""
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
import aiofiles

from .deps import (
    get_conn, hash_password, verify_password, create_token, get_current_user,
    UPLOAD_DIR, MAX_IMAGE_BYTES,
)
from .models import RegisterBody, LoginBody, ForgotPasswordBody, ResetPasswordBody

api = APIRouter()


def _validate_password(password: str) -> None:
    """Enforce minimum password strength: 8+ chars, at least 1 letter and 1 number."""
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if not re.search(r"[a-zA-Z]", password):
        raise HTTPException(400, "Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        raise HTTPException(400, "Password must contain at least one number")


@api.post("/auth/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("worker"),
    image: UploadFile = File(...),
    terms_accepted: str = Form(...),
    privacy_accepted: str = Form(...),
    marketing_opt_in: str = Form(...),
):
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
        cur.execute(
            "INSERT INTO users (name, email, password_hash, role, avatar_url) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (name, email, hash_password(password), role, avatar_url),
        )
        user = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        dest.unlink(missing_ok=True)
        if "unique" in str(e).lower():
            raise HTTPException(400, "Email already registered")
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()

    token = create_token(user["id"])
    for f in ("password_hash", "reset_token", "reset_token_expires"):
        user.pop(f, None)
    return {"token": token, "user": user}


@api.post("/auth/login")
def login(request: Request, body: LoginBody):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (body.email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    if user["is_suspended"]:
        raise HTTPException(403, f"Account suspended: {user['suspension_reason'] or 'Violation of community guidelines'}")

    token = create_token(user["id"])
    user = dict(user)
    for f in ("password_hash", "reset_token", "reset_token_expires"):
        user.pop(f, None)
    return {"token": token, "user": user}


@api.post("/auth/forgot-password")
def forgot_password(body: ForgotPasswordBody, request: Request):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        # Return success anyway to prevent email enumeration
        return {"ok": True, "message": "If that email is registered, a reset link was created."}

    token = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(hours=1)
    
    cur.execute(
        "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE id = %s",
        (token, expires, user["id"])
    )
    conn.commit()
    cur.close()
    conn.close()

    # In production, send the reset link via email.
    # For now, we store the token and the user must use the reset form with the token
    # from an actual email. We do NOT return the token in the API response.
    return {
        "ok": True,
        "message": "If that email is registered, a reset link has been sent.",
    }


@api.post("/auth/reset-password")
def reset_password(body: ResetPasswordBody):
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
    now = datetime.utcnow()
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
    for f in ("password_hash", "reset_token", "reset_token_expires"):
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
    for f in ("password_hash", "reset_token", "reset_token_expires"):
        updated.pop(f, None)
    return updated
