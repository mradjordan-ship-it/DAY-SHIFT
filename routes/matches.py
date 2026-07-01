"""Match routes for Day Shift Marketplace."""
import json
import os
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from google import genai
from google.genai import types

from .deps import get_conn, get_current_user
from .models import MatchBody, ReviewBody

api = APIRouter()


def _parse_time_range(event_time: str) -> tuple | None:
    """Parse event_time into (start_minutes, end_minutes) or None.

    Handles: '9am-5pm', '14:00-22:00', '8:00 AM - 4:00 PM', '9:00-17:00'
    Returns None if unparseable or empty.
    """
    if not event_time or not event_time.strip():
        return None
    t = event_time.strip().lower()
    parts = re.split(r'\s*[-–—to]+\s*', t, maxsplit=1)
    if len(parts) != 2:
        return None

    def _to_minutes(s: str) -> int | None:
        s = s.strip().lower()
        m = re.match(r'^(\d{1,2}):(\d{2})$', s)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', s)
        if m:
            h = int(m.group(1))
            mins = int(m.group(2)) if m.group(2) else 0
            if m.group(3) == 'pm' and h != 12:
                h += 12
            if m.group(3) == 'am' and h == 12:
                h = 0
            return h * 60 + mins
        return None

    start = _to_minutes(parts[0])
    end = _to_minutes(parts[1])
    if start is None or end is None:
        return None
    return (start, end)


def _times_overlap(a: tuple, b: tuple) -> bool:
    """Check if two (start_min, end_min) ranges overlap, handling overnight shifts.

    For overnight shifts where start > end (e.g. 10pm=1320 to 6am=360),
    end is treated as wrapping to the next day by adding 1440 minutes.
    """
    a_start, a_end = a
    b_start, b_end = b
    if a_start > a_end:
        a_end += 1440
    if b_start > b_end:
        b_end += 1440
    return max(a_start, b_start) < min(a_end, b_end)


# ── AI Match Ranking (must be before /matches/{match_id}) ────────────────
MAX_AI_RETRIES = 3


def _get_ai_client() -> genai.Client:
    return genai.Client(
        api_key=os.environ.get("STRIPE_GOOGLE_API_KEY"),
        http_options={
            "api_version": "v1alpha",
            "base_url": os.environ.get("STRIPE_GOOGLE_BASE_URL"),
        },
    )


def _call_ai_with_retry(prompt: str, schema: dict) -> dict:
    for attempt in range(1, MAX_AI_RETRIES + 1):
        try:
            client = _get_ai_client()
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=types.Schema(**schema),
                ),
            )
            raw = response.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)

            for key in schema.get("properties", {}):
                if key in schema.get("required", []) and key not in data:
                    raise ValueError(f"Missing required key: {key}")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[AI-MATCH] Attempt {attempt}/{MAX_AI_RETRIES} parse/validation error: {e}")
            if attempt == MAX_AI_RETRIES:
                raise HTTPException(
                    502,
                    f"AI returned invalid data after {MAX_AI_RETRIES} attempts.",
                )
        except Exception as e:
            err_str = str(e).lower()
            print(f"[AI-MATCH] Attempt {attempt}/{MAX_AI_RETRIES} failed: {type(e).__name__}: {e}")
            if "rate" in err_str or "quota" in err_str or "429" in err_str:
                raise HTTPException(429, "AI rate limit — please wait and retry.")
            if attempt == MAX_AI_RETRIES:
                raise HTTPException(502, f"AI error: {type(e).__name__}")
    raise HTTPException(502, "AI match ranking failed.")


MATCH_RANK_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "matches": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "video_id": {"type": "INTEGER"},
                    "title": {"type": "STRING"},
                    "score": {"type": "NUMBER"},
                    "reasoning": {"type": "STRING"},
                },
                "required": ["video_id", "title", "score", "reasoning"],
            },
        },
    },
    "required": ["matches"],
}


