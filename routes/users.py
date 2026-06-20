"""User routes for Day Shift Marketplace."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import aiofiles

from .deps import get_conn, get_current_user, UPLOAD_DIR, MAX_IMAGE_BYTES
from .models import ProfileUpdateBody

api = APIRouter()


@api.get("/users/search")
def search_users(
    q: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    cuisine_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    conn = get_conn()
    cur = conn.cursor()
    query = """SELECT id, name, role, avatar_url, bio, location, cuisine_type, experience_level, avg_rating, total_shifts, created_at
               FROM users WHERE 1=1"""
    params = []
    if q:
        query += " AND (name ILIKE %s OR bio ILIKE %s)"
        term = f"%{q}%"
        params.extend([term, term])
    if role:
        query += " AND role = %s"
        params.append(role)
    if location:
        query += " AND location ILIKE %s"
        params.append(f"%{location}%")
    if cuisine_type:
        query += " AND cuisine_type ILIKE %s"
        params.append(f"%{cuisine_type}%")
    if experience_level:
        query += " AND experience_level = %s"
        params.append(experience_level)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    users = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for u in users:
        if u.get("created_at"):
            u["created_at"] = u["created_at"].isoformat()
    return users


@api.get("/users/{user_id}")
def get_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, name, role, avatar_url, bio, location, cuisine_type, experience_level,
                  avg_rating, total_shifts, is_advertiser, created_at
           FROM users WHERE id = %s""",
        (user_id,),
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        raise HTTPException(404, "User not found")
    user = dict(user)
    if user.get("created_at"):
        user["created_at"] = user["created_at"].isoformat()
    return user


@api.get("/users/{user_id}/reviews")
def get_user_reviews(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT r.*, u.name as reviewer_name, u.avatar_url as reviewer_avatar
           FROM reviews r JOIN users u ON r.reviewer_id = u.id
           WHERE r.reviewee_id = %s ORDER BY r.created_at DESC""",
        (user_id,),
    )
    reviews = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for r in reviews:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return reviews


@api.patch("/users/me")
def update_profile(body: ProfileUpdateBody, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    updates = {}
    if body.name:
        updates["name"] = body.name
    if body.bio is not None:
        updates["bio"] = body.bio
    if body.email:
        updates["email"] = body.email

    if updates:
        # ── Content moderation on bio ────────────────────────────────────────
        if body.bio is not None:
            from .moderation import should_block_text
            blocked, blocked_term = should_block_text(body.bio)
            if blocked:
                cur.close()
                conn.close()
                raise HTTPException(422, f"Bio rejected. Content violation: {blocked_term}")

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(
            f"UPDATE users SET {set_clause} WHERE id = %s RETURNING *",
            list(updates.values()) + [current_user["id"]],
        )
        user = dict(cur.fetchone())
        conn.commit()
    else:
        user = current_user

    cur.close()
    conn.close()
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token", "email"):
        user.pop(f, None)
    if user.get("created_at"):
        user["created_at"] = user["created_at"].isoformat()
    return user


@api.delete("/users/me")
def delete_account(current_user=Depends(get_current_user)):
    """Permanently delete the user account and all associated data (GDPR/CCPA)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        user_id = current_user["id"]
        # Cascade: all user data
        cur.execute("DELETE FROM messages WHERE sender_id = %s", (user_id,))
        cur.execute("DELETE FROM likes WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM matches WHERE worker_id = %s OR employer_id = %s", (user_id, user_id))
        cur.execute("DELETE FROM reviews WHERE reviewer_id = %s OR reviewee_id = %s", (user_id, user_id))
        cur.execute("DELETE FROM bookmarks WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM push_subscriptions WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM reports WHERE reporter_id = %s", (user_id,))
        cur.execute("DELETE FROM videos WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()
    return {"ok": True}


@api.patch("/users/me/avatar")
async def update_avatar(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        raise HTTPException(400, "Only JPG, PNG, WEBP, and GIF images are allowed")
        
    filename = f"avatar_{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(400, f"Image exceeds {MAX_IMAGE_BYTES // (1024*1024)}MB limit")
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)
    url = f"/api/media/{filename}"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET avatar_url=%s WHERE id=%s RETURNING *", (url, current_user["id"]))
    user = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    for f in ("password_hash", "reset_token", "reset_token_expires", "email_verify_token", "email"):
        user.pop(f, None)
    return user
