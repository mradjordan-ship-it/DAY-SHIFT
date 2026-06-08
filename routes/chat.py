"""Chat / message routes for Day Shift Marketplace."""
from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, get_current_user
from .models import MessageBody

api = APIRouter()


@api.get("/matches/{match_id}/messages")
def get_messages(match_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id=%s AND (worker_id=%s OR employer_id=%s)",
                (match_id, current_user["id"], current_user["id"]))
    match = cur.fetchone()
    if not match:
        raise HTTPException(403, "Not part of this match")
    if dict(match)["status"] == "pending":
        raise HTTPException(400, "Messages are available after the match is accepted")

    cur.execute(
        """SELECT m.*, u.name as sender_name, u.avatar_url as sender_avatar
           FROM messages m JOIN users u ON m.sender_id = u.id
           WHERE m.match_id = %s ORDER BY m.created_at ASC""",
        (match_id,),
    )
    msgs = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for m in msgs:
        if m.get("created_at"):
            m["created_at"] = m["created_at"].isoformat()
    return msgs


@api.post("/matches/{match_id}/messages")
def send_message(match_id: int, body: MessageBody, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM matches WHERE id=%s AND (worker_id=%s OR employer_id=%s)",
                (match_id, current_user["id"], current_user["id"]))
    match = cur.fetchone()
    if not match:
        raise HTTPException(403, "Not part of this match")
    if dict(match)["status"] == "pending":
        raise HTTPException(400, "Messages are available after the match is accepted")

    try:
        cur.execute(
            "INSERT INTO messages (match_id, sender_id, content) VALUES (%s, %s, %s) RETURNING *",
            (match_id, current_user["id"], body.content),
        )
        msg = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    if msg.get("created_at"):
        msg["created_at"] = msg["created_at"].isoformat()
    msg["sender_name"] = current_user["name"]
    msg["sender_avatar"] = current_user["avatar_url"]

    # Send push notification to the other party
    try:
        from .push import send_push_to_user
        match_dict = dict(match)
        other_id = match_dict["employer_id"] if current_user["id"] == match_dict["worker_id"] else match_dict["worker_id"]
        # Truncate long messages for the notification
        preview = body.content[:80] + ("…" if len(body.content) > 80 else "")
        send_push_to_user(other_id, f"{current_user['name']}", preview, f"/chat?matchId={match_id}")
    except Exception:
        pass  # Don't fail the message if push fails

    return msg


@api.post("/messages/{message_id}/read")
def mark_read(message_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE messages SET read=TRUE WHERE id=%s AND sender_id!=%s",
        (message_id, current_user["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}
