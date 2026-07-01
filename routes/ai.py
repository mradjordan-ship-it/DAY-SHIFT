"""AI-powered shift parsing and job matching routes for Day Shift Marketplace.

Uses Gemini with structured JSON outputs and robust retry/validation logic.
"""
import json
import os
import re
from datetime import datetime, date, time, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator

from .deps import get_conn, get_current_user

api = APIRouter()

# ── Gemini client (Workshop proxy) — lazy init ──────────────────────────

def _get_client() -> genai.Client:
    """Create Gemini client on first use (ensures env vars are loaded)."""
    return genai.Client(
        api_key=os.environ.get("STRIPE_GOOGLE_API_KEY"),
        http_options={
            "api_version": "v1alpha",
            "base_url": os.environ.get("STRIPE_GOOGLE_BASE_URL"),
        },
    )

# ── Retry config ──────────────────────────────────────────────────────────
MAX_RETRIES = 3


def _call_llm_with_retry(prompt: str, schema: dict) -> dict:
    """Call Gemini with JSON schema enforcement and retry on parse failures."""
    full_prompt = (
        f"{prompt}\n\n"
        f"Respond with ONLY valid JSON matching this exact schema. "
        f"No markdown fences, no explanation, no extra text:\n\n"
        f"{json.dumps(schema, indent=2)}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _client = _get_client()
            response = _client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=types.Schema(**schema),
                ),
            )
            raw = response.text.strip()
            # Strip any accidental markdown code fences
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)

            # Validate required top-level keys exist
            for key in schema.get("properties", {}):
                if key in schema.get("required", []) and key not in data:
                    raise ValueError(f"Missing required key: {key}")

            return data

        except json.JSONDecodeError as e:
            print(f"[AI] Attempt {attempt}/{MAX_RETRIES} JSON parse error: {e}")
            if attempt == MAX_RETRIES:
                raise HTTPException(
                    502,
                    f"AI service returned invalid JSON after {MAX_RETRIES} attempts. "
                    f"Please try rephrasing your input.",
                )
        except ValueError as e:
            print(f"[AI] Attempt {attempt}/{MAX_RETRIES} schema validation error: {e}")
            if attempt == MAX_RETRIES:
                raise HTTPException(
                    502,
                    f"AI response missing required fields after {MAX_RETRIES} attempts: {e}",
                )
        except Exception as e:
            err_str = str(e).lower()
            print(f"[AI] Attempt {attempt}/{MAX_RETRIES} failed: {type(e).__name__}: {e}")
            if "rate" in err_str or "quota" in err_str or "429" in err_str:
                raise HTTPException(429, "AI rate limit reached — please wait a moment and retry.")
            if attempt == MAX_RETRIES:
                raise HTTPException(
                    502,
                    f"AI service error after {MAX_RETRIES} attempts: {type(e).__name__}: {e}",
                )

    raise HTTPException(502, "Unexpected AI failure.")


# ══════════════════════════════════════════════════════════════════════════
# STEP 1 — Shift Parsing: /api/shifts/parse
# ══════════════════════════════════════════════════════════════════════════

SHIFT_PARSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "description": "Concise job title like 'Line Cook - Dinner Shift'"},
        "description": {"type": "STRING", "description": "Full shift description with duties and environment"},
        "category": {
            "type": "STRING",
            "description": "One of: line_cook, prep_cook, dishwasher, server, bartender, host, sous_chef, expeditor, other",
        },
        "role": {"type": "STRING", "description": "Role label like 'Line Cook', 'Server', 'Dishwasher'"},
        "event_date": {
            "type": "STRING",
            "description": "Date in YYYY-MM-DD format. If user said 'today', use today's date. If 'tomorrow', use tomorrow.",
        },
        "start_time": {"type": "STRING", "description": "Start time in 24-hour HH:MM format"},
        "end_time": {"type": "STRING", "description": "End time in 24-hour HH:MM format"},
        "pay_rate": {
            "type": "NUMBER",
            "description": "Hourly pay rate as a number. If not mentioned, use null or a reasonable default for the role (15-25).",
        },
        "special_requirements": {
            "type": "STRING",
            "description": "Any special requirements like 'fast-paced', 'must lift 50lbs', 'Spanish preferred'. Empty string if none.",
        },
        "location_hint": {
            "type": "STRING",
            "description": "Location info extracted from text. Empty string if none provided.",
        },
    },
    "required": ["title", "description", "category", "role", "event_date", "start_time", "end_time"],
}


class ParseShiftBody(BaseModel):
    raw_text: str = Field(..., min_length=3, max_length=2000, description="Unstructured shift description from restaurant manager")


@field_validator("raw_text")
@classmethod
def clean_raw_text(cls, v: str) -> str:
    return v.strip()


