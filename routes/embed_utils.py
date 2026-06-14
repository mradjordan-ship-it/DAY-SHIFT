"""Convert video platform URLs to embeddable iframe URLs.

Supported platforms:
  - YouTube (youtube.com, youtu.be)
  - Vimeo (vimeo.com)
  - TikTok (tiktok.com)
  - Facebook / Instagram Reels (facebook.com, fb.watch, instagram.com)
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs, urlencode


def to_embed_url(url: str) -> str:
    """Convert a video platform URL to its embed equivalent.

    Returns an empty string if the URL is not a recognized video platform.
    """
    if not url or not url.strip():
        return ""

    url = url.strip()

    # YouTube
    embed = _youtube(url)
    if embed:
        return embed

    # Vimeo
    embed = _vimeo(url)
    if embed:
        return embed

    # TikTok
    embed = _tiktok(url)
    if embed:
        return embed

    # Facebook / Instagram
    embed = _facebook(url)
    if embed:
        return embed

    return ""


def _youtube(url: str) -> str:
    """Convert YouTube URLs to embed URLs.

    Handles:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID  (already embed)
      - https://www.youtube.com/shorts/VIDEO_ID
      - https://m.youtube.com/watch?v=VIDEO_ID
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    # Already an embed URL
    if "youtube.com/embed/" in url:
        return url.split("?")[0]  # strip extra params, keep clean

    # youtu.be short links
    if host == "youtu.be" or host == "www.youtu.be":
        video_id = parsed.path.strip("/")
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return ""

    # youtube.com watch URLs
    if "youtube.com" in host:
        # /shorts/VIDEO_ID
        shorts_match = re.match(r"^/shorts/([A-Za-z0-9_-]+)", parsed.path)
        if shorts_match:
            return f"https://www.youtube.com/embed/{shorts_match.group(1)}"

        # /watch?v=VIDEO_ID
        qs = parse_qs(parsed.query)
        video_id = qs.get("v", [None])[0]
        if video_id:
            # Preserve start time if present
            params = {}
            t = qs.get("t", [None])[0]
            if t:
                # Convert time string (e.g., "1m30s" or "90") to seconds
                try:
                    params["start"] = _parse_youtube_time(t)
                except (ValueError, TypeError):
                    pass
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            if params:
                embed_url += "?" + urlencode(params)
            return embed_url

    return ""


def _parse_youtube_time(t: str) -> int:
    """Parse YouTube time parameter to seconds.

    Handles: "90", "1m30s", "1h2m30s"
    """
    t = str(t).strip()
    # Pure number
    if t.isdigit():
        return int(t)

    # Parse h/m/s format
    total = 0
    for match in re.finditer(r"(\d+)([hms]?)", t):
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "h":
            total += value * 3600
        elif unit == "m":
            total += value * 60
        else:
            total += value
    return total


def _vimeo(url: str) -> str:
    """Convert Vimeo URLs to embed URLs.

    Handles:
      - https://vimeo.com/VIDEO_ID
      - https://player.vimeo.com/video/VIDEO_ID  (already embed)
      - https://vimeo.com/channels/CHANNEL/VIDEO_ID
      - https://vimeo.com/groups/GROUP/videos/VIDEO_ID
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if "vimeo.com" not in host:
        return ""

    # Already embed
    if "player.vimeo.com" in host:
        return url.split("?")[0]

    # Extract video ID from path
    path = parsed.path.strip("/")

    # Channels: channels/NAME/ID
    channel_match = re.match(r"channels/[\w-]+/(\d+)", path)
    if channel_match:
        return f"https://player.vimeo.com/video/{channel_match.group(1)}"

    # Groups: groups/NAME/videos/ID
    group_match = re.match(r"groups/[\w-]+/videos/(\d+)", path)
    if group_match:
        return f"https://player.vimeo.com/video/{group_match.group(1)}"

    # Direct: VIDEO_ID
    direct_match = re.match(r"^(\d+)", path)
    if direct_match:
        return f"https://player.vimeo.com/video/{direct_match.group(1)}"

    return ""


def _tiktok(url: str) -> str:
    """Convert TikTok URLs to embed URLs.

    Handles:
      - https://www.tiktok.com/@USER/video/VIDEO_ID
      - https://vm.tiktok.com/SHORT_ID
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if "tiktok.com" not in host:
        return ""

    path = parsed.path.strip("/")

    # Standard video URL: @username/video/ID
    video_match = re.match(r"@[\w.-]+/video/(\d+)", path)
    if video_match:
        return f"https://www.tiktok.com/embed/v2/{video_match.group(1)}"

    # Short URL (vm.tiktok.com/XXXXX) — can't resolve without fetching,
    # but we can use the embed v2 endpoint with the short ID
    if "vm.tiktok.com" in host:
        short_id = path.strip("/")
        if short_id:
            # TikTok embed v2 needs the full video ID, not the short URL ID.
            # For short URLs we return the original URL as-is — the frontend
            # can open it in a new tab instead.
            return ""

    return ""


def _facebook(url: str) -> str:
    """Convert Facebook/Instagram video URLs to embed URLs.

    Handles:
      - https://www.facebook.com/USER/videos/VIDEO_ID
      - https://www.facebook.com/watch/?v=VIDEO_ID
      - https://www.facebook.com/reel/VIDEO_ID
      - https://fb.watch/SHORT_ID
      - https://www.instagram.com/reel/REEL_ID/
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    is_facebook = "facebook.com" in host or "fb.watch" in host
    is_instagram = "instagram.com" in host

    if not is_facebook and not is_instagram:
        return ""

    if is_instagram:
        # Instagram reels: /reel/REEL_ID/
        reel_match = re.match(r"reel/([A-Za-z0-9_-]+)", parsed.path.strip("/"))
        if reel_match:
            return f"https://www.instagram.com/reel/{reel_match.group(1)}/embed/"
        return ""

    # Facebook
    path = parsed.path.strip("/")

    # /USER/videos/VIDEO_ID
    video_match = re.match(r"[\w.-]+/videos/(\d+)", path)
    if video_match:
        video_id = video_match.group(1)
        return f"https://www.facebook.com/plugins/video.php?href={url}"

    # /watch/?v=VIDEO_ID
    qs = parse_qs(parsed.query)
    video_id = qs.get("v", [None])[0]
    if video_id:
        return f"https://www.facebook.com/plugins/video.php?href={url}"

    # /reel/VIDEO_ID
    reel_match = re.match(r"reel/(\d+)", path)
    if reel_match:
        return f"https://www.facebook.com/plugins/video.php?href={url}"

    # fb.watch short links
    if "fb.watch" in host:
        return f"https://www.facebook.com/plugins/video.php?href={url}"

    return ""


def get_platform_name(url: str) -> str:
    """Return the platform name for a video URL (for display purposes)."""
    if not url:
        return ""
    host = (urlparse(url).hostname or "").lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "YouTube"
    if "vimeo.com" in host:
        return "Vimeo"
    if "tiktok.com" in host:
        return "TikTok"
    if "facebook.com" in host or "fb.watch" in host:
        return "Facebook"
    if "instagram.com" in host:
        return "Instagram"
    return ""
