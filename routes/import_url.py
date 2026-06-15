"""Import job data from an external URL via Open Graph meta tags, JSON-LD, and page scraping."""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

api = APIRouter()

# ── Regex patterns for field extraction ──

_PAY_KEYWORDS = re.compile(
    r"\$(\d[\d,.]*)\s*(?:/|per\s*)?(?:hr|hour|hrly|hourly|week|month|year|annually)?", re.I
)
_HOURS_KEYWORDS = re.compile(
    r"\b(\d[\d.]*)\s*(?:hrs?|hours?|shift\s*hours?)\b", re.I
)
_EXP_KEYWORDS = re.compile(
    r"\b(?:entry.level|junior|mid.level|senior|lead|executive|experienced)\b", re.I
)
# City, State pattern (e.g., "Columbus, OH", "New York, NY")
_CITY_STATE = re.compile(
    r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2})\b"
)
# Phone number
_PHONE = re.compile(
    r"(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})"
)
# Email
_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
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
    source_domain: str = ""
    category: str = "general"
    contact_info: str = ""


# ── Extraction helpers ──


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

    tw_player = soup.find("meta", attrs={"name": "twitter:player"})
    if tw_player and tw_player.get("content"):
        data.setdefault("video_url", tw_player["content"].strip())

    return data


def _extract_from_jsonld(soup: BeautifulSoup) -> dict:
    """Extract from JSON-LD structured data (schema.org JobPosting, etc.)."""
    data: dict = {}

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = script.string
            if not raw:
                continue
            ld = json.loads(raw)
            # Handle @graph arrays
            items = ld.get("@graph", [ld]) if isinstance(ld, dict) else ld if isinstance(ld, list) else [ld]

            for item in items:
                if not isinstance(item, dict):
                    continue
                schema_type = (item.get("@type") or "").lower()
                if isinstance(schema_type, list):
                    schema_type = " ".join(str(t).lower() for t in schema_type)

                # JobPosting schema
                if "jobposting" in schema_type:
                    if item.get("title"):
                        data.setdefault("title", item["title"])
                    if item.get("description"):
                        desc = item["description"]
                        # Strip HTML from description
                        if "<" in desc:
                            desc_soup = BeautifulSoup(desc, "html.parser")
                            desc = desc_soup.get_text(separator=" ", strip=True)
                        data.setdefault("description", desc[:2000])
                    if item.get("jobLocation"):
                        loc = item["jobLocation"]
                        if isinstance(loc, dict):
                            addr = loc.get("address", {})
                            if isinstance(addr, dict):
                                parts = [addr.get("addressLocality", ""), addr.get("addressRegion", "")]
                                location = ", ".join(p for p in parts if p)
                                if location:
                                    data["location"] = location
                            elif isinstance(addr, str):
                                data["location"] = addr
                    if item.get("baseSalary"):
                        salary = item["baseSalary"]
                        if isinstance(salary, dict):
                            value = salary.get("value", {})
                            if isinstance(value, dict):
                                min_val = value.get("minValue", "")
                                max_val = value.get("maxValue", "")
                                unit = value.get("unitText", "")
                                if min_val and max_val:
                                    data["pay_rate"] = f"${min_val}-${max_val}/{unit}" if unit else f"${min_val}-${max_val}"
                                elif min_val:
                                    data["pay_rate"] = f"${min_val}/{unit}" if unit else f"${min_val}"
                    if item.get("employmentType"):
                        emp_type = item["employmentType"]
                        if isinstance(emp_type, list):
                            emp_type = emp_type[0]
                        emp_map = {
                            "FULL_TIME": "Full-time",
                            "PART_TIME": "Part-time",
                            "CONTRACT": "Contract",
                            "TEMPORARY": "Temporary",
                        }
                        mapped = emp_map.get(emp_type.upper(), emp_type)
                        if not data.get("hours"):
                            data["hours"] = mapped
                    if item.get("experienceRequirements"):
                        data.setdefault("experience_level", item["experienceRequirements"])

                # Article / SocialMediaPosting schema
                if "article" in schema_type or "posting" in schema_type or "socialmediaposting" in schema_type:
                    if item.get("headline"):
                        data.setdefault("title", item["headline"])
                    if item.get("articleBody"):
                        data.setdefault("description", item["articleBody"][:2000])
                    if item.get("image"):
                        img = item["image"]
                        if isinstance(img, str):
                            data.setdefault("image_url", img)
                        elif isinstance(img, dict) and img.get("url"):
                            data.setdefault("image_url", img["url"])

                # Event schema
                if "event" in schema_type:
                    if item.get("name"):
                        data.setdefault("title", item["name"])
                    if item.get("description"):
                        data.setdefault("description", item["description"][:2000])
                    if item.get("location"):
                        loc = item["location"]
                        if isinstance(loc, dict):
                            name = loc.get("name", "")
                            addr = loc.get("address", {})
                            if isinstance(addr, dict):
                                parts = [addr.get("addressLocality", ""), addr.get("addressRegion", "")]
                                location = ", ".join(p for p in parts if p)
                                data["location"] = f"{name} — {location}" if name and location else name or location
                    if item.get("startDate"):
                        data.setdefault("event_date", item["startDate"][:10])

        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    return data


