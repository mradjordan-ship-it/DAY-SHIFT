"""Import job data from an external URL via Open Graph meta tags and page scraping."""
from __future__ import annotations

import os
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .embed_utils import to_embed_url, get_platform_name

api = APIRouter()

# Keywords that suggest a field mapping
_PAY_KEYWORDS = re.compile(
    r"\$(\d[\d,.]*)\s*(?:/|per\s*)?(?:hr|hour|hrly|hourly)?", re.I
)
_LOCATION_KEYWORDS = re.compile(
    r"\b(?:location|city|area|address|where)\b", re.I
)
_HOURS_KEYWORDS = re.compile(
    r"\b(\d[\d.]*)\s*(?:hrs?|hours?|shift\s*hours?)\b", re.I
)
_EXP_KEYWORDS = re.compile(
    r"\b(?:entry.level|junior|mid.level|senior|lead|executive|experienced)\b", re.I
)


class ImportURLRequest(BaseModel):
    url: str


class ImportURLResponse(BaseModel):
    title: str = ""
    description: str = ""
    location: str = ""
    pay_rate: str = ""
    hours: str = ""
    experience_level: str = ""
    cuisine_type: str = ""
    image_url: str = ""
    video_url: str = ""
    embed_url: str = ""
    platform: str = ""
    source_domain: str = ""
    category: str = "general"


def _extract_from_og(soup: BeautifulSoup) -> dict:
    """Pull data from Open Graph meta tags."""
    data: dict = {}

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        data["title"] = og_title["content"].strip()

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        data["description"] = og_desc["content"].strip()

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        data["image_url"] = og_image["content"].strip()

    # Extract video URL from OG video tags
    for prop in ("og:video", "og:video:url", "og:video:secure_url"):
        og_video = soup.find("meta", property=prop)
        if og_video and og_video.get("content"):
            video_url = og_video["content"].strip()
            # Only accept direct video URLs (mp4, webm, etc.) — skip SWF/players
            if any(video_url.lower().endswith(ext) for ext in (".mp4", ".webm", ".mov", ".m3u8")) or "video" in (og_video.get("type") or "").lower():
                data["video_url"] = video_url
                break

    return data


def _extract_from_twitter(soup: BeautifulSoup) -> dict:
    """Pull data from Twitter Card meta tags as fallback."""
    data: dict = {}

    tw_title = soup.find("meta", attrs={"name": "twitter:title"})
    if tw_title and tw_title.get("content"):
        data.setdefault("title", tw_title["content"].strip())

    tw_desc = soup.find("meta", attrs={"name": "twitter:description"})
    if tw_desc and tw_desc.get("content"):
        data.setdefault("description", tw_desc["content"].strip())

    tw_image = soup.find("meta", attrs={"name": "twitter:image"})
    if tw_image and tw_image.get("content"):
        data.setdefault("image_url", tw_image["content"].strip())

    return data


def _extract_from_html(soup: BeautifulSoup) -> dict:
    """Fallback: pull from <title>, meta description, and visible text."""
    data: dict = {}

    if not data.get("title"):
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            # Clean up common suffixes like " | LinkedIn", " - Facebook"
            cleaned = re.sub(
                r"\s*[|\-–—]\s*(LinkedIn|Facebook|Indeed|Glassdoor|ZipRecruiter|Instagram|X|Twitter).*$",
                "",
                title_tag.string.strip(),
                flags=re.I,
            )
            data["title"] = cleaned

    if not data.get("description"):
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            data["description"] = meta_desc["content"].strip()

    return data


def _extract_job_fields(text: str) -> dict:
    """Parse pay rate, hours, experience level, location from visible text."""
    data: dict = {}

    # Pay rate
    pay_match = _PAY_KEYWORDS.search(text)
    if pay_match:
        data["pay_rate"] = pay_match.group(0).strip()

    # Hours
    hours_match = _HOURS_KEYWORDS.search(text)
    if hours_match:
        data["hours"] = hours_match.group(0).strip()

    # Experience level
    exp_match = _EXP_KEYWORDS.search(text)
    if exp_match:
        data["experience_level"] = exp_match.group(0).strip().title()

    # Location — look for common patterns like "Location: Columbus, OH"
    loc_match = re.search(
        r"(?:location|city|area|address)\s*[:\-–]\s*(.+?)(?:\n|<br|$)", text, re.I
    )
    if loc_match:
        data["location"] = loc_match.group(1).strip()[:100]

    # Cuisine type — look for common food industry keywords
    cuisine_match = re.search(
        r"(?:cuisine|cuisine type|food type|restaurant type)\s*[:\-–]\s*(.+?)(?:\n|<br|$)",
        text,
        re.I,
    )
    if cuisine_match:
        data["cuisine_type"] = cuisine_match.group(1).strip()[:100]

    return data


