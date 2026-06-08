"""Email sending utilities for Day Shift Marketplace using Resend."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("MAIL_FROM", "Day Shift <noreply@dayshift.app>")

# Whether email sending is enabled (graceful degrade if no API key)
EMAIL_ENABLED = bool(RESEND_API_KEY)


def _get_base_url() -> str:
    """Get the public base URL for constructing verification links."""
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    if custom_domain:
        return f"https://{custom_domain}"
    # Fallback: use request origin (set per-request in calling code)
    return os.environ.get("APP_BASE_URL", "https://dayshift.app")


def send_verification_email(email: str, name: str, token: str, base_url: Optional[str] = None) -> bool:
    """Send an email verification link to the user.
    
    Returns True if email was sent or gracefully skipped (no API key).
    Returns False only if Resend returned an error.
    """
    if not EMAIL_ENABLED:
        logger.info(f"[Email] No RESEND_API_KEY set — skipping verification email to {email}. Token: {token}")
        return True

    url = base_url or _get_base_url()
    verify_link = f"{url}?screen=verify-email&token={token}"

    try:
        import resend
        resend.api_key = RESEND_API_KEY

        params: resend.Emails.SendParams = {
            "from": FROM_EMAIL,
            "to": [email],
            "subject": "Verify your email — Day Shift",
            "html": _verification_html(name, verify_link),
            "text": f"Hey {name},\n\nPlease verify your email for Day Shift by clicking this link:\n\n{verify_link}\n\nThis link expires in 24 hours.\n\nIf you didn't create an account, you can ignore this email.\n\n— The Day Shift Team",
        }
        resend.Emails.send(params)
        logger.info(f"[Email] Verification email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"[Email] Failed to send verification email to {email}: {e}")
        return False


def send_password_reset_email(email: str, token: str, base_url: Optional[str] = None) -> bool:
    """Send a password reset link to the user."""
    if not EMAIL_ENABLED:
        logger.info(f"[Email] No RESEND_API_KEY set — skipping reset email to {email}. Token: {token}")
        return True

    url = base_url or _get_base_url()
    reset_link = f"{url}?screen=reset&token={token}"

    try:
        import resend
        resend.api_key = RESEND_API_KEY

        params: resend.Emails.SendParams = {
            "from": FROM_EMAIL,
            "to": [email],
            "subject": "Reset your password — Day Shift",
            "html": _reset_html(reset_link),
            "text": f"Reset your Day Shift password by clicking this link:\n\n{reset_link}\n\nThis link expires in 1 hour.\n\nIf you didn't request a reset, you can ignore this email.\n\n— The Day Shift Team",
        }
        resend.Emails.send(params)
        logger.info(f"[Email] Password reset email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"[Email] Failed to send reset email to {email}: {e}")
        return False


def _verification_html(name: str, verify_link: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;margin:40px auto;background:#18181b;border-radius:16px;overflow:hidden;">
    <tr><td style="padding:32px 24px 8px;text-align:center;">
      <h1 style="margin:0;color:#f97316;font-size:28px;font-weight:800;letter-spacing:-0.5px;">Day Shift</h1>
    </td></tr>
    <tr><td style="padding:8px 24px 24px;text-align:center;">
      <p style="margin:0 0 8px;color:#fafafa;font-size:18px;font-weight:600;">Hey {name},</p>
      <p style="margin:0 0 24px;color:#a1a1aa;font-size:15px;line-height:1.5;">
        Confirm your email to start finding your next culinary shift.
      </p>
      <a href="{verify_link}" style="display:inline-block;background:#f97316;color:#fff;text-decoration:none;padding:14px 32px;border-radius:10px;font-size:16px;font-weight:700;letter-spacing:0.3px;">
        Verify Email
      </a>
      <p style="margin:24px 0 0;color:#71717a;font-size:13px;line-height:1.5;">
        This link expires in 24 hours. If you didn't create an account on Day Shift, you can safely ignore this email.
      </p>
    </td></tr>
    <tr><td style="padding:16px 24px;text-align:center;border-top:1px solid #27272a;">
      <p style="margin:0;color:#52525b;font-size:12px;">© 2026 Day Shift · Built for Culinarians That Move Fast</p>
    </td></tr>
  </table>
</body>
</html>"""


def _reset_html(reset_link: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;margin:40px auto;background:#18181b;border-radius:16px;overflow:hidden;">
    <tr><td style="padding:32px 24px 8px;text-align:center;">
      <h1 style="margin:0;color:#f97316;font-size:28px;font-weight:800;letter-spacing:-0.5px;">Day Shift</h1>
    </td></tr>
    <tr><td style="padding:8px 24px 24px;text-align:center;">
      <p style="margin:0 0 24px;color:#a1a1aa;font-size:15px;line-height:1.5;">
        We received a request to reset your password. Click below to choose a new one.
      </p>
      <a href="{reset_link}" style="display:inline-block;background:#f97316;color:#fff;text-decoration:none;padding:14px 32px;border-radius:10px;font-size:16px;font-weight:700;letter-spacing:0.3px;">
        Reset Password
      </a>
      <p style="margin:24px 0 0;color:#71717a;font-size:13px;line-height:1.5;">
        This link expires in 1 hour. If you didn't request a reset, you can safely ignore this email.
      </p>
    </td></tr>
    <tr><td style="padding:16px 24px;text-align:center;border-top:1px solid #27272a;">
      <p style="margin:0;color:#52525b;font-size:12px;">© 2026 Day Shift · Built for Culinarians That Move Fast</p>
    </td></tr>
  </table>
</body>
</html>"""
