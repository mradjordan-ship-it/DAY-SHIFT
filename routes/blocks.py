"""User block routes for Day Shift Marketplace."""
from fastapi import APIRouter, HTTPException, Depends

from .deps import get_conn, get_current_user

api = APIRouter()


@api.get("/blocks")
def list_blocks(current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT ub.id, ub.blocked_id, u.name as blocked_name, u.avatar_url as blocked_avatar, ub.created_at
           FROM user_blocks ub
           JOIN users u ON ub.blocked_id = u.id
           WHERE ub.blocker_id = %s
           ORDER BY ub.created_at DESC""",
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


@api.post("/blocks")
def toggle_block(body: dict, current_user=Depends(get_current_user)):
    blocked_id = body.get("user_id")
    if not blocked_id:
        raise HTTPException(400, "user_id required")
    if blocked_id == current_user["id"]:
        raise HTTPException(400, "Cannot block yourself")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM user_blocks WHERE blocker_id=%s AND blocked_id=%s",
            (current_user["id"], blocked_id),
        )
        existing = cur.fetchone()
        if existing:
            cur.execute("DELETE FROM user_blocks WHERE id=%s", (existing["id"],))
            blocked = False
        else:
            cur.execute(
                "INSERT INTO user_blocks (blocker_id, blocked_id) VALUES (%s, %s)",
                (current_user["id"], blocked_id),
            )
            blocked = True
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"blocked": blocked}


@api.delete("/blocks/{block_id}")
def remove_block(block_id: int, current_user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_blocks WHERE id=%s AND blocker_id=%s", (block_id, current_user["id"]))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "removed"}
