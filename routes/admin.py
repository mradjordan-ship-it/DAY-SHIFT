"""Admin routes for Day Shift Marketplace."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Form

from .deps import get_conn, require_admin
from .models import TIERS, AdminBoostBody, AdminCreateBoostBody, AdminAdvertiseBody

api = APIRouter()


@api.get("/admin/stats")
def admin_stats(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    stats = {}
    cur.execute("SELECT COUNT(*) FROM users")
    stats["total_users"] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='worker'")
    stats["workers"] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='employer'")
    stats["employers"] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM videos")
    stats["total_videos"] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM matches")
    stats["total_matches"] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM matches WHERE status='pending'")
    stats["pending_matches"] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM matches WHERE status='active'")
    stats["active_matches"] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) FROM matches WHERE status='completed'")
    stats["completed_matches"] = cur.fetchone()["count"]
    # Signups in last 7 days
    cur.execute("SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '7 days'")
    stats["signups_last_7d"] = cur.fetchone()["count"]
    # Signups today
    cur.execute("SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '1 day'")
    stats["signups_today"] = cur.fetchone()["count"]
    cur.close()
    conn.close()
    return stats


@api.get("/admin/users")
def admin_list_users(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, name, email, role, is_admin, is_advertiser, advertiser_agreement_accepted, avg_rating, total_shifts,
                  avatar_url, created_at, bio
           FROM users ORDER BY created_at DESC"""
    )
    users = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for u in users:
        if u.get("created_at"):
            u["created_at"] = u["created_at"].isoformat()
    return users


