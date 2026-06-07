"""Video routes for Day Shift Marketplace."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
import aiofiles

from .deps import (
    get_conn, get_current_user, get_optional_user, UPLOAD_DIR, FFMPEG_BIN,
    transcode_video, MAX_VIDEO_BYTES, MAX_IMAGE_BYTES,
)
from .external_data import fetch_bls_wages, fetch_rss_news


def _extract_media(media_row: dict) -> str:
    """Extract the best available media URL from a COALESCE query row, stripping invalid values."""
    if not media_row:
        return ""
    for key in ("img", "vid", "avatar"):
        val = media_row.get(key, "") or ""
        val = val.strip()
        # Skip non-URL placeholder values
        if val and val not in ("", " ", "*", "-") and (val.startswith("/") or val.startswith("http")):
            return val
    return ""

api = APIRouter()


@api.get("/ticker")
def get_ticker_quotes():
    """Return daily inspirational quotes for the feed ticker tape."""
    import hashlib, time

    QUOTES = [
        # ── African American chefs & culinary icons ──
        {"text": "I am not a chef. I am a cook. A chef is a title. A cook is a person who does the work.", "author": "Leah Chase", "photo": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=crop&crop=face"},
        {"text": "You don't have to cook fancy or complicated masterpieces — just good food from fresh ingredients.", "author": "Edna Lewis", "photo": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=200&h=200&fit=crop&crop=face"},
        {"text": "I want every meal to be a celebration of who we are and where we come from.", "author": "Marcus Samuelsson", "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face"},
        {"text": "Cooking is an art, but all art requires knowing something about the technique and materials.", "author": "Nina Simone", "photo": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=face"},
        {"text": "Food is our common ground, a universal experience. Our stories live in the food we make.", "author": "Carla Hall", "photo": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&crop=face"},
        {"text": "I've been cooking since I was tall enough to reach the stove. The kitchen is where I found my voice.", "author": "Mashama Bailey", "photo": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face"},
        {"text": "When you know who you are and where you come from, your food tells that story.", "author": "Jerome Grant", "photo": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&h=200&fit=crop&crop=face"},
        {"text": "Every dish I create honors the hands that taught me — my grandmother, my mother, my community.", "author": "Kwame Onwuachi", "photo": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=200&h=200&fit=crop&crop=face"},
        {"text": "The table is a meeting place, a place of nourishment and story and song.", "author": "Michael Twitty", "photo": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=200&h=200&fit=crop&crop=face"},
        {"text": "I cook to preserve the legacy of those who came before me. Every recipe is a memory.", "author": "Briana Riddock", "photo": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=200&h=200&fit=crop&crop=face"},
        {"text": "Soul food isn't just about the food. It's about the soul you put into it.", "author": "Patricia Clark", "photo": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&h=200&fit=crop&crop=face"},
        {"text": "My cooking is an extension of my heritage. I carry my ancestors in every pot I stir.", "author": "JJ Johnson", "photo": "https://images.unsplash.com/photo-1463453091185-61582044d556?w=200&h=200&fit=crop&crop=face"},
        {"text": "If you can't feed a hundred people, then feed just one. But do it with love.", "author": "Leah Chase", "photo": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=crop&crop=face"},
        {"text": "The beauty of Black foodways is that we made something from nothing and made it glorious.", "author": "Michael Twitty", "photo": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face"},
        # ── Classic culinary & motivational quotes ──
        {"text": "The kitchen is a country in which there are always discoveries to be made.", "author": "Grimod de la Reynière", "photo": "https://images.unsplash.com/photo-1564564321837-a57b7070ac4f?w=200&h=200&fit=crop&crop=face"},
        {"text": "People who love to eat are always the best people.", "author": "Julia Child", "photo": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=200&h=200&fit=crop&crop=face"},
        {"text": "Cooking is like love. It should be entered into with abandon or not at all.", "author": "Harriet Van Horne", "photo": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face"},
        {"text": "No one is born a great cook, one learns by doing.", "author": "Julia Child", "photo": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&crop=face"},
        {"text": "A recipe has no soul. You, as the cook, must bring soul to the recipe.", "author": "Thomas Keller", "photo": "https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=200&h=200&fit=crop&crop=face"},
        {"text": "Cooking is at once child's play and adult joy. And cooking done with care is an act of love.", "author": "Craig Claiborne", "photo": "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=200&h=200&fit=crop&crop=face"},
        {"text": "One cannot think well, love well, sleep well, if one has not dined well.", "author": "Virginia Woolf", "photo": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&h=200&fit=crop&crop=face"},
        {"text": "Food is symbolic of love when words are inadequate.", "author": "Alan D. Wolfelt", "photo": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&h=200&fit=crop&crop=face"},
        {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs", "photo": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=crop&crop=face"},
        {"text": "Hard work beats talent when talent doesn't work hard.", "author": "Tim Notke", "photo": "https://images.unsplash.com/photo-1463453091185-61582044d556?w=200&h=200&fit=crop&crop=face"},
        {"text": "Hustle in silence, let your success make the noise.", "author": "Unknown", "photo": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=200&h=200&fit=crop&crop=face"},
        {"text": "The kitchen is the heart of every home.", "author": "Unknown", "photo": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=200&h=200&fit=crop&crop=face"},
        {"text": "Do what you can, with what you have, where you are.", "author": "Theodore Roosevelt", "photo": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=200&h=200&fit=crop&crop=face"},
        {"text": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein", "photo": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=200&h=200&fit=crop&crop=face"},
    ]

    # Use day-of-year as seed so quotes rotate daily but stay consistent within a day
    day_seed = int(hashlib.md5(str(time.strftime("%Y-%m-%d")).encode()).hexdigest(), 16)
    # Pick 8 quotes for today using deterministic shuffle
    indices = list(range(len(QUOTES)))
    for i in range(len(indices) - 1, 0, -1):
        j = day_seed % (i + 1)
        indices[i], indices[j] = indices[j], indices[i]
        day_seed = day_seed // (i + 1) + 1

    selected = [QUOTES[indices[i]] for i in range(min(8, len(QUOTES)))]

    stats = []
    for q in selected:
        stats.append({
            "photo": q["photo"],
            "author": q["author"],
            "text": f'"{q["text"]}"',
            "scope": "quote",
        })

    return {"stats": stats, "config": _get_ticker_config()}

def _get_ticker_config() -> dict:
    """Get ticker layout config from DB, with defaults."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'ticker_config'")
        row = cur.fetchone()
        if row:
            import json
            return json.loads(row[0])
    except Exception:
        pass
    return {"frequency": 4, "mobile_height": "full", "desktop_height": 180, "desktop_span": True}