def _detect_category(text: str, url: str) -> str:
    """Auto-detect post category from page content and URL."""
    text_lower = text.lower()
    url_lower = url.lower()

    # For-sale indicators
    sale_keywords = [
        "for sale", "selling", "used", "equipment", "fryer", "oven",
        "mixer", "freezer", "kitchen equipment", "negotiable", "obo",
        "buy", "price:", "condition:", "barely used", "like new",
    ]
    if any(kw in text_lower for kw in sale_keywords):
        return "sale"

    # Kitchen/employer indicators — looking to hire
    kitchen_keywords = [
        "hiring", "looking for", "seeking", "position", "job opening",
        "open position", "we need", "join our team", "now hiring",
        "help wanted", "full-time", "part-time", "shift available",
        "line cook", "sous chef", "prep cook", "dishwasher",
        "server", "bartender", "host", "pastry chef", "sous",
        "kitchen manager", "executive chef", "chef de cuisine",
    ]
    # Crew/worker indicators — looking for work
    crew_keywords = [
        "available for", "looking for work", "seeking employment",
        "i have experience", "years of experience", "my specialty",
        "i specialize", "work history", "certified", "i am", "i'm",
        "my experience", "i cook", "i can", "resume",
    ]
    has_kitchen = any(kw in text_lower for kw in kitchen_keywords)
    has_crew = any(kw in text_lower for kw in crew_keywords)

    if has_kitchen and not has_crew:
        return "kitchen"
    if has_crew and not has_kitchen:
        return "crew"

    # Job board URLs → likely kitchen/employer posting
    job_board_domains = ["indeed.com", "ziprecruiter.com", "glassdoor.com", "linkedin.com/jobs"]
    if any(domain in url_lower for domain in job_board_domains):
        return "kitchen"

    # Event indicators (checked after job keywords to avoid false positives)
    event_keywords = [
        "food festival", "pop-up dinner", "tasting event", "gala",
        "charity dinner", "cook-off", "culinary competition",
        "ticket required", "admission fee",
    ]
    if any(kw in text_lower for kw in event_keywords) or "/event" in url_lower:
        return "event"

    # Default
    return "general"


@api.post("/import-url", response_model=ImportURLResponse)
async def import_url(body: ImportURLRequest):
    """Fetch a URL and extract job-relevant data from its content."""
    # Validate URL
    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "URL must start with http:// or https://")

    source_domain = parsed.hostname or ""

    # Block private/internal IPs to prevent SSRF
    if source_domain in ("localhost", "127.0.0.1", "0.0.0.0"):
        raise HTTPException(400, "Cannot import from local addresses")

    # Check if the URL itself is a direct video file
    video_exts = (".mp4", ".webm", ".mov", ".m4v", ".3gp")
    if any(parsed.path.lower().endswith(ext) for ext in video_exts):
        return ImportURLResponse(
            title=parsed.path.split("/")[-1] or "Imported Video",
            description=f"Imported from {source_domain}",
            video_url=body.url,
            source_domain=source_domain,
            category="kitchen" if any(kw in source_domain for kw in ("indeed", "ziprecruiter", "linkedin")) else "general",
        )

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "DayShift/1.0 (job import bot; +https://day-shift.workshop.build)",
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
            },
        ) as client:
            resp = await client.get(body.url)
            resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(408, "Timed out fetching that URL")
    except httpx.HTTPStatusError as e:
        raise HTTPException(422, f"Could not fetch URL (HTTP {e.response.status_code})")
    except Exception:
        raise HTTPException(422, "Could not fetch that URL")

    content_type = resp.headers.get("content-type", "")
    # Check if response is a direct video (some URLs redirect to video files)
    if any(t in content_type for t in ("video/", "application/x-mpegURL", "application/vnd.apple.mpegurl")):
        return ImportURLResponse(
            title=body.url.split("/")[-1] or "Imported Video",
            description=f"Imported from {source_domain}",
            video_url=str(resp.url),
            source_domain=source_domain,
            category="general",
        )

    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise HTTPException(422, "URL does not point to a web page or video")

    # Parse HTML
    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        soup = BeautifulSoup(resp.text, "html.parser")

    # Extract in priority order: OG → Twitter → plain HTML
    result: dict = {}
    result.update(_extract_from_og(soup))
    result.update(_extract_from_twitter(soup))
    result.update(_extract_from_html(soup))

    # Extract job-specific fields from visible text
    visible_text = soup.get_text(separator=" ", strip=True)
    result.update(_extract_job_fields(visible_text))

    # Also try extracting from the description itself if location/pay not found
    desc_text = result.get("description", "")
    if desc_text and (not result.get("pay_rate") or not result.get("location")):
        result.update(_extract_job_fields(desc_text))

    result["source_domain"] = source_domain

    # Auto-detect category
    all_text = f"{result.get('title', '')} {result.get('description', '')} {visible_text}"
    result["category"] = _detect_category(all_text, body.url)

    # Detect embed URL for video platforms (YouTube, Vimeo, TikTok, Facebook, Instagram)
    embed = to_embed_url(body.url)
    if embed:
        result["embed_url"] = embed
        result["platform"] = get_platform_name(body.url)
    # Also try the OG video URL if it's a video platform
    elif result.get("video_url"):
        embed = to_embed_url(result["video_url"])
        if embed:
            result["embed_url"] = embed
            result["platform"] = get_platform_name(result["video_url"])

    return ImportURLResponse(**result)
