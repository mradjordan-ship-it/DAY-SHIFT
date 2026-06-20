"""Report / moderation routes for Day Shift Marketplace."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .deps import get_conn, get_current_user, require_admin
from .models import ReportBody, ReviewReportBody

api = APIRouter()

limiter = Limiter(key_func=get_remote_address)

# ── Strike thresholds ────────────────────────────────────────────────────────
# 3 strikes  → 7-day suspension
# 5 strikes  → 30-day suspension
# 8 strikes  → permanent suspension
STRIKE_TIERS = [
    (3, 7),    # (strike_count, suspension_days)
    (5, 30),
    (8, None),  # None = permanent
]


def _apply_strike(conn, cur, user_id: int, reason: str, report_id: int = None, issued_by: int = None) -> dict:
    """Issue a strike and escalate suspension if threshold met. Returns strike info."""
    # Get current strike count
    cur.execute("SELECT COALESCE(strike_count, 0) FROM users WHERE id = %s", (user_id,))
    current_count = cur.fetchone()["coalesce"]

    new_level = current_count + 1

    # Insert strike record
    cur.execute(
        """INSERT INTO strikes (user_id, reason, report_id, issued_by, strike_level)
           VALUES (%s, %s, %s, %s, %s) RETURNING *""",
        (user_id, reason, report_id, issued_by, new_level),
    )
    strike = dict(cur.fetchone())

    # Update user strike count
    cur.execute("UPDATE users SET strike_count = %s WHERE id = %s", (new_level, user_id))

    # Check thresholds
    suspension_days = None
    for threshold, days in STRIKE_TIERS:
        if new_level >= threshold:
            suspension_days = days

    suspended = False
    expires_at = None
    if suspension_days is not None:
        suspended = True
        if suspension_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=suspension_days)
            cur.execute(
                "UPDATE users SET is_suspended=TRUE, suspension_reason=%s, suspension_expires_at=%s WHERE id=%s",
                (f"Auto-suspended: {new_level} strikes ({suspension_days}-day suspension)", expires_at, user_id),
            )
        else:
            # Permanent
            cur.execute(
                "UPDATE users SET is_suspended=TRUE, suspension_reason=%s, suspension_expires_at=NULL WHERE id=%s",
                (f"Permanently suspended: {new_level} strikes", user_id),
            )

    if expires_at:
        strike["suspension_expires_at"] = expires_at.isoformat()
    strike["suspended"] = suspended
    strike["strike_count"] = new_level
    return strike


@api.post("/reports")
@limiter.limit("10/minute")
def create_report(request: Request, body: ReportBody, current_user=Depends(get_current_user)):
    if body.target_type not in ("video", "user"):
        raise HTTPException(400, "target_type must be 'video' or 'user'")
    if body.reason not in ("harassment", "spam", "inappropriate", "fake", "other"):
        raise HTTPException(400, "Invalid reason")

    # Can't report yourself
    if body.target_type == "user" and body.target_id == current_user["id"]:
        raise HTTPException(400, "Cannot report yourself")

    # Prevent duplicate reports from same user on same target
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM reports WHERE reporter_id=%s AND target_type=%s AND target_id=%s AND status='open'",
        (current_user["id"], body.target_type, body.target_id),
    )
    if cur.fetchone():
        raise HTTPException(400, "You already reported this")

    try:
        cur.execute(
            """INSERT INTO reports (reporter_id, target_type, target_id, reason, comment)
               VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (current_user["id"], body.target_type, body.target_id, body.reason, body.comment),
        )
        report = dict(cur.fetchone())

        # ── Strike-based escalation ────────────────────────────────────────────
        # Get the target user_id (for video reports, resolve to owner)
        target_user_id = body.target_id
        if body.target_type == "video":
            cur.execute("SELECT user_id FROM videos WHERE id = %s", (body.target_id,))
            vid = cur.fetchone()
            if vid:
                target_user_id = vid["user_id"]

        # Only issue a strike after 3+ unique reporters on the same target
        cur.execute(
            "SELECT COUNT(DISTINCT reporter_id) FROM reports WHERE target_type=%s AND target_id=%s AND status='open'",
            (body.target_type, body.target_id),
        )
        unique_reporters = cur.fetchone()["count"]

        strike = None
        if unique_reporters >= 3:
            strike = _apply_strike(
                conn, cur, target_user_id,
                reason=f"Multiple reports ({unique_reporters}): {body.reason}",
                report_id=report["id"],
            )

        conn.commit()

        # Notify admins via push notification about the new report
        try:
            from .push import send_push_to_users
            admin_cur = conn.cursor()
            admin_cur.execute("SELECT id FROM users WHERE is_admin = TRUE")
            admin_ids = [r["id"] for r in admin_cur.fetchall()]
            admin_cur.close()
            if admin_ids:
                label = "user" if body.target_type == "user" else "post"
                send_push_to_users(admin_ids, "New Report 🚩", f"{body.reason} ({label})", "/admin")
        except Exception:
            pass

        # Send strike notification email if issued
        if strike and strike.get("suspended"):
            try:
                from .email_utils import send_strike_email
                cur.execute("SELECT name, email FROM users WHERE id = %s", (target_user_id,))
                target_user = cur.fetchone()
                if target_user:
                    send_strike_email(
                        target_user["email"],
                        target_user["name"],
                        strike["strike_count"],
                        strike["reason"],
                    )
            except Exception:
                pass
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    if report.get("created_at"):
        report["created_at"] = report["created_at"].isoformat()
    return report