def _extract_from_html(soup: BeautifulSoup) -> dict:
    """Fallback: pull from <title>, meta description, and structured elements."""
    data: dict = {}

    if not data.get("title"):
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            # Clean up common suffixes like " | LinkedIn", " - Facebook"
            cleaned = re.sub(
                r"\s*[|\-–—]\s*(LinkedIn|Facebook|Indeed|Glassdoor|ZipRecruiter|Instagram|X|Twitter|YouTube|Vimeo|TikTok).*$",
                "",
                title_tag.string.strip(),
                flags=re.I,
            )
            data["title"] = cleaned

    if not data.get("description"):
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            data["description"] = meta_desc["content"].strip()

    # Try to find a good image from <img> tags if OG/Twitter didn't give us one
    if not data.get("image_url"):
        for img in soup.find_all("img", src=True):
            src = img.get("src", "")
            # Skip tiny icons, tracking pixels, data URIs
            if not src or src.startswith("data:") or "icon" in (img.get("class", []) or []):
                continue
            width = img.get("width", "")
            height = img.get("height", "")
            # Skip small images
            try:
                if width and int(width) < 100:
                    continue
                if height and int(height) < 100:
                    continue
            except (ValueError, TypeError):
                pass
            data["image_url"] = src
            break

    return data


def _extract_job_fields(text: str) -> dict:
    """Parse pay rate, hours, experience level, location from visible text."""
    data: dict = {}

    # Pay rate
    pay_match = _PAY_KEYWORDS.search(text)
    if pay_match:
        data["pay_rate"] = pay_match.group(0).strip()

    # Hours / shift patterns
    hours_match = _HOURS_KEYWORDS.search(text)
    if hours_match:
        data["hours"] = hours_match.group(0).strip()
    else:
        # Try time range patterns like "6pm-11pm", "9:00 AM - 5:00 PM"
        time_range = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*[-–—to]+\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))", text)
        if time_range and not data.get("hours"):
            data["hours"] = f"{time_range.group(1)}-{time_range.group(2)}"

    # Experience level
    exp_match = _EXP_KEYWORDS.search(text)
    if exp_match:
        data["experience_level"] = exp_match.group(0).strip().title()
    else:
        # Try "X+ years" patterns
        years_exp = re.search(r"(\d[\d+]*)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text, re.I)
        if years_exp:
            data["experience_level"] = f"{years_exp.group(0).strip()} experience"

    # Location — try multiple patterns
    if not data.get("location"):
        # Pattern: "Location: City, ST"
        loc_match = re.search(
            r"(?:location|city|area|address|where)\s*[:\-–]\s*(.+?)(?:[.\n|,;]|\s{2,}|$)", text, re.I
        )
        if loc_match:
            data["location"] = loc_match.group(1).strip()[:100]
        else:
            # Try City, State pattern
            city_match = _CITY_STATE.search(text)
            if city_match:
                data["location"] = city_match.group(0)

    # Cuisine type
    cuisine_match = re.search(
        r"(?:cuisine|cuisine type|food type|restaurant type|specialty)\s*[:\-–]\s*(.+?)(?:[.\n|,;]|\s{2,}|$)",
        text, re.I
    )
    if cuisine_match:
        data["cuisine_type"] = cuisine_match.group(1).strip()[:100]
    else:
        # Try to detect from keywords
        cuisine_types = {
            "italian": "Italian", "french": "French", "japanese": "Japanese",
            "sushi": "Japanese/Sushi", "mexican": "Mexican", "thai": "Thai",
            "chinese": "Chinese", "indian": "Indian", "korean": "Korean",
            "mediterranean": "Mediterranean", "seafood": "Seafood",
            "bbq": "BBQ", "barbecue": "BBQ", "bakery": "Bakery",
            "pastry": "Pastry", "steakhouse": "Steakhouse",
        }
        for kw, label in cuisine_types.items():
            if kw in text.lower():
                data["cuisine_type"] = label
                break

    # Contact info
    phone = _PHONE.search(text)
    email = _EMAIL.search(text)
    contacts = []
    if phone:
        contacts.append(phone.group(0))
    if email:
        contacts.append(email.group(0))
    if contacts:
        data["contact_info"] = " | ".join(contacts)

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
        "restaurant", "kitchen", "culinary", "cook needed",
        "staff needed", "recruiting", "career opportunity",
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
    job_board_domains = ["indeed.com", "ziprecruiter.com", "glassdoor.com", "linkedin.com/jobs", "simplyhired.com", "snagajob.com"]
    if any(domain in url_lower for domain in job_board_domains):
        return "kitchen"

    # Facebook group job posts
    if "facebook.com/groups" in url_lower:
        if has_kitchen:
            return "kitchen"
        if has_crew:
            return "crew"

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


def _make_image_absolute(image_url: str, base_url: str) -> str:
    """Convert relative image URLs to absolute."""
    if not image_url:
        return image_url
    if image_url.startswith("//"):
        return f"https:{image_url}"
    if image_url.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{image_url}"
    if not image_url.startswith("http"):
        return urljoin(base_url, image_url)
    return image_url


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
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
                "Accept-Language": "en-US,en;q=0.9",
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

    # Remove script/style/nav elements for cleaner text extraction
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Extract in priority order: JSON-LD → OG → Twitter → plain HTML
    result: dict = {}
    result.update(_extract_from_jsonld(soup))
    result.update(_extract_from_og(soup))
    result.update(_extract_from_twitter(soup))
    result.update(_extract_from_html(soup))

    # Extract job-specific fields from visible text
    visible_text = soup.get_text(separator=" ", strip=True)
    # Clean up excessive whitespace
    visible_text = re.sub(r"\s{3,}", " ", visible_text)
    result.update(_extract_job_fields(visible_text))

    # Also try extracting from the description itself if location/pay not found
    desc_text = result.get("description", "")
    if desc_text and (not result.get("pay_rate") or not result.get("location")):
        result.update(_extract_job_fields(desc_text))

    # Make image URLs absolute
    if result.get("image_url"):
        result["image_url"] = _make_image_absolute(result["image_url"], str(resp.url))

    result["source_domain"] = source_domain

    # Auto-detect category
    all_text = f"{result.get('title', '')} {result.get('description', '')} {visible_text}"
    result["category"] = _detect_category(all_text, body.url)

    # Clean description — remove excessive length
    if result.get("description") and len(result["description"]) > 2000:
        result["description"] = result["description"][:2000] + "..."

    return ImportURLResponse(**result)
