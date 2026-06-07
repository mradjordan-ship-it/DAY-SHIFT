"""Support / contact routes for Day Shift Marketplace."""
from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, get_current_user, require_admin
from .models import AUTO_REPLY

api = APIRouter()


@api.post("/support")
def create_support_thread(body: dict, current_user=Depends(get_current_user)):
    """User sends a message to admin. Creates a thread or adds to existing open thread."""
    subject = body.get("subject", "").strip()
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(400, "Message is required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Find or create an open thread for this user
        cur.execute(
            "SELECT id FROM support_threads WHERE user_id = %s AND status = 'open' ORDER BY updated_at DESC LIMIT 1",
            (current_user["id"],),
        )
        thread = cur.fetchone()

        if thread:
            thread_id = thread["id"]
            cur.execute("UPDATE support_threads SET updated_at = NOW() WHERE id = %s", (thread_id,))
        else:
            cur.execute(
                "INSERT INTO support_threads (user_id, subject, status, source) VALUES (%s, %s, 'open', 'app') RETURNING id",
                (current_user["id"], subject or "Support Request"),
            )
            thread_id = cur.fetchone()["id"]

        # Insert user message
        cur.execute(
            "INSERT INTO support_messages (thread_id, sender_id, sender_role, content) VALUES (%s, %s, 'user', %s) RETURNING *",
            (thread_id, current_user["id"], message),
        )
        user_msg = dict(cur.fetchone())

        # Auto-reply from admin
        cur.execute(
            "INSERT INTO support_messages (thread_id, sender_id, sender_role, content) VALUES (%s, %s, 'auto', %s) RETURNING *",
            (thread_id, current_user["id"], AUTO_REPLY),
        )
        auto_msg = dict(cur.fetchone())

        conn.commit()

        for m in (user_msg, auto_msg):
            if m.get("created_at"):
                m["created_at"] = m["created_at"].isoformat()

        return {
            "thread_id": thread_id,
            "message": user_msg,
            "auto_reply": auto_msg,
        }
    finally:
        cur.close()
        conn.close()


@api.post("/support/guest")
def guest_support(body: dict):
    """Non-logged-in user sends a support message."""
    name = body.get("name", "").strip()
    email = body.get("email", "").strip()
    message = body.get("message", "").strip()
    if not message or not name or not email:
        raise HTTPException(400, "Name, email, and message are required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO support_threads (user_id, subject, status, source) VALUES (NULL, %s, 'open', 'guest') RETURNING id",
            (f"Guest: {name} ({email})",),
        )
        thread_id = cur.fetchone()["id"]

        cur.execute(
            "INSERT INTO support_messages (thread_id, sender_id, sender_role, content) VALUES (%s, NULL, 'user', %s)",
            (thread_id, f"[Guest] {name} ({email}):\n\n{message}"),
        )

        conn.commit()
        return {"status": "ok", "thread_id": thread_id}
    finally:
        cur.close()
        conn.close()


@api.get("/support")
def list_my_threads(current_user=Depends(get_current_user)):
    """User sees their own support threads."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, 
                  (SELECT content FROM support_messages WHERE thread_id = t.id ORDER BY created_at DESC LIMIT 1) as last_message,
                  (SELECT COUNT(*) FROM support_messages WHERE thread_id = t.id AND sender_role != 'user' AND sender_id != %s) as admin_replies
           FROM support_threads t
           WHERE t.user_id = %s
           ORDER BY t.updated_at DESC""",
        (current_user["id"], current_user["id"]),
    )
    threads = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for t in threads:
        if t.get("created_at"):
            t["created_at"] = t["created_at"].isoformat()
        if t.get("updated_at"):
            t["updated_at"] = t["updated_at"].isoformat()
    return threads


@api.get("/support/{thread_id}")
def get_thread_messages(thread_id: int, current_user=Depends(get_current_user)):
    """User gets messages in their thread."""
    conn = get_conn()
    cur = conn.cursor()
    # Verify ownership (or admin)
    cur.execute("SELECT user_id FROM support_threads WHERE id = %s", (thread_id,))
    thread = cur.fetchone()
    if not thread:
        raise HTTPException(404, "Thread not found")
    if thread["user_id"] != current_user["id"] and not current_user.get("is_admin"):
        raise HTTPException(403, "Not your thread")

    cur.execute(
        """SELECT sm.*, u.name as sender_name, u.avatar_url as sender_avatar
           FROM support_messages sm JOIN users u ON sm.sender_id = u.id
           WHERE sm.thread_id = %s
           ORDER BY sm.created_at ASC""",
        (thread_id,),
    )
    messages = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for m in messages:
        if m.get("created_at"):
            m["created_at"] = m["created_at"].isoformat()
    return messages


@api.post("/support/{thread_id}/reply")
def reply_to_thread(thread_id: int, body: dict, current_user=Depends(get_current_user)):
    """User or admin replies to a thread."""
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(400, "Message is required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id, status FROM support_threads WHERE id = %s", (thread_id,))
        thread = cur.fetchone()
        if not thread:
            raise HTTPException(404, "Thread not found")

        is_admin_user = current_user.get("is_admin", False)
        if thread["user_id"] != current_user["id"] and not is_admin_user:
            raise HTTPException(403, "Not your thread")

        sender_role = "admin" if is_admin_user else "user"

        # Reopen if closed and user replies
        if thread["status"] == "closed" and not is_admin_user:
            cur.execute("UPDATE support_threads SET status = 'open', updated_at = NOW() WHERE id = %s", (thread_id,))
        else:
            cur.execute("UPDATE support_threads SET updated_at = NOW() WHERE id = %s", (thread_id,))

        cur.execute(
            "INSERT INTO support_messages (thread_id, sender_id, sender_role, content) VALUES (%s, %s, %s, %s) RETURNING *",
            (thread_id, current_user["id"], sender_role, message),
        )
        msg = dict(cur.fetchone())
        conn.commit()

        if msg.get("created_at"):
            msg["created_at"] = msg["created_at"].isoformat()
        return msg
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()


@api.get("/admin/support")
def admin_list_threads(admin=Depends(require_admin)):
    """Admin sees all support threads."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, u.name as user_name, u.email as user_email, u.avatar_url as user_avatar,
                  (SELECT content FROM support_messages WHERE thread_id = t.id ORDER BY created_at DESC LIMIT 1) as last_message,
                  (SELECT created_at FROM support_messages WHERE thread_id = t.id ORDER BY created_at DESC LIMIT 1) as last_message_at,
                  (SELECT COUNT(*) FROM support_messages WHERE thread_id = t.id AND sender_role = 'user') as user_messages,
                  (SELECT COUNT(*) FROM support_messages WHERE thread_id = t.id AND sender_role = 'admin') as admin_replies
           FROM support_threads t
           JOIN users u ON t.user_id = u.id
           ORDER BY t.updated_at DESC""",
    )
    threads = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for t in threads:
        for k in ("created_at", "updated_at", "last_message_at"):
            if t.get(k):
                t[k] = t[k].isoformat()
    return threads


@api.post("/admin/support/{thread_id}/close")
def admin_close_thread(thread_id: int, admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE support_threads SET status = 'closed', updated_at = NOW() WHERE id = %s", (thread_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}
