"""Shared dependencies for Day Shift Marketplace routes."""
import os
import uuid
import shutil
import asyncio
import aiofiles
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import bcrypt as _bcrypt
from jose import jwt, JWTError
import imageio_ffmpeg

from db import get_conn, init_db, db_conn

# ── Stripe Setup ──────────────────────────────────────────────────────────────
def _init_stripe():
    import stripe as _stripe
    key = os.environ.get("STRIPE_SECRET_KEY")
    if key:
        _stripe.api_key = key
    return _stripe

stripe = _init_stripe()

# ── Auth Setup ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required. Set it before starting the server.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_VIDEO_DURATION_SECONDS = 60       # Videos must be 60 seconds or less

bearer = HTTPBearer(auto_error=False)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()


async def get_video_duration(path: Path) -> float | None:
    """Return video duration in seconds using ffmpeg, or None on failure.
    
    Uses ffmpeg to probe the input file and parses duration from stderr output.
    This avoids needing ffprobe, which imageio_ffmpeg does not ship.
    """
    cmd = [
        FFMPEG_BIN,
        "-i", str(path),
        "-f", "null",
        "-t", "0",        # Don't actually decode frames — just probe
        "-",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        # ffmpeg writes input info to stderr, e.g.:
        #   Duration: 00:01:05.12, start: 0.000000, bitrate: 1234 kb/s
        import re
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr.decode(errors="replace"))
        if match:
            h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
            return h * 3600 + m * 60 + s
        return None
    except Exception:
        return None


async def transcode_video(src: Path, dest: Path) -> bool:
    """Transcode to H.264 MP4 with faststart + silent AAC audio. Caps at 720p for mobile compatibility.
    
    iOS Safari requires at least a silent audio stream for video playback,
    so we always include a mono AAC track even if the source has no audio.
    """
    cmd = [
        FFMPEG_BIN, "-y", "-i", str(src),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=44100",
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "fast",
        "-vf", "scale=-2:'min(720,ih)'",
        "-c:a", "aac",
        "-b:a", "96k",
        "-shortest",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(dest),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode != 0:
            print(f"[FFmpeg] error: {stderr.decode()[-500:]}")
            return False
        return True
    except Exception as e:
        print(f"[FFmpeg] exception: {e}")
        return False


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8")[:72], _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode())


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user["is_suspended"]:
        raise HTTPException(status_code=403, detail=f"Account suspended: {user['suspension_reason'] or 'Violation of community guidelines'}")
    return dict(user)


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        return None
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


def require_admin(current_user=Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
