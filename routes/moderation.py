"""Content moderation utilities for Day Shift Marketplace."""
import logging
from typing import Optional

from .deps import get_conn

logger = logging.getLogger(__name__)


def scan_text(text: str) -> list[dict]:
    """Scan text against moderation keywords. Returns list of matches."""
    if not text:
        return []

    text_lower = text.lower()
    matches = []

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT keyword, severity FROM moderation_keywords")
        keywords = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    for kw in keywords:
        if kw["keyword"] in text_lower:
            matches.append({"keyword": kw["keyword"], "severity": kw["severity"]})

    return matches


def flag_content(target_type: str, target_id: int, matched_term: str) -> None:
    """Create a content_flag record for admin review."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO content_flags (target_type, target_id, flag_type, matched_term)
               VALUES (%s, %s, 'keyword', %s)
               ON CONFLICT DO NOTHING""",
            (target_type, target_id, matched_term),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"[Moderation] Failed to flag content: {e}")
    finally:
        cur.close()
        conn.close()


def should_block_text(text: str) -> tuple[bool, Optional[str]]:
    """Check if text contains block-level keywords. Returns (blocked, matched_keyword)."""
    matches = scan_text(text)
    for m in matches:
        if m["severity"] == "block":
            return True, m["keyword"]
    return False, None


def moderate_and_flag(target_type: str, target_id: int, text: str) -> dict:
    """Full moderation scan: check for blocks, create flags, return result."""
    matches = scan_text(text)

    blocked = False
    blocked_term = None
    flagged = []

    for m in matches:
        if m["severity"] == "block":
            blocked = True
            blocked_term = m["keyword"]
        elif m["severity"] in ("flag", "warn"):
            flagged.append(m["keyword"])
            flag_content(target_type, target_id, m["keyword"])

    return {
        "blocked": blocked,
        "blocked_term": blocked_term,
        "flagged_terms": flagged,
        "all_matches": matches,
    }
