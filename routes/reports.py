"""Report / moderation routes for Day Shift Marketplace."""
from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, get_current_user, require_admin
from .models import ReportBody, ReviewReportBody

api = APIRouter()


@api.post("/reports")
def create_report(body: ReportBody, current_user=Depends(get_current_user)):
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

        # Auto-flag: if 3+ open reports on same target, auto-suspend user or flag for urgent review
        cur.execute(
            "SELECT COUNT(*) FROM reports WHERE target_type=%s AND target_id=%s AND status='open'",
            (body.target_type, body.target_id),
        )
        report_count = cur.fetchone()["count"]

        if report_count >= 3:
            if body.target_type == "user":
                cur.execute(
                    "UPDATE users SET is_suspended=TRUE, suspension_reason='Auto-suspended: multiple reports' WHERE id=%s",
                    (body.target_id,),
                )
            elif body.target_type == "video":
                # Find the video owner and suspend them
                cur.execute("SELECT user_id FROM videos WHERE id=%s", (body.target_id,))
                vid = cur.fetchone()
                if vid:
                    cur.execute(
                        "UPDATE users SET is_suspended=TRUE, suspension_reason='Auto-suspended: video received multiple reports' WHERE id=%s",
                        (vid["user_id"],),
                    )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
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

        if body.action == "suspend":
            # Suspend the target user
            if report["target_type"] == "user":
                cur.execute(
                    "UPDATE users SET is_suspended=TRUE, suspension_reason=%s WHERE id=%s",
                    (body.reason or "Suspended by admin", report["target_id"]),
                )
            elif report["target_type"] == "video":
                cur.execute("SELECT user_id FROM videos WHERE id=%s", (report["target_id"],))
                vid = cur.fetchone()
                if vid:
                    cur.execute(
                        "UPDATE users SET is_suspended=TRUE, suspension_reason=%s WHERE id=%s",
                        (body.reason or "Suspended by admin: video violation", vid["user_id"]),
                    )

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
        raise HTTPException(500, str(e))
    finally:
        cur.close()
        conn.close()

    return {"ok": True, "action": body.action}