@api.get("/admin/reports")
def admin_list_reports(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT r.*,
            reporter.name as reporter_name,
            CASE
                WHEN r.target_type = 'user' THEN target_u.name
                WHEN r.target_type = 'video' THEN target_v.title
            END as target_name,
            CASE
                WHEN r.target_type = 'user' THEN target_u.email
                WHEN r.target_type = 'video' THEN target_v.title
            END as target_detail
           FROM reports r
           JOIN users reporter ON r.reporter_id = reporter.id
           LEFT JOIN users target_u ON r.target_type = 'user' AND r.target_id = target_u.id
           LEFT JOIN videos target_v ON r.target_type = 'video' AND r.target_id = target_v.id
           ORDER BY
             CASE WHEN r.status = 'open' THEN 0 ELSE 1 END,
             r.created_at DESC"""
    )
    reports = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for r in reports:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
        if r.get("reviewed_at"):
            r["reviewed_at"] = r["reviewed_at"].isoformat()
    return reports


@api.patch("/admin/reports/{report_id}")
def admin_review_report(report_id: int, body: ReviewReportBody, admin=Depends(require_admin)):
    if body.action not in ("dismiss", "warn", "suspend", "remove_content"):
        raise HTTPException(400, "Invalid action. Use: dismiss, warn, suspend, remove_content")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reports WHERE id=%s", (report_id,))
    report = cur.fetchone()
    if not report:
        raise HTTPException(404, "Report not found")
    report = dict(report)

    try:
        # Update report status
        cur.execute(
            "UPDATE reports SET status='reviewed', admin_action=%s, reviewed_by=%s, reviewed_at=NOW() WHERE id=%s",
            (body.action, admin["id"], report_id),
        )

        # Resolve target user_id for strikes/notifications
        target_user_id = report["target_id"]
        if report["target_type"] == "video":
            cur.execute("SELECT user_id FROM videos WHERE id=%s", (report["target_id"],))
            vid = cur.fetchone()
            if vid:
                target_user_id = vid["user_id"]

        if body.action == "warn":
            # Issue a strike without suspending
            strike = _apply_strike(
                conn, cur, target_user_id,
                reason=body.reason or f"Admin warning: {report['reason']}",
                report_id=report_id,
                issued_by=admin["id"],
            )
            # Send strike email
            try:
                from .email_utils import send_strike_email
                cur.execute("SELECT name, email FROM users WHERE id = %s", (target_user_id,))
                target_user = cur.fetchone()
                if target_user:
                    send_strike_email(
                        target_user["email"], target_user["name"],
                        strike["strike_count"], strike["reason"],
                    )
            except Exception:
                pass

        elif body.action == "suspend":
            # Issue a strike AND suspend (suspension duration from threshold)
            strike = _apply_strike(
                conn, cur, target_user_id,
                reason=body.reason or f"Admin suspension: {report['reason']}",
                report_id=report_id,
                issued_by=admin["id"],
            )
            # If strike system didn't already suspend, force suspend
            if not strike.get("suspended"):
                cur.execute(
                    "UPDATE users SET is_suspended=TRUE, suspension_reason=%s, suspension_expires_at=NULL WHERE id=%s",
                    (body.reason or "Suspended by admin", target_user_id),
                )
            # Send suspension email
            try:
                from .email_utils import send_suspension_email
                cur.execute("SELECT name, email FROM users WHERE id = %s", (target_user_id,))
                target_user = cur.fetchone()
                if target_user:
                    send_suspension_email(
                        target_user["email"], target_user["name"],
                        body.reason or "Suspended by admin",
                    )
            except Exception:
                pass

        elif body.action == "remove_content":
            if report["target_type"] == "video":
                cur.execute("DELETE FROM likes WHERE video_id=%s", (report["target_id"],))
                cur.execute("DELETE FROM videos WHERE id=%s", (report["target_id"],))
            elif report["target_type"] == "user":
                # Remove all user's videos
                cur.execute("DELETE FROM likes WHERE video_id IN (SELECT id FROM videos WHERE user_id=%s)", (report["target_id"],))
                cur.execute("DELETE FROM videos WHERE user_id=%s", (report["target_id"],))

        # Also resolve all other open reports on the same target
        cur.execute(
            "UPDATE reports SET status='resolved', reviewed_by=%s, reviewed_at=NOW() WHERE target_type=%s AND target_id=%s AND status='open' AND id != %s",
            (admin["id"], report["target_type"], report["target_id"], report_id),
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    return {"ok": True, "action": body.action}


# ── Appeals ───────────────────────────────────────────────────────────────────

@api.post("/appeals")
def create_appeal(body: dict, current_user=Depends(get_current_user)):
    """Suspended user submits an appeal for their suspension."""
    if not current_user["is_suspended"]:
        raise HTTPException(400, "You can only appeal while suspended")

    reason = (body.get("reason") or "").strip()
    if len(reason) < 20:
        raise HTTPException(400, "Please provide more detail (at least 20 characters)")
    if len(reason) > 2000:
        raise HTTPException(400, "Appeal too long (max 2000 characters)")

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Only one pending appeal at a time
        cur.execute(
            "SELECT id FROM appeals WHERE user_id=%s AND status='pending'",
            (current_user["id"],),
        )
        if cur.fetchone():
            raise HTTPException(400, "You already have a pending appeal")

        cur.execute(
            """INSERT INTO appeals (user_id, reason) VALUES (%s, %s) RETURNING *""",
            (current_user["id"], reason),
        )
        appeal = dict(cur.fetchone())
        conn.commit()

        # Notify admins
        try:
            from .push import send_push_to_users
            admin_cur = conn.cursor()
            admin_cur.execute("SELECT id FROM users WHERE is_admin = TRUE")
            admin_ids = [r["id"] for r in admin_cur.fetchall()]
            admin_cur.close()
            if admin_ids:
                send_push_to_users(admin_ids, "New Appeal", f"Appeal from {current_user['name']}", "/admin")
        except Exception:
            pass
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error")
    finally:
        cur.close()
        conn.close()

    if appeal.get("created_at"):
        appeal["created_at"] = appeal["created_at"].isoformat()
    return appeal


@api.get("/appeals/mine")
def get_my_appeal(current_user=Depends(get_current_user)):
    """Get the user's latest appeal."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM appeals WHERE user_id=%s ORDER BY created_at DESC LIMIT 1",
        (current_user["id"],),
    )
    appeal = cur.fetchone()
    cur.close()
    conn.close()
    if not appeal:
        return None
    appeal = dict(appeal)
    for k in ("created_at", "reviewed_at"):
        if appeal.get(k):
            appeal[k] = appeal[k].isoformat()
    return appeal


