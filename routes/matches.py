"""Match routes for Day Shift Marketplace."""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, get_current_user
from .models import MatchBody, ReviewBody

api = APIRouter()


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

    # Check for duplicate
    cur.execute(
        "SELECT id FROM matches WHERE worker_id=%s AND employer_id=%s AND status != 'cancelled'",
        (worker_id, employer_id),
    )
    if cur.fetchone():
        raise HTTPException(400, "Match already exists")

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
