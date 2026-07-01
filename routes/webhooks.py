"""Webhook routes for Day Shift Marketplace."""
import os
import json
import logging
import base64
import email as email_lib
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import smtplib

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

api = APIRouter()

# ── Inbound email forwarding config ────────────────────────────────────
FORWARD_TO_EMAIL = os.environ.get("FORWARD_TO_EMAIL", "mradjordan@live.com")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.resend.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("RESEND_API_KEY", "")  # Resend uses API key as SMTP user
SMTP_PASSWORD = os.environ.get("RESEND_API_KEY", "")
FROM_NAME = "Day Shift Inbox"


# ── Resend Inbound Email Webhook ───────────────────────────────────────
@api.post("/webhooks/inbound")
async def resend_inbound_webhook(request: Request):
    """Receive inbound emails via Resend and forward to personal email.

    Resend sends a POST with the raw RFC-5322 email in base64-encoded
    `email` field. We parse it and relay it to FORWARD_TO_EMAIL.

    Setup:
      1. In Resend dashboard → Domains → dayshiftnow.me → enable "Inbound"
      2. Set webhook URL to: https://yourdomain.com/api/webhooks/inbound
      3. Point MX records to Resend (see docs)
    """
    # Verify the request is from Resend via svix webhook signing
    RESEND_WEBHOOK_SECRET = os.environ.get("RESEND_WEBHOOK_SECRET", "")
    raw_body = await request.body()
    if RESEND_WEBHOOK_SECRET:
        try:
            from svix.webhooks import Webhook
            wh = Webhook(RESEND_WEBHOOK_SECRET)
            wh.verify(raw_body, dict(request.headers))
        except ImportError:
            # Fallback: manual HMAC comparison via svix-signature header
            import hmac
            import hashlib
            sig_header = request.headers.get("svix-signature", "")
            computed = hmac.new(
                RESEND_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig_header, computed):
                raise HTTPException(403, "Invalid webhook signature")
        except Exception:
            raise HTTPException(403, "Invalid webhook signature")
    else:
        logger.warning("[Inbound] No RESEND_WEBHOOK_SECRET configured — accepting unverified requests")
    try:
        body = json.loads(raw_body)
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")

    # Extract the base64-encoded raw email from Resend's payload
    raw_email_b64 = body.get("email", "")
    if not raw_email_b64:
        logger.warning("[Inbound] No 'email' field in payload — ignoring")
        raise HTTPException(400, "Missing email payload")

    try:
        raw_email_bytes = base64.b64decode(raw_email_b64)
        msg = email_lib.message_from_bytes(raw_email_bytes)
    except Exception as e:
        logger.error(f"[Inbound] Failed to decode/parse email: {e}")
        raise HTTPException(400, "Malformed email payload")

    # Extract headers from original message
    original_from = msg.get("From", "unknown@unknown")
    original_to = msg.get("To", "unknown@dayshiftnow.me")
    original_subject = msg.get("Subject", "(no subject)")
    original_date = msg.get("Date", formatdate(localtime=True))

    # Extract plain text and/or HTML body
    text_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and not text_body:
                charset = part.get_content_charset() or "utf-8"
                try:
                    text_body = part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    pass
            elif content_type == "text/html" and not html_body:
                charset = part.get_content_charset() or "utf-8"
                try:
                    html_body = part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        ct = msg.get_content_type()
        try:
            raw_body = msg.get_payload(decode=True).decode(charset, errors="replace")
            if ct == "text/html":
                html_body = raw_body
            else:
                text_body = raw_body
        except Exception:
            pass

    # Build forwarded message
    fwd_subject = f"[Day Shift] {original_subject}"

    # Use HTML if available, otherwise plain text
    if html_body:
        # Wrap original HTML in a container with forwarding header
        fwd_html = f"""\
<html><body>
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;background:#18181b;border-radius:12px;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<tr><td style="padding:20px 24px 8px;border-bottom:1px solid #27272a;">
  <p style="margin:0;color:#f97316;font-size:14px;font-weight:700;">📬 Day Shift Inbox Forward</p>
</td></tr>
<tr><td style="padding:16px 24px;">
  <table style="font-size:13px;color:#a1a1aa;line-height:1.6;">
    <tr><td style="color:#52525b;padding:2px 0;"><strong>From:</strong></td><td>{original_from}</td></tr>
    <tr><td style="color:#52525b;padding:2px 0;"><strong>To:</strong></td><td>{original_to}</td></tr>
    <tr><td style="color:#52525b;padding:2px 0;"><strong>Date:</strong></td><td>{original_date}</td></tr>
  </table>
  <hr style="border:none;border-top:1px solid #27272a;margin:16px 0;">
</td></tr>
<tr><td style="padding:0 24px 24px;">
{html_body}
</td></tr>
<tr><td style="padding:12px 24px;text-align:center;border-top:1px solid #27272a;color:#52525b;font-size:11px;">
  Forwarded by Day Shift &middot; <a href="https://app.dayshiftnow.me" style="color:#f97316;">dayshiftnow.me</a>
</td></tr>
</table>
</body></html>"""
        fwd_msg = MIMEText(fwd_html, "html", "utf-8")
    else:
        fwd_text = f"""\
--- Day Shift Inbox Forward ---
From: {original_from}
To:   {original_to}
Date: {original_date}

{text_body}

---
Forwarded by Day Shift · https://app.dayshiftnow.me"""
        fwd_msg = MIMEText(fwd_text, "plain", "utf-8")

    fwd_msg["Subject"] = fwd_subject
    fwd_msg["From"] = f"{FROM_NAME} <contact@dayshiftnow.me>"
    fwd_msg["To"] = FORWARD_TO_EMAIL
    fwd_msg["Reply-To"] = original_from
    fwd_msg["Date"] = formatdate(localtime=True)
    fwd_msg["Message-ID"] = make_msgid(domain="dayshiftnow.me")

    # Send via Resend SMTP
    if SMTP_USER and SMTP_PASSWORD:
        try:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(
                    "contact@dayshiftnow.me",
                    [FORWARD_TO_EMAIL],
                    fwd_msg.as_string(),
                )
            logger.info(f"[Inbound] Forwarded email from {original_from} to {FORWARD_TO_EMAIL}")
        except Exception as e:
            logger.error(f"[Inbound] Failed to forward email: {e}")
            # Don't fail the webhook — we don't want Resend retrying forever
            return {"forwarded": False, "error": str(e)}
    else:
        logger.warning("[Inbound] No SMTP credentials configured — skipping send")

    return {"forwarded": True, "to": FORWARD_TO_EMAIL}