@api.get("/matches/rank")
async def rank_matches(current_user=Depends(get_current_user)):
    """AI-ranked best-fit shifts for the current worker.

    Fetches worker profile + open employer shifts, returns top 3 ranked matches
    with AI reasoning.
    """
    if os.environ.get("AI_ENABLED", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(503, "AI features are currently disabled.")
    try:
        conn = get_conn()
        cur = conn.cursor()
        uid = current_user["id"]

        cur.execute(
            """SELECT id, name, bio, role, avg_rating, total_shifts, avatar_url
               FROM users WHERE id = %s""",
            (uid,),
        )
        worker = cur.fetchone()
        if not worker:
            raise HTTPException(404, "Worker profile not found")
        worker = dict(worker)

        cur.execute(
            """SELECT type, title, description, category, price as pay_rate,
                      location, event_date, event_time
               FROM videos WHERE user_id = %s
               ORDER BY created_at DESC LIMIT 10""",
            (uid,),
        )
        worker_videos = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT v.id, v.title, v.description, v.category, v.price as pay_rate,
                      v.location, v.event_date, v.event_time, u.name as employer_name,
                      u.avg_rating as employer_rating
               FROM videos v
               JOIN users u ON v.user_id = u.id
               WHERE v.type = 'employer'
                 AND v.user_id != %s
                 AND COALESCE(NULLIF(v.event_date, ''), '2099-12-31')::date >= CURRENT_DATE
               ORDER BY v.created_at DESC LIMIT 30""",
            (uid,),
        )
        shifts = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI-MATCH] DB error: {type(e).__name__}: {e}")
        raise HTTPException(500, f"Database error: {e}")

    if not shifts:
        return {"ok": True, "matches": [], "message": "No open shifts available."}

    worker_context = json.dumps({
        "name": worker.get("name", ""),
        "bio": worker.get("bio", "") or "",
        "role": worker.get("role", ""),
        "rating": float(worker.get("avg_rating") or 0),
        "total_shifts": worker.get("total_shifts", 0),
        "videos": [
            {"type": v.get("type"), "title": v.get("title"),
             "category": v.get("category"), "pay_rate": v.get("pay_rate")}
            for v in worker_videos
        ],
    }, indent=2, default=str)

    shifts_context = json.dumps([
        {
            "id": s["id"], "title": s.get("title", "Untitled Shift"),
            "description": s.get("description", "")[:300],
            "category": s.get("category"), "pay_rate": s.get("pay_rate"),
            "location": s.get("location"),
            "event_date": str(s.get("event_date")) if s.get("event_date") else None,
            "event_time": s.get("event_time"),
            "employer": s.get("employer_name"),
            "employer_rating": float(s.get("employer_rating") or 0),
        }
        for s in shifts
    ], indent=2, default=str)

    prompt = (
        f"You are an expert culinary job matcher for Day Shift.\n\n"
        f"WORKER PROFILE:\n{worker_context}\n\n"
        f"AVAILABLE SHIFTS:\n{shifts_context}\n\n"
        f"Return the top 3 best-fit shifts (score 0-100). "
        f"Scoring: role alignment 40%, pay 20%, schedule 20%, reputation 20%. "
        f"One-sentence reasoning per match. Skip scores below 30."
    )

    result = _call_ai_with_retry(prompt, MATCH_RANK_SCHEMA)
    matches = result.get("matches", [])

    valid_matches = []
    seen_ids = set()
    for m in matches[:3]:
        try:
            vid = int(m.get("video_id", 0))
            if vid <= 0 or vid in seen_ids:
                continue
            seen_ids.add(vid)
            score = max(0.0, min(100.0, float(m.get("score", 0))))
            valid_matches.append({
                "video_id": vid,
                "title": str(m.get("title", "Untitled Shift"))[:200],
                "score": round(score, 1),
                "reasoning": str(m.get("reasoning", "Good match."))[:500],
            })
        except (TypeError, ValueError, KeyError):
            continue

    return {"ok": True, "matches": valid_matches, "total_shifts_analyzed": len(shifts)}


@api.get("/matches")
def list_matches(current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    uid = current_user["id"]
    cur.execute(
        """SELECT m.*,
            w.name as worker_name, w.avatar_url as worker_avatar,
            e.name as employer_name, e.avatar_url as employer_avatar,
            ev.location as employer_location
           FROM matches m
           JOIN users w ON m.worker_id = w.id
           JOIN users e ON m.employer_id = e.id
           LEFT JOIN videos ev ON m.employer_video_id = ev.id
           WHERE m.worker_id = %s OR m.employer_id = %s
           ORDER BY m.created_at DESC""",
        (uid, uid),
    )
    matches = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for m in matches:
        if m.get("created_at"):
            m["created_at"] = m["created_at"].isoformat()
    return matches


@api.post("/matches")
def create_match(body: MatchBody, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()

    # Determine worker and employer from the current user and the target video
    # At least one video ID must be provided
    worker_video_id = body.worker_video_id
    employer_video_id = body.employer_video_id

    worker_id = None
    employer_id = None

    if employer_video_id:
        cur.execute("SELECT user_id, type FROM videos WHERE id = %s", (employer_video_id,))
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(404, "Spot video not found")
        employer_id = ev["user_id"]

    if worker_video_id:
        cur.execute("SELECT user_id, type FROM videos WHERE id = %s", (worker_video_id,))
        wv = cur.fetchone()
        if not wv:
            raise HTTPException(404, "Crew video not found")
        worker_id = wv["user_id"]

    # If only one video provided, the current user is the other party
    if worker_video_id and not employer_video_id:
        # Worker liked an employer's post but had no video to attach
        employer_id = None  # we need to figure it out from context
        # Current user is the worker
        worker_id_from_video = worker_id
        if current_user["role"] == "worker":
            worker_id = current_user["id"]
            # Find the employer from the video
            employer_id = None  # still unknown without a video
        else:
            worker_id = worker_id_from_video
            employer_id = current_user["id"]
    elif employer_video_id and not worker_video_id:
        # Employer liked a worker's post but had no video to attach
        if current_user["role"] == "employer":
            employer_id = employer_id  # already set from video query
            worker_id = None  # need to find from video
        else:
            worker_id = current_user["id"]

    # Simpler approach: use the video to find the other user, current user is the initiator
    # Re-derive cleanly
    if employer_video_id and not worker_video_id:
        # Current user saw an employer video → current user is the worker
        worker_id = current_user["id"]
        # employer_id already set from video query above
    elif worker_video_id and not employer_video_id:
        # Current user saw a worker video → current user is the employer
        employer_id = current_user["id"]
        # worker_id already set from video query above

    if not worker_id or not employer_id:
        raise HTTPException(400, "Could not determine match participants")

    if worker_id == employer_id:
        raise HTTPException(400, "Cannot match with yourself")

    # Block check — either party can block the other
    cur.execute(
        "SELECT 1 FROM user_blocks WHERE (blocker_id=%s AND blocked_id=%s) OR (blocker_id=%s AND blocked_id=%s)",
        (worker_id, employer_id, employer_id, worker_id),
    )
    if cur.fetchone():
        raise HTTPException(403, "Cannot match with this user")

    # Check for duplicate — same worker, employer, and video pair
    dup_sql = """SELECT id FROM matches WHERE worker_id=%s AND employer_id=%s AND status != 'cancelled'"""
    dup_params = [worker_id, employer_id]
    if employer_video_id:
        dup_sql += " AND employer_video_id=%s"
        dup_params.append(employer_video_id)
    if worker_video_id:
        dup_sql += " AND worker_video_id=%s"
        dup_params.append(worker_video_id)
    cur.execute(dup_sql, tuple(dup_params))
    if cur.fetchone():
        raise HTTPException(400, "Match already exists for this shift")

    # Check for overlapping shifts: worker already has active/pending match on same date
    new_date = None
    new_time = None
    if employer_video_id:
        cur.execute("SELECT event_date, event_time FROM videos WHERE id = %s", (employer_video_id,))
        new_evt = cur.fetchone()
        if new_evt:
            new_date = new_evt["event_date"]
            new_time = new_evt["event_time"]
    elif worker_video_id:
        cur.execute("SELECT event_date, event_time FROM videos WHERE id = %s", (worker_video_id,))
        new_evt = cur.fetchone()
        if new_evt:
            new_date = new_evt["event_date"]
            new_time = new_evt["event_time"]

    if new_date and new_date.strip():
        # Fetch all active/pending matches for this worker on the same date
        cur.execute(
            """SELECT m.id, v.title, v.event_date, v.event_time, u.name as employer_name
               FROM matches m
               JOIN videos v ON v.id IN (m.employer_video_id, m.worker_video_id)
               JOIN users u ON m.employer_id = u.id
               WHERE m.worker_id = %s
                 AND m.status IN ('pending', 'active')
                 AND v.event_date = %s""",
            (worker_id, new_date),
        )
        existing_matches = [dict(r) for r in cur.fetchall()]

        new_range = _parse_time_range(new_time or "")

        for existing in existing_matches:
            existing_range = _parse_time_range(existing.get("event_time") or "")

            if new_range and existing_range:
                # Both have time ranges — only reject if times actually overlap
                if _times_overlap(new_range, existing_range):
                    raise HTTPException(
                        409,
                        f"Time conflict: \"{new_time}\" overlaps with your existing shift "
                        f"\"{existing['title']}\" ({existing.get('event_time')}) on {new_date}. "
                        f"Cancel it before applying."
                    )
                # Same date but different time slots — allow
            else:
                # Can't parse times — reject conservatively (same date = potential overlap)
                raise HTTPException(
                    409,
                    f"You already have a shift on {new_date} (\"{existing['title']}\"). "
                    f"Cancel it before applying for another shift on the same date."
                )

    try:
        cur.execute(
            """INSERT INTO matches (worker_id, employer_id, worker_video_id, employer_video_id, status, initiated_by)
               VALUES (%s, %s, %s, %s, 'pending', %s) RETURNING *""",
            (worker_id, employer_id, worker_video_id, employer_video_id, current_user["id"]),
        )
        match = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    # Send push notification to the other party
    try:
        from .push import send_push_to_user
        other_id = employer_id if current_user["id"] == worker_id else worker_id
        send_push_to_user(other_id, "New Match Request 🧡", f"{current_user['name']} wants to connect!", "/matches")
    except Exception:
        pass  # Don't fail the match if push fails

    if match.get("created_at"):
        match["created_at"] = match["created_at"].isoformat()
    return match


@api.post("/matches/{match_id}/confirm")
def confirm_match(match_id: int, current_user=Depends(get_current_user)):
    """Both parties confirming shift completion."""
    conn = get_conn()
    cur = conn.cursor()
    # Use FOR UPDATE to lock the row and prevent race conditions
    cur.execute("SELECT * FROM matches WHERE id = %s FOR UPDATE", (match_id,))
    match = cur.fetchone()
    if not match:
        conn.rollback()
        raise HTTPException(404, "Match not found")
    match = dict(match)

    uid = current_user["id"]
    if uid == match["worker_id"]:
        cur.execute("UPDATE matches SET worker_confirmed=TRUE WHERE id=%s RETURNING worker_confirmed, employer_confirmed", (match_id,))
    elif uid == match["employer_id"]:
        cur.execute("UPDATE matches SET employer_confirmed=TRUE WHERE id=%s RETURNING worker_confirmed, employer_confirmed", (match_id,))
    else:
        conn.rollback()
        raise HTTPException(403, "Not part of this match")

    updated = dict(cur.fetchone())
    # If both are now confirmed, mark as completed
    if updated["worker_confirmed"] and updated["employer_confirmed"]:
        cur.execute("UPDATE matches SET status='completed' WHERE id=%s", (match_id,))
        # Update user stats
        cur.execute("UPDATE users SET total_shifts = total_shifts + 1 WHERE id IN (%s, %s)", (match["worker_id"], match["employer_id"]))

    conn.commit()
    cur.close()
    conn.close()
    return {"confirmed": True, "both_confirmed": updated["worker_confirmed"] and updated["employer_confirmed"]}


@api.post("/matches/{match_id}/accept")
def accept_match(match_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id=%s FOR UPDATE", (match_id,))
    match = cur.fetchone()
    if not match:
        conn.rollback()
        raise HTTPException(404, "Match not found")
    match = dict(match)
    uid = current_user["id"]
    if uid not in (match["worker_id"], match["employer_id"]):
        conn.rollback()
        raise HTTPException(403, "Not part of this match")
    if match["status"] != "pending":
        raise HTTPException(400, f"Match is {match['status']}, not pending")
    if uid == match["initiated_by"]:
        raise HTTPException(400, "You initiated this match — wait for the other person to accept")
    cur.execute("UPDATE matches SET status='active' WHERE id=%s", (match_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "active"}


@api.post("/matches/{match_id}/decline")
def decline_match(match_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id=%s", (match_id,))
    match = cur.fetchone()
    if not match:
        raise HTTPException(404, "Match not found")
    match = dict(match)
    uid = current_user["id"]
    if uid not in (match["worker_id"], match["employer_id"]):
        conn.rollback()
        raise HTTPException(403, "Not part of this match")
    if match["status"] != "pending":
        conn.rollback()
        raise HTTPException(400, f"Match is {match['status']}, not pending")
    if uid == match["initiated_by"]:
        conn.rollback()
        raise HTTPException(400, "You initiated this match — you can cancel it instead")
    cur.execute("UPDATE matches SET status='cancelled' WHERE id=%s", (match_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "cancelled"}


@api.post("/matches/{match_id}/cancel")
def cancel_match(match_id: int, current_user=Depends(get_current_user)):
    """Initiator can cancel their pending match request."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id=%s FOR UPDATE", (match_id,))
    match = cur.fetchone()
    if not match:
        conn.rollback()
        raise HTTPException(404, "Match not found")
    match = dict(match)
    uid = current_user["id"]
    if uid not in (match["worker_id"], match["employer_id"]):
        raise HTTPException(403, "Not part of this match")
    if match["status"] != "pending":
        raise HTTPException(400, f"Match is {match['status']}, can only cancel pending matches")
    cur.execute("UPDATE matches SET status='cancelled' WHERE id=%s", (match_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "cancelled"}


@api.get("/matches/{match_id}")
def get_match(match_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT m.*,
            w.name as worker_name, w.avatar_url as worker_avatar,
            e.name as employer_name, e.avatar_url as employer_avatar
           FROM matches m
           JOIN users w ON m.worker_id = w.id
           JOIN users e ON m.employer_id = e.id
           WHERE m.id = %s AND (m.worker_id = %s OR m.employer_id = %s)""",
        (match_id, current_user["id"], current_user["id"]),
    )
    match = cur.fetchone()
    cur.close()
    conn.close()
    if not match:
        raise HTTPException(404, "Match not found")
    match = dict(match)
    if match.get("created_at"):
        match["created_at"] = match["created_at"].isoformat()
    return match


@api.post("/matches/{match_id}/review/{reviewee_id}")
def review_match(match_id: int, reviewee_id: int, body: ReviewBody, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id=%s AND status='completed'", (match_id,))
    match = cur.fetchone()
    if not match:
        raise HTTPException(400, "Match not completed yet")
    uid = current_user["id"]
    if uid not in (match["worker_id"], match["employer_id"]):
        raise HTTPException(403, "Not part of this match")

    try:
        cur.execute(
            "INSERT INTO reviews (match_id, reviewer_id, reviewee_id, rating, feedback) VALUES (%s,%s,%s,%s,%s)",
            (match_id, uid, reviewee_id, body.rating, body.feedback),
        )
        # Update avg rating on reviewee
        cur.execute(
            """UPDATE users SET avg_rating = (
                SELECT AVG(rating) FROM reviews WHERE reviewee_id = %s
               ), total_shifts = total_shifts + 1
               WHERE id = %s""",
            (reviewee_id, reviewee_id),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        if "unique" in str(e).lower():
            raise HTTPException(400, "Already reviewed this match")
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    return {"ok": True}