@api.get("/admin/appeals")
def admin_list_appeals(admin=Depends(require_admin)):
    """Admin lists all pending appeals, then resolved ones."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT a.*, u.name as user_name, u.email as user_email, u.avatar_url as user_avatar,
                  u.strike_count, u.suspension_reason
           FROM appeals a
           JOIN users u ON a.user_id = u.id
           ORDER BY
             CASE WHEN a.status = 'pending' THEN 0 ELSE 1 END,
             a.created_at DESC"""
    )
    appeals = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for a in appeals:
        for k in ("created_at", "reviewed_at"):
            if a.get(k):
                a[k] = a[k].isoformat()
    return appeals


@api.patch("/admin/appeals/{appeal_id}")
def admin_review_appeal(appeal_id: int, body: dict, admin=Depends(require_admin)):
    action = body.get("action")  # 'approve' | 'deny'
    admin_response = body.get("response", "")

    if action not in ("approve", "deny"):
        raise HTTPException(400, "action must be 'approve' or 'deny'")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM appeals WHERE id=%s", (appeal_id,))
    appeal = cur.fetchone()
    if not appeal:
        raise HTTPException(404, "Appeal not found")
    appeal = dict(appeal)

    try:
        if action == "approve":
            cur.execute(
                "UPDATE appeals SET status='approved', admin_response=%s, reviewed_by=%s, reviewed_at=NOW() WHERE id=%s",
                (admin_response, admin["id"], appeal_id),
            )
            # Unuspend the user
            cur.execute(
                "UPDATE users SET is_suspended=FALSE, suspension_reason=NULL, suspension_expires_at=NULL WHERE id=%s",
                (appeal["user_id"],),
            )
            # Notify user
            try:
                from .push import send_push_to_user
                send_push_to_user(appeal["user_id"], "Appeal Approved ✅", "Your account has been reactivated.", "/feed")
            except Exception:
                pass
        else:
            cur.execute(
                "UPDATE appeals SET status='denied', admin_response=%s, reviewed_by=%s, reviewed_at=NOW() WHERE id=%s",
                (admin_response, admin["id"], appeal_id),
            )
            try:
                from .push import send_push_to_user
                send_push_to_user(appeal["user_id"], "Appeal Denied", "Your appeal was reviewed and denied.", "/profile")
            except Exception:
                pass

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error")
    finally:
        cur.close()
        conn.close()

    return {"ok": True, "action": action}


