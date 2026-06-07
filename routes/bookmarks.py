"""Bookmark routes for Day Shift Marketplace."""
from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, get_current_user

api = APIRouter()


@api.get("/bookmarks")
def list_bookmarks(current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT b.video_id, v.title, v.image_url, v.thumbnail_url, v.type, v.category, v.created_at, u.name as author_name, u.avatar_url as author_avatar
           FROM bookmarks b
           JOIN videos v ON b.video_id = v.id
           JOIN users u ON v.user_id = u.id
           WHERE b.user_id = %s
           ORDER BY b.created_at DESC""",
        (current_user["id"],),
    )
    result = []
    for r in cur.fetchall():
        item = dict(r)
        if item.get("created_at"):
            item["created_at"] = item["created_at"].isoformat()
        result.append(item)
    cur.close()
    conn.close()
    return result


@api.post("/bookmarks")
def toggle_bookmark(body: dict, current_user=Depends(get_current_user)):
    video_id = body.get("video_id")
    if not video_id:
        raise HTTPException(400, "video_id required")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM bookmarks WHERE user_id=%s AND video_id=%s",
            (current_user["id"], video_id),
        )
        existing = cur.fetchone()
        if existing:
            cur.execute("DELETE FROM bookmarks WHERE id=%s", (existing["id"],))
            bookmarked = False
        else:
            cur.execute(
                "INSERT INTO bookmarks (user_id, video_id) VALUES (%s, %s)",
                (current_user["id"], video_id),
            )
            bookmarked = True
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"bookmarked": bookmarked}
