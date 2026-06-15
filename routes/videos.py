"""Video routes for Day Shift Marketplace."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
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
        {"text": "I am not a chef. I am a cook. A chef is a title. A cook is a person who does the work.", "author": "Leah Chase", "photo": "https://upload.wikimedia.org/wikipedia/commons/1/14/LeahChaseAp08Crop.jpg"},
        {"text": "You don't have to cook fancy or complicated masterpieces — just good food from fresh ingredients.", "author": "Edna Lewis", "photo": "https://upload.wikimedia.org/wikipedia/en/9/9a/Photo_of_Edna_Regina_Lewis.jpg"},
        {"text": "I want every meal to be a celebration of who we are and where we come from.", "author": "Marcus Samuelsson", "photo": "https://upload.wikimedia.org/wikipedia/commons/6/6b/Marcus_Samuelsson_2022.jpg"},
        {"text": "Cooking is an art, but all art requires knowing something about the technique and materials.", "author": "Nina Simone", "photo": "https://upload.wikimedia.org/wikipedia/commons/8/8e/Nina_Simone14.JPG"},
        {"text": "Food is our common ground, a universal experience. Our stories live in the food we make.", "author": "Carla Hall", "photo": "https://upload.wikimedia.org/wikipedia/commons/4/45/Carla_Hall_Oct_09.JPG"},
        {"text": "I've been cooking since I was tall enough to reach the stove. The kitchen is where I found my voice.", "author": "Mashama Bailey", "photo": "https://upload.wikimedia.org/wikipedia/commons/8/8f/The_Grey%2C_Savannah_GA.jpg"},
        {"text": "When you know who you are and where you come from, your food tells that story.", "author": "Jerome Grant", "photo": "https://upload.wikimedia.org/wikipedia/commons/6/6b/Marcus_Samuelsson_2022.jpg"},
        {"text": "Every dish I create honors the hands that taught me — my grandmother, my mother, my community.", "author": "Kwame Onwuachi", "photo": "https://upload.wikimedia.org/wikipedia/commons/c/cc/Kwame_Onwuachi_5183194.jpg"},
        {"text": "The table is a meeting place, a place of nourishment and story and song.", "author": "Michael Twitty", "photo": "https://upload.wikimedia.org/wikipedia/commons/2/27/Michael_Twitty.jpg"},
        {"text": "I cook to preserve the legacy of those who came before me. Every recipe is a memory.", "author": "Briana Riddock", "photo": "https://cdn.apartmenttherapy.info/image/upload/f_auto,q_auto:eco,c_fill,g_auto,w_1500,ar_3:2/k%2FEdit%2F2019-08-Author-Profile-Photos%2Fbrianariddock"},
        {"text": "Soul food isn't just about the food. It's about the soul you put into it.", "author": "Patrick Clark", "photo": "https://www.foodandwine.com/thmb/PpjcaKfIjlLdYXEM3eEqmWQtQkM=/1500x0/filters:no_upscale():max_bytes(150000):strip_icc()/Patrick-Clark-FT-mag0719-51c60c46204f4b93b6d34215d016e93e.jpg"},
        {"text": "My cooking is an extension of my heritage. I carry my ancestors in every pot I stir.", "author": "JJ Johnson", "photo": "https://upload.wikimedia.org/wikipedia/commons/0/0e/Chef_JJ_Johnson.jpg"},
        {"text": "If you can't feed a hundred people, then feed just one. But do it with love.", "author": "Leah Chase", "photo": "https://upload.wikimedia.org/wikipedia/commons/1/14/LeahChaseAp08Crop.jpg"},
        {"text": "The beauty of Black foodways is that we made something from nothing and made it glorious.", "author": "Michael Twitty", "photo": "https://upload.wikimedia.org/wikipedia/commons/2/27/Michael_Twitty.jpg"},
        # ── Classic culinary & motivational quotes ──
        {"text": "The kitchen is a country in which there are always discoveries to be made.", "author": "Grimod de la Reynière", "photo": "https://upload.wikimedia.org/wikipedia/commons/7/77/Alexandre_Balthazar_Laurent_Grimod_de_La_Reyni%C3%A8re.jpg"},
        {"text": "People who love to eat are always the best people.", "author": "Julia Child", "photo": "https://upload.wikimedia.org/wikipedia/commons/c/c5/Julia_Child_1994.jpg"},
        {"text": "Cooking is like love. It should be entered into with abandon or not at all.", "author": "Harriet Van Horne", "photo": "https://c7.alamy.com/comp/HD7010/whats-the-story-panelist-and-newspaper-columnist-harriet-van-horne-HD7010.jpg"},
        {"text": "No one is born a great cook, one learns by doing.", "author": "Julia Child", "photo": "https://upload.wikimedia.org/wikipedia/commons/c/c5/Julia_Child_1994.jpg"},
        {"text": "A recipe has no soul. You, as the cook, must bring soul to the recipe.", "author": "Thomas Keller", "photo": "https://upload.wikimedia.org/wikipedia/commons/9/93/Thomas_Keller.jpg"},
        {"text": "Cooking is at once child's play and adult joy. And cooking done with care is an act of love.", "author": "Craig Claiborne", "photo": "https://upload.wikimedia.org/wikipedia/commons/5/5a/Craig_Claiborne%2C_Chef-Gormondiser_%28cropped%29.jpg"},
        {"text": "One cannot think well, love well, sleep well, if one has not dined well.", "author": "Virginia Woolf", "photo": "https://upload.wikimedia.org/wikipedia/commons/a/a6/Virginia_Woolf_1927.jpg"},
        {"text": "Food is symbolic of love when words are inadequate.", "author": "Alan D. Wolfelt", "photo": "https://d1ldvf68ux039x.cloudfront.net/thumbs/photos/2404/8340613/1000w_q95.jpg"},
        {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs", "photo": "https://upload.wikimedia.org/wikipedia/commons/5/54/Steve_Jobs.jpg"},
        {"text": "Hard work beats talent when talent doesn't work hard.", "author": "Tim Notke", "photo": "https://upload.wikimedia.org/wikipedia/commons/0/0e/Chef_JJ_Johnson.jpg"},
        {"text": "Hustle in silence, let your success make the noise.", "author": "Unknown", "photo": "https://upload.wikimedia.org/wikipedia/commons/4/45/Carla_Hall_Oct_09.JPG"},
        {"text": "The kitchen is the heart of every home.", "author": "Unknown", "photo": "https://upload.wikimedia.org/wikipedia/commons/1/14/LeahChaseAp08Crop.jpg"},
        {"text": "Do what you can, with what you have, where you are.", "author": "Theodore Roosevelt", "photo": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Theodore_Roosevelt_by_the_Pach_Bros.jpg"},
        {"text": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein", "photo": "https://upload.wikimedia.org/wikipedia/commons/1/10/Albert_Einstein_photo_1920.jpg"},
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
    cursor: Optional[str] = None,
    limit: int = 20,
    current_user=Depends(get_optional_user),
):
    # Clamp limit
    limit = max(1, min(limit, 50))

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

    # Exclude videos from blocked users
    if current_user:
        cur.execute("SELECT blocked_id FROM user_blocks WHERE blocker_id = %s", (current_user["id"],))
        blocked_ids = [r["blocked_id"] for r in cur.fetchall()]
        if blocked_ids:
            placeholders = ",".join(["%s"] * len(blocked_ids))
            query += f" AND v.user_id NOT IN ({placeholders})"
            params.extend(blocked_ids)

    # Cursor pagination: only return posts older than the cursor timestamp
    if cursor:
        try:
            from datetime import datetime as _dt
            cursor_dt = _dt.fromisoformat(cursor)
            query += " AND v.created_at < %s"
            params.append(cursor_dt)
        except (ValueError, TypeError):
            pass  # Invalid cursor — ignore and start from top

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
    query += " ORDER BY v.created_at DESC LIMIT %s"
    params.append(limit + 1)  # fetch one extra to know if there's a next page

    cur.execute(query, params)
    videos = [dict(r) for r in cur.fetchall()]

    # Determine if there's a next page
    has_more = len(videos) > limit
    if has_more:
        videos = videos[:limit]

    # Fetch active boosted posts and merge at the top (for the main "all" feed)
    if not type and (not category or category == "all") and not q and not user_id and not cursor:
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

    # Build next cursor from the last item's created_at
    next_cursor = None
    if has_more and videos:
        last_created = videos[-1].get("created_at")
        if last_created:
            next_cursor = last_created if isinstance(last_created, str) else last_created.isoformat()

    return {"videos": videos, "next_cursor": next_cursor, "has_more": has_more}


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

        # Auto-flag: if account is less than 1 hour old and this is their first video,
        # create an auto-flag report for admin review
        from datetime import timezone
        account_age = datetime.now(timezone.utc) - current_user["created_at"].replace(tzinfo=timezone.utc) if current_user.get("created_at") else None
        auto_flag_reason = None
        if account_age and account_age.total_seconds() < 3600:  # < 1 hour
            cur.execute("SELECT COUNT(*) FROM videos WHERE user_id = %s", (current_user["id"],))
            video_count = cur.fetchone()["count"]
            if video_count <= 1:  # First video
                auto_flag_reason = "Auto-flagged: first post from new account (<1hr old)"

        # Check for profanity in title/description
        PROFANITY_LIST = ["fuck", "shit", "bitch", "asshole", "nigger", "nigga", "cunt", "dick", "pussy", "fag"]
        text_to_check = f"{title or ''} {description}".lower()
        found_profanity = [w for w in PROFANITY_LIST if w in text_to_check]
        if found_profanity:
            auto_flag_reason = f"Auto-flagged: profanity detected ({found_profanity[0]})"

        if auto_flag_reason:
            cur.execute(
                """INSERT INTO reports (reporter_id, target_type, target_id, reason, comment, status)
                   VALUES (NULL, 'video', %s, 'auto-flagged', %s, 'open')""",
                (video["id"], auto_flag_reason),
            )
            # Notify admins via push
            try:
                from .push import send_push_to_users
                cur.execute("SELECT id FROM users WHERE is_admin = TRUE")
                admin_ids = [r["id"] for r in cur.fetchall()]
                if admin_ids:
                    send_push_to_users(admin_ids, "Content Flagged 🚨", auto_flag_reason, "/admin")
            except Exception:
                pass

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
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
    # Verify video exists
    cur.execute("SELECT id FROM videos WHERE id = %s", (video_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(404, "Video not found")
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
        raise HTTPException(500, "Internal error — please try again")
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
                # Save raw upload first
                raw_filename = f"raw_{uuid.uuid4()}{ext}"
                raw_dest = UPLOAD_DIR / raw_filename
                content = await file.read()
                async with aiofiles.open(raw_dest, "wb") as f:
                    await f.write(content)
                # Transcode to H.264 MP4 for cross-device playback
                final_filename = f"vid_{uuid.uuid4()}.mp4"
                final_dest = UPLOAD_DIR / final_filename
                ok = await transcode_video(raw_dest, final_dest)
                if ok:
                    raw_dest.unlink(missing_ok=True)
                    updates.append("video_url = %s")
                    params.append(f"/api/media/{final_filename}")
                else:
                    # Fallback: serve raw but warn
                    print(f"[FFmpeg] transcode failed in PATCH, serving raw: {raw_filename}")
                    updates.append("video_url = %s")
                    params.append(f"/api/media/{raw_filename}")
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
        raise HTTPException(500, "Internal error — please try again")
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