# ── Strike history ──────────────────────────────────────────────────────────

@api.get("/admin/users/{user_id}/strikes")
def admin_user_strikes(user_id: int, admin=Depends(require_admin)):
    """View a user's strike history."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT s.*, issuer.name as issued_by_name
           FROM strikes s
           LEFT JOIN users issuer ON s.issued_by = issuer.id
           WHERE s.user_id = %s
           ORDER BY s.created_at DESC""",
        (user_id,),
    )
    strikes = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for s in strikes:
        if s.get("created_at"):
            s["created_at"] = s["created_at"].isoformat()
    return strikes


@api.get("/admin/content-flags")
def admin_list_content_flags(admin=Depends(require_admin)):
    """List unresolved content flags from automated scanning."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT cf.*,
            CASE WHEN cf.target_type='user' THEN u.name ELSE v.title END as target_name,
            CASE WHEN cf.target_type='user' THEN u.email ELSE v.description END as target_detail
           FROM content_flags cf
           LEFT JOIN users u ON cf.target_type='user' AND cf.target_id = u.id
           LEFT JOIN videos v ON cf.target_type='video' AND cf.target_id = v.id
           WHERE cf.auto_resolved = FALSE
           ORDER BY cf.created_at DESC"""
    )
    flags = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for f in flags:
        if f.get("created_at"):
            f["created_at"] = f["created_at"].isoformat()
    return flags


@api.patch("/admin/content-flags/{flag_id}")
def admin_resolve_content_flag(flag_id: int, body: dict, admin=Depends(require_admin)):
    action = body.get("action")  # 'dismiss' | 'escalate'
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE content_flags SET auto_resolved=TRUE WHERE id=%s", (flag_id,))
    if action == "escalate":
        # Get the flag info and issue a strike
        cur.execute("SELECT * FROM content_flags WHERE id=%s", (flag_id,))
        flag = cur.fetchone()
        if flag:
            target_user_id = flag["target_id"]
            if flag["target_type"] == "video":
                cur.execute("SELECT user_id FROM videos WHERE id=%s", (flag["target_id"],))
                vid = cur.fetchone()
                if vid:
                    target_user_id = vid["user_id"]
            _apply_strike(conn, cur, target_user_id, reason=f"Content violation: {flag['matched_term']}", issued_by=admin["id"])
    conn.commit()
    cur.close()
    conn.close()
    return {"ok": True}