@api.post("/shifts/parse")
async def parse_shift(body: ParseShiftBody, current_user=Depends(get_current_user)):
    """Parse unstructured text into a structured shift using AI.

    Accepts freeform input like 'need line cook tonight 5-11 fast pace $18/hr'
    and returns validated, schema-compliant shift data ready for video creation.
    """
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    day_after = (date.today() + timedelta(days=2)).isoformat()

    prompt = (
        f"You are a shift parsing assistant for Day Shift, a culinary worker marketplace.\n"
        f"Today's date is {today}, tomorrow is {tomorrow}.\n\n"
        f"Parse this restaurant manager's input into structured shift data:\n\n"
        f'"""{body.raw_text}"""\n\n'
        f"Rules:\n"
        f"- Extract role, date, times, pay rate, and any special requirements.\n"
        f"- For dates: 'today' = {today}, 'tonight' = {today}, 'tomorrow' = {tomorrow}. "
        f"If no date is given, assume {tomorrow}.\n"
        f"- Times must be in 24-hour HH:MM format. '5-11' means 17:00 to 23:00.\n"
        f"- Pay rate should be a number. If none given, use a reasonable default for the role.\n"
        f"- Category must be one of: line_cook, prep_cook, dishwasher, server, bartender, host, sous_chef, expeditor, other.\n"
        f"- Generate a clear title and description suitable for a job posting.\n"
        f"- NEVER invent data that isn't implied. Use null/empty for unknowns."
    )

    result = _call_llm_with_retry(prompt, SHIFT_PARSE_SCHEMA)

    # ── Post-LLM validation ───────────────────────────────────────────
    errors = []

    # Validate date format and not in the past
    try:
        parsed_date = date.fromisoformat(result["event_date"])
        if parsed_date < date.today():
            result["event_date"] = tomorrow
            errors.append("warn:date_was_in_past_corrected_to_tomorrow")
    except (ValueError, TypeError):
        result["event_date"] = tomorrow
        errors.append("warn:date_invalid_corrected_to_tomorrow")

    # Validate time format
    for time_field in ("start_time", "end_time"):
        try:
            time.fromisoformat(result[time_field])
        except (ValueError, TypeError):
            errors.append(f"error:invalid_{time_field}_format")

    # Validate pay_rate is non-negative
    pay = result.get("pay_rate")
    if pay is not None:
        try:
            pay_val = float(pay)
            if pay_val < 0:
                result["pay_rate"] = None
                errors.append("warn:negative_pay_corrected_to_null")
        except (TypeError, ValueError):
            result["pay_rate"] = None

    # Validate category against allowed values
    allowed_cats = {
        "line_cook", "prep_cook", "dishwasher", "server",
        "bartender", "host", "sous_chef", "expeditor", "other",
    }
    if result.get("category") not in allowed_cats:
        result["category"] = "other"
        errors.append("warn:invalid_category_corrected_to_other")

    # Build event_time string from start/end (matching existing video schema)
    start = result.get("start_time", "")
    end = result.get("end_time", "")
    result["event_time"] = f"{start}-{end}" if start and end else ""

    return {
        "ok": True,
        "parsed": result,
        "warnings": [e for e in errors if e.startswith("warn:")],
        "errors": [e for e in errors if e.startswith("error:")],
    }


# ══════════════════════════════════════════════════════════════════════════
# STEP 2 — AI Job Matching is in routes/matches.py as /api/matches/rank
# (Defined there to avoid route conflict with /matches/{match_id})
# ═════════════════════════════════════════════════════════════════════════†
# ── Improve Post Description ─────────────────────────────────────────────

IMPROVE_PROMPT = """You are a writing assistant for Day Shift, a video marketplace for kitchen and restaurant workers.

Improve the following post description. Make it more compelling, professional, and clear while keeping the original meaning and key details. Keep it concise — no more than 3-4 sentences. Use a friendly but professional tone.

Original: {text}

Return ONLY the improved text, no quotes, no explanation."""


class ImproveRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=2000)


IMPROVE_POST_RETRIES = 2


@api.post("/ai/improve-post")
async def improve_post(body: ImproveRequest, _user=Depends(get_current_user)):
    """Improve a post description using AI with retry and rate-limit handling."""
    prompt = IMPROVE_PROMPT.format(text=body.text)

    for attempt in range(1, IMPROVE_POST_RETRIES + 1):
        try:
            _client = _get_client()
            response = _client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
            )
            improved = response.text.strip()
            improved = improved.strip('"').strip("'")
            if not improved or len(improved) < 10:
                if attempt == IMPROVE_POST_RETRIES:
                    raise HTTPException(502, "AI returned empty or too-short response after retries")
                continue
            return {"improved": improved}
        except HTTPException:
            raise
        except Exception as e:
            err_str = str(e).lower()
            print(f"[AI-IMPROVE] Attempt {attempt}/{IMPROVE_POST_RETRIES} failed: {type(e).__name__}: {e}")
            if "rate" in err_str or "quota" in err_str or "429" in err_str:
                raise HTTPException(429, "AI rate limit — please wait a moment and retry.")
            if attempt == IMPROVE_POST_RETRIES:
                raise HTTPException(502, f"AI unavailable after {IMPROVE_POST_RETRIES} attempts: {type(e).__name__}")
    raise HTTPException(502, "AI improve-post failed.")

