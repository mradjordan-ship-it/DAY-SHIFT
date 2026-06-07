"""Sponsor / donor / supporter contact routes for Day Shift Marketplace."""
from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, require_admin

api = APIRouter()


@api.post("/contact/sponsor")
def sponsor_contact(body: dict):
    """Public endpoint — no auth required. For sponsors, donors, supporters."""
    name = body.get("name", "").strip()
    email = body.get("email", "").strip()
    phone = body.get("phone", "").strip()
    message = body.get("message", "").strip()

    if not name or not email or not phone or not message:
        raise HTTPException(400, "Name, email, phone, and message are required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO sponsor_contacts (name, email, phone, message) VALUES (%s, %s, %s, %s) RETURNING *",
            (name, email, phone, message),
        )
        row = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()

    if row.get("created_at"):
        row["created_at"] = row["created_at"].isoformat()
    return {"ok": True, "id": row["id"]}


@api.get("/admin/sponsors")
def admin_list_sponsors(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT sc.*,
                  (SELECT COUNT(*) FROM sponsor_replies WHERE contact_id = sc.id) as reply_count
           FROM sponsor_contacts sc ORDER BY sc.created_at DESC"""
    )
    contacts = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for c in contacts:
        if c.get("created_at"):
            c["created_at"] = c["created_at"].isoformat()
    return contacts


@api.get("/admin/sponsors/{contact_id}/replies")
def admin_get_sponsor_replies(contact_id: int, admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT sr.*, u.name as admin_name
           FROM sponsor_replies sr JOIN users u ON sr.admin_id = u.id
           WHERE sr.contact_id = %s ORDER BY sr.created_at ASC""",
        (contact_id,),
    )
    replies = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for r in replies:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return replies


@api.post("/admin/sponsors/{contact_id}/replies")
def admin_reply_sponsor(contact_id: int, body: dict, admin=Depends(require_admin)):
    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(400, "Reply is required")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO sponsor_replies (contact_id, admin_id, content) VALUES (%s, %s, %s) RETURNING *",
            (contact_id, admin["id"], content),
        )
        reply = dict(cur.fetchone())
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()
    if reply.get("created_at"):
        reply["created_at"] = reply["created_at"].isoformat()
    reply["admin_name"] = admin["name"]
    return reply
