"""Sanitization utilities for user-generated content.

Applies consistent HTML stripping and normalization to all user inputs
before storage and before interpolation into email templates.
"""
import html
import re


def strip_html(text: str | None) -> str:
    """Strip all HTML tags and decode HTML entities from text.

    Returns empty string for None/empty input.
    """
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]*>", "", str(text))
    # Decode HTML entities (&lt; → <, &amp; → &, etc.)
    cleaned = html.unescape(cleaned)
    # Collapse whitespace (remove excessive spaces, tabs, newlines)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def sanitize_text(text: str | None, max_length: int = 0) -> str:
    """Full sanitization: strip HTML, normalize whitespace, optionally truncate.

    Returns empty string for None/empty input.
    """
    cleaned = strip_html(text)
    if max_length > 0 and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def sanitize_email_body(text: str | None) -> str:
    """HTML-escape user text for safe interpolation into HTML email templates.

    This is critical: without escaping, user input containing HTML tags
    or script elements would be injected directly into the email body.
    """
    if not text:
        return ""
    return html.escape(str(text), quote=True)
