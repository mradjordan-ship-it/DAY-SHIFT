"""Sponsor / donor / supporter contact routes for Day Shift Marketplace."""
import os
import logging
from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, require_admin
from .sanitize import sanitize_email_body

logger = logging.getLogger(__name__)

# Contact email & phone for Day Shift
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "contact@dayshiftnow.me")
CONTACT_PHONE = os.environ.get("CONTACT_PHONE", "")

api = APIRouter()


def _send_contact_email(name: str, email: str, phone: str, message: str):
    """Send a real email to Day Shift when someone uses the contact form."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.info("[Contact] No RESEND_API_KEY — skipping email notification")
        return

    try:
        import resend
        resend.api_key = api_key

        safe_name = sanitize_email_body(name)
        safe_email = sanitize_email_body(email)
        safe_phone = sanitize_email_body(phone)
        safe_message = sanitize_email_body(message)

        resend.Emails.send({
            "from": f"Day Shift <{CONTACT_EMAIL}>",
            "to": [CONTACT_EMAIL],
            "reply_to": email,
            "subject": f"New Contact Message from {safe_name}",
            "html": f"""
                <div style="font-family:-apple-system,sans-serif;max-width:480px;margin:auto;padding:20px;">
                    <h2 style="color:#f97316;">📬 New Contact Message</h2>
                    <table style="width:100%;border-collapse:collapse;">
                        <tr><td style="padding:8px 0;color:#71717a;font-weight:600;">Name:</td><td>{safe_name}</td></tr>
                        <tr><td style="padding:8px 0;color:#71717a;font-weight:600;">Email:</td><td><a href="mailto:{safe_email}">{safe_email}</a></td></tr>
                        <tr><td style="padding:8px 0;color:#71717a;font-weight:600;">Phone:</td><td><a href="tel:{safe_phone}">{safe_phone}</a></td></tr>
                    </table>
                    <div style="background:#18181b;border-radius:12px;padding:16px;margin-top:16px;">
                        <p style="margin:0;color:#fafafa;white-space:pre-wrap;">{safe_message}</p>
                    </div>
                    <p style="margin-top:16px;color:#52525b;font-size:12px;">Sent from Day Shift app</p>
                </div>
            """,
            "text": f"New Contact Message from {name}\n\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}\n\n— Day Shift App",
        })
        logger.info(f"[Contact] Email sent to {CONTACT_EMAIL} from {name}")
    except Exception as e:
        logger.error(f"[Contact] Failed to send email: {e}")
        # Don't fail the request — DB save already succeeded


@api.post("/contact/sponsor")
def sponsor_contact(body: dict):
    """Public endpoint — no auth required. For sponsors, donors, supporters.

    Saves to DB AND sends a real email to Day Shift.
    """
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
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    # Send real email notification
    _send_contact_email(name, email, phone, message)

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
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()
    if reply.get("created_at"):
        reply["created_at"] = reply["created_at"].isoformat()
    reply["admin_name"] = admin["name"]
    return reply