@api.patch("/admin/users/{user_id}")
def admin_update_user(user_id: int, body: dict, admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    if not cur.fetchone():
        raise HTTPException(404, "User not found")
    allowed = {"is_admin", "is_advertiser"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, "No valid fields to update")
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    cur.execute(f"UPDATE users SET {set_clause} WHERE id=%s RETURNING *",
                list(updates.values()) + [user_id])
    user = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    for f in ("password_hash", "reset_token", "reset_token_expires"):
        user.pop(f, None)
    return user


@api.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin=Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(400, "Cannot delete your own account")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM messages WHERE sender_id = %s", (user_id,))
        cur.execute("DELETE FROM likes WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM matches WHERE worker_id = %s OR employer_id = %s", (user_id, user_id))
        cur.execute("DELETE FROM reviews WHERE reviewer_id = %s OR reviewee_id = %s", (user_id, user_id))
        cur.execute("DELETE FROM videos WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()
    return {"ok": True}


@api.get("/admin/boosts")
def admin_list_boosts(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT pb.*, u.name as user_name, u.email as user_email, v.title as video_title
           FROM post_boosts pb
           JOIN users u ON pb.user_id = u.id
           LEFT JOIN videos v ON pb.video_id = v.id
           ORDER BY pb.created_at DESC"""
    )
    boosts = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for b in boosts:
        for k in ("created_at", "start_date", "end_date"):
            if b.get(k): b[k] = b[k].isoformat()
    return boosts


@api.patch("/admin/boosts/{boost_id}")
def admin_update_boost(boost_id: int, body: AdminBoostBody, admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM post_boosts WHERE id = %s", (boost_id,))
    boost = cur.fetchone()
    if not boost:
        raise HTTPException(404, "Boost not found")
    boost = dict(boost)

    if body.action == "approve":
        if boost["payment_status"] != "paid":
            raise HTTPException(400, "Payment not confirmed yet")
        tier_info = TIERS.get(boost["tier"], {})
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=tier_info.get("duration_days", 1))
        cur.execute(
            "UPDATE post_boosts SET status='active', admin_approved=TRUE, start_date=%s, end_date=%s WHERE id=%s",
            (now, end, boost_id),
        )
        # Update subscription
        cur.execute("SELECT * FROM advertiser_subscriptions WHERE user_id = %s", (boost["user_id"],))
        sub = cur.fetchone()
        if sub:
            sub = dict(sub)
            if boost["tier"] == "boost" and not sub.get("free_boost_used"):
                cur.execute("UPDATE advertiser_subscriptions SET free_boost_used=TRUE, boosts_used=boosts_used+1 WHERE user_id=%s", (boost["user_id"],))
            else:
                cur.execute("UPDATE advertiser_subscriptions SET boosts_used=boosts_used+1, boosts_remaining=GREATEST(boosts_remaining-1, 0) WHERE user_id=%s", (boost["user_id"],))
    elif body.action == "reject":
        cur.execute("UPDATE post_boosts SET status='rejected' WHERE id=%s", (boost_id,))
    else:
        raise HTTPException(400, "Action must be 'approve' or 'reject'")

    conn.commit()
    cur.execute("SELECT * FROM post_boosts WHERE id = %s", (boost_id,))
    updated = dict(cur.fetchone())
    cur.close()
    conn.close()
    for k in ("created_at", "start_date", "end_date"):
        if updated.get(k): updated[k] = updated[k].isoformat()
    return updated


@api.post("/admin/boosts")
def admin_create_boost(body: AdminCreateBoostBody, admin=Depends(require_admin)):
    """Admin can create free boosts for any post (including their own)."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Verify video exists
    cur.execute("SELECT * FROM videos WHERE id = %s", (body.video_id,))
    video = cur.fetchone()
    if not video:
        raise HTTPException(404, "Video not found")
    video = dict(video)
    
    # Check for existing active boost
    cur.execute("SELECT id FROM post_boosts WHERE video_id = %s AND status = 'active' AND end_date > NOW()", (body.video_id,))
    if cur.fetchone():
        raise HTTPException(400, "This post already has an active boost")
    
    tier_info = TIERS.get(body.tier, TIERS["boost"])
    duration = body.duration_days or tier_info["duration_days"]
    
    # Create and activate boost immediately
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=duration)
    
    cur.execute(
        """INSERT INTO post_boosts (video_id, user_id, tier, status, payment_status, admin_approved, start_date, end_date)
           VALUES (%s, %s, %s, 'active', 'paid', TRUE, %s, %s) RETURNING *""",
        (body.video_id, admin["id"], body.tier, now, end),
    )
    boost = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    
    for k in ("created_at", "start_date", "end_date"):
        if boost.get(k): boost[k] = boost[k].isoformat()
    return boost


@api.post("/admin/advertise")
def admin_advertise(body: AdminAdvertiseBody, admin=Depends(require_admin)):
    """Admin can activate advertiser subscription for free, no Stripe."""
    conn = get_conn()
    cur = conn.cursor()

    # Set user as advertiser
    cur.execute("UPDATE users SET is_advertiser = TRUE WHERE id = %s", (admin["id"],))

    # Upsert advertiser subscription as active
    cur.execute(
        """INSERT INTO advertiser_subscriptions (user_id, tier, status, stripe_session_id)
           VALUES (%s, %s, 'active', 'admin_free')
           ON CONFLICT (user_id) DO UPDATE SET tier = %s, status = 'active'
           RETURNING *""",
        (admin["id"], body.tier, body.tier),
    )
    sub = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()

    for k in ("created_at",):
        if sub.get(k): sub[k] = sub[k].isoformat()
    return {"status": "active", "tier": body.tier, "message": "Advertiser subscription activated for free"}


@api.get("/admin/videos")
def admin_list_videos(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT v.*, u.name as user_name, u.role as user_role
           FROM videos v JOIN users u ON v.user_id = u.id
           ORDER BY v.created_at DESC"""
    )
    videos = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for v in videos:
        if v.get("created_at"):
            v["created_at"] = v["created_at"].isoformat()
    return videos


@api.delete("/admin/videos/{video_id}")
def admin_delete_video(video_id: int, admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM videos WHERE id=%s", (video_id,))
    video = cur.fetchone()
    if not video:
        raise HTTPException(404, "Video not found")
    try:
        cur.execute("DELETE FROM likes WHERE video_id = %s", (video_id,))
        cur.execute("DELETE FROM videos WHERE id = %s", (video_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()
    return {"ok": True}


@api.patch("/admin/videos/{video_id}")
def admin_update_video(
    video_id: int,
    title: str = Form(None),
    description: str = Form(None),
    category: str = Form(None),
    price: str = Form(None),
    event_date: str = Form(None),
    event_time: str = Form(None),
    aspect_ratio: str = Form(None),
    cuisine_type: str = Form(None),
    pay_rate: str = Form(None),
    hours: str = Form(None),
    experience_level: str = Form(None),
    location: str = Form(None),
    admin=Depends(require_admin),
):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM videos WHERE id = %s", (video_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Video not found")

        updates = []
        params = []

        for field, value in [
            ("title", title),
            ("description", description),
            ("category", category),
            ("price", price),
            ("event_date", event_date),
            ("event_time", event_time),
            ("aspect_ratio", aspect_ratio),
            ("cuisine_type", cuisine_type),
            ("pay_rate", pay_rate),
            ("hours", hours),
            ("experience_level", experience_level),
            ("location", location),
        ]:
            if value is not None:
                updates.append(f"{field} = %s")
                params.append(value)

        if not updates:
            return {"ok": True}

        params.append(video_id)
        cur.execute(f"UPDATE videos SET {', '.join(updates)} WHERE id = %s RETURNING *", tuple(params))
        video = dict(cur.fetchone())
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Internal error — please try again")
    finally:
        cur.close()
        conn.close()

    if video.get("created_at"):
        video["created_at"] = video["created_at"].isoformat()
    return video


@api.get("/admin/scheduled")
def admin_list_scheduled(admin=Depends(require_admin)):
    """List all posts with a scheduled_at that haven't gone live yet."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT v.id, v.title, v.description, v.type, v.category, v.scheduled_at, v.created_at,
                  v.image_url, v.video_url,
                  u.id as user_id, u.name as user_name, u.role as user_role, u.is_advertiser
           FROM videos v JOIN users u ON v.user_id = u.id
           WHERE v.scheduled_at IS NOT NULL AND v.scheduled_at > NOW()
           ORDER BY v.scheduled_at ASC"""
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for r in rows:
        if r.get("scheduled_at"):
            r["scheduled_at"] = r["scheduled_at"].isoformat()
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


@api.get("/admin/matches")
def admin_list_matches(admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT m.*, w.name as worker_name, e.name as employer_name
           FROM matches m
           JOIN users w ON m.worker_id = w.id
           JOIN users e ON m.employer_id = e.id
           ORDER BY m.created_at DESC"""
    )
    matches = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for m in matches:
        if m.get("created_at"):
            m["created_at"] = m["created_at"].isoformat()
    return matches


@api.post("/admin/users/{user_id}/suspend")
def admin_suspend_user(user_id: int, body: dict, admin=Depends(require_admin)):
    reason = body.get("reason", "Suspended by admin")
    conn = get_conn()
    cur = conn.cursor()
    try:
        strike = _apply_strike(
            conn, cur, user_id,
            reason=reason,
            issued_by=admin["id"],
        )
        # If strike system didn't auto-suspend, force permanent suspend
        if not strike.get("suspended"):
            cur.execute(
                "UPDATE users SET is_suspended=TRUE, suspension_reason=%s, suspension_expires_at=NULL WHERE id=%s",
                (reason, user_id),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Failed to suspend: {e}")
    finally:
        cur.close()
        conn.close()
    # Send suspension email
    try:
        from .email_utils import send_suspension_email
        cur2 = get_conn().cursor()
        cur2.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
        target_user = cur2.fetchone()
        if target_user:
            send_suspension_email(target_user["email"], target_user["name"], reason)
        cur2.close()
        get_conn().close()
    except Exception:
        pass
    # Notify user via push
    try:
        from .push import send_push_to_user
        send_push_to_user(user_id, "Account Suspended", reason, "/profile")
    except Exception:
        pass
    return {"ok": True}


@api.post("/admin/users/{user_id}/unsuspend")
def admin_unsuspend_user(user_id: int, admin=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_suspended=FALSE, suspension_reason=NULL, suspension_expires_at=NULL WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    # Notify user via push
    try:
        from .push import send_push_to_user
        send_push_to_user(user_id, "Account Restored", "Your account has been reactivated.", "/feed")
    except Exception:
        pass
    return {"ok": True}