@api.get("/ticker-config")
def get_ticker_config(current_user=Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(403, "Admin only")
    return _get_ticker_config()

@api.post("/ticker-config")
def save_ticker_config(config: dict, current_user=Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(403, "Admin only")
    import json
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (key, value) VALUES ('ticker_config', %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (json.dumps(config),))
    conn.commit()
    return {"ok": True}

@api.get("/videos")
def list_videos(
    type: Optional[str] = None,
    user_id: Optional[int] = None,
    q: Optional[str] = None,
    location: Optional[str] = None,
    cuisine_type: Optional[str] = None,
    category: Optional[str] = None,
    experience_level: Optional[str] = None,
    current_user=Depends(get_optional_user),
):
    conn = get_conn()
    cur = conn.cursor()

    query = """
        SELECT v.*, u.name as author_name, u.avatar_url as author_avatar, u.avg_rating as author_rating, u.role as author_role, u.is_admin as author_is_admin, u.is_advertiser as author_is_advertiser
        FROM videos v JOIN users u ON v.user_id = u.id
        WHERE 1=1
    """
    params = []
    if type:
        query += " AND v.type = %s"
        params.append(type)
    if user_id:
        query += " AND v.user_id = %s"
        params.append(user_id)
    if q:
        query += " AND (v.title ILIKE %s OR v.description ILIKE %s OR v.cuisine_type ILIKE %s OR v.location ILIKE %s OR u.name ILIKE %s)"
        term = f"%{q}%"
        params.extend([term, term, term, term, term])
    if location:
        query += " AND v.location ILIKE %s"
        params.append(f"%{location}%")
    if cuisine_type:
        query += " AND v.cuisine_type ILIKE %s"
        params.append(f"%{cuisine_type}%")
    if category and category != "all":
        query += " AND v.category = %s"
        params.append(category)
    if experience_level:
        query += " AND v.experience_level = %s"
        params.append(experience_level)
    # Hide scheduled posts that haven't gone live yet (unless viewing own posts)
    if current_user:
        query += " AND (v.scheduled_at IS NULL OR v.scheduled_at <= NOW() OR v.user_id = %s)"
        params.append(current_user["id"])
    else:
        query += " AND (v.scheduled_at IS NULL OR v.scheduled_at <= NOW())"

    # check which ones the current user liked
    liked_ids = set()
    if current_user:
        cur.execute("SELECT video_id FROM likes WHERE user_id = %s", (current_user["id"],))
        liked_ids = {r["video_id"] for r in cur.fetchall()}

    # Fetch sponsored posts (admin only, highest priority)
    sponsored = []
    if not type and (not category or category == "all") and not q and not user_id:
        cur.execute("""
            SELECT v.*, u.name as author_name, u.avatar_url as author_avatar, u.avg_rating as author_rating,
                   u.role as author_role, u.is_admin as author_is_admin, u.is_advertiser as author_is_advertiser
            FROM videos v JOIN users u ON v.user_id = u.id
            WHERE v.category = 'sponsored' AND u.is_admin = TRUE
            ORDER BY v.created_at DESC
            LIMIT 5
        """)
        sponsored = [dict(r) for r in cur.fetchall()]
        for s in sponsored:
            s["liked_by_me"] = s["id"] in liked_ids
            s["is_sponsored"] = True
            if s.get("created_at"): s["created_at"] = s["created_at"].isoformat()

    # Newest first for all feeds
    query += " ORDER BY v.created_at DESC"

    cur.execute(query, params)
    videos = [dict(r) for r in cur.fetchall()]

    # Fetch active boosted posts and merge at the top (for the main "all" feed)
    if not type and (not category or category == "all") and not q and not user_id:
        cur.execute("""
            SELECT v.*, u.name as author_name, u.avatar_url as author_avatar, u.avg_rating as author_rating,
                   u.role as author_role, u.is_admin as author_is_admin, u.is_advertiser as author_is_advertiser,
                   pb.tier as boost_tier
            FROM post_boosts pb
            JOIN videos v ON pb.video_id = v.id
            JOIN users u ON v.user_id = u.id
            WHERE pb.status = 'active' AND pb.end_date > NOW()
            ORDER BY
              CASE pb.tier WHEN 'premium' THEN 0 WHEN 'spotlight' THEN 1 WHEN 'boost' THEN 2 END,
              pb.created_at DESC
        """)
        boosted = [dict(r) for r in cur.fetchall()]
        for b in boosted:
            b["liked_by_me"] = b["id"] in liked_ids
            if b.get("created_at"): b["created_at"] = b["created_at"].isoformat()
            if b["type"] == "worker" and (not current_user or (current_user["role"] != "employer" and current_user["id"] != b["user_id"])):
                b["pay_rate"] = ""
        # Dedupe: remove sponsored and boosted posts from regular videos
        sponsored_ids = {s["id"] for s in sponsored}
        boosted_ids = {b["id"] for b in boosted}
        videos = [v for v in videos if v["id"] not in sponsored_ids and v["id"] not in boosted_ids]
        # Merge: sponsored first, then boosted, then regular
        videos = sponsored + boosted + videos

    for v in videos:
        v["liked_by_me"] = v["id"] in liked_ids
        # make timestamps JSON serializable
        if v.get("created_at") and not isinstance(v["created_at"], str):
            v["created_at"] = v["created_at"].isoformat()
            
        # Hide worker pay rates from other workers/anonymous users
        if v["type"] == "worker":
            if not current_user or (current_user["role"] != "employer" and current_user["id"] != v["user_id"]):
                v["pay_rate"] = ""

    return videos


@api.post("/videos")
def create_video(
    type: str = Form(...),
    title: str = Form(""),
    video_url: str = Form(""),
    image_url: str = Form(""),
    post_type: str = Form("video"),
    category: str = Form("general"),
    price: str = Form(""),
    event_date: str = Form(""),
    event_time: str = Form(""),
    scheduled_at: str = Form(""),
    aspect_ratio: str = Form("9:16"),
    description: str = Form(""),
    cuisine_type: str = Form(""),
    pay_rate: str = Form(""),
    hours: str = Form(""),
    experience_level: str = Form(""),
    location: str = Form(""),
    current_user=Depends(get_current_user),
):
    # Validate: must have at least some content
    has_media = bool(video_url or image_url)
    has_text = bool(title.strip() or description.strip())
    if not has_media and not has_text:
        raise HTTPException(400, "Post must have a title, description, image, or video")

    # Validate aspect ratio
    if aspect_ratio not in ("9:16", "1:1", "4:5", "16:9"):
        aspect_ratio = "9:16"

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO videos (user_id, video_url, image_url, type, post_type, category, price, event_date, event_time, scheduled_at, aspect_ratio, title, description, cuisine_type, pay_rate, hours, experience_level, location)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (current_user["id"], video_url or None, image_url or None, type, post_type, category, price, event_date, event_time, scheduled_at or None, aspect_ratio, title or None, description, cuisine_type, pay_rate, hours, experience_level, location),
        )
        video = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()

    if video.get("created_at"):
        video["created_at"] = video["created_at"].isoformat()
    if video.get("scheduled_at"):
        video["scheduled_at"] = video["scheduled_at"].isoformat()
    return video


@api.post("/videos/{video_id}/like")
def toggle_like(video_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM likes WHERE user_id=%s AND video_id=%s", (current_user["id"], video_id))
        existing = cur.fetchone()
        if existing:
            cur.execute("DELETE FROM likes WHERE user_id=%s AND video_id=%s", (current_user["id"], video_id))
            cur.execute("UPDATE videos SET likes = likes - 1 WHERE id = %s RETURNING likes", (video_id,))
            liked = False
        else:
            cur.execute("INSERT INTO likes (user_id, video_id) VALUES (%s, %s)", (current_user["id"], video_id))
            cur.execute("UPDATE videos SET likes = likes + 1 WHERE id = %s RETURNING likes", (video_id,))
            liked = True
        row = cur.fetchone()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()
    return {"liked": liked, "likes": row["likes"] if row else 0}


@api.patch("/videos/{video_id}")
async def update_video(
    video_id: int,
    title: str = Form(None),
    description: str = Form(None),
    repost: str = Form("false"),
    category: str = Form(None),
    price: str = Form(None),
    event_date: str = Form(None),
    event_time: str = Form(None),
    aspect_ratio: str = Form(None),
    file: UploadFile = File(None),
    current_user=Depends(get_current_user),
):
    conn = get_conn()
    cur = conn.cursor()
    try:
        # verify ownership
        cur.execute("SELECT user_id FROM videos WHERE id = %s", (video_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Video not found")
        if row["user_id"] != current_user["id"]:
            raise HTTPException(403, "Not authorized to edit this post")

        updates = []
        params = []
        
        if file is not None and file.filename:
            ext = Path(file.filename).suffix.lower()
            if ext in (".mp4", ".mov", ".webm"):
                new_filename = f"vid_{uuid.uuid4()}{ext}"
                dest = UPLOAD_DIR / new_filename
                content = await file.read()
                async with aiofiles.open(dest, "wb") as f:
                    await f.write(content)
                updates.append("video_url = %s")
                params.append(f"/api/media/{new_filename}")
                updates.append("image_url = NULL")
            elif ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                new_filename = f"img_{uuid.uuid4()}{ext}"
                dest = UPLOAD_DIR / new_filename
                content = await file.read()
                async with aiofiles.open(dest, "wb") as f:
                    await f.write(content)
                updates.append("image_url = %s")
                params.append(f"/api/media/{new_filename}")
                updates.append("video_url = NULL")
        
        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if category is not None:
            updates.append("category = %s")
            params.append(category)
        if price is not None:
            updates.append("price = %s")
            params.append(price)
        if event_date is not None:
            updates.append("event_date = %s")
            params.append(event_date)
        if event_time is not None:
            updates.append("event_time = %s")
            params.append(event_time)
        if aspect_ratio is not None and aspect_ratio in ("9:16", "1:1", "4:5", "16:9"):
            updates.append("aspect_ratio = %s")
            params.append(aspect_ratio)
            
        if str(repost).lower() == "true":
            updates.append("created_at = CURRENT_TIMESTAMP")

        if not updates:
            return {"ok": True}

        params.append(video_id)
        
        cur.execute(f"UPDATE videos SET {', '.join(updates)} WHERE id = %s RETURNING *", tuple(params))
        video = dict(cur.fetchone())
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()
    
    if video.get("created_at"):
        video["created_at"] = video["created_at"].isoformat()
    return video


@api.delete("/videos/{video_id}")
def delete_video(video_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM videos WHERE id = %s", (video_id,))
    video = cur.fetchone()
    if not video:
        raise HTTPException(404, "Video not found")
    if video["user_id"] != current_user["id"]:
        raise HTTPException(403, "Not your video")
    cur.execute("DELETE FROM videos WHERE id = %s", (video_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted": True}
