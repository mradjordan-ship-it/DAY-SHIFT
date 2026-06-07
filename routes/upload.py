"""Upload / media routes for Day Shift Marketplace."""
import uuid
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles

from .deps import get_current_user, UPLOAD_DIR, MAX_VIDEO_BYTES, MAX_IMAGE_BYTES

api = APIRouter()


@api.post("/upload/video")
async def upload_video(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    ext = Path(file.filename).suffix.lower() if file.filename else ".mp4"
    if ext not in (".mp4", ".mov", ".webm", ".avi"):
        raise HTTPException(400, "Only MP4, MOV, WEBM, and AVI files are allowed")
    # Validate MIME type
    content_type = (file.content_type or "").lower()
    if not any(t in content_type for t in ("video/", "application/octet-stream")):
        raise HTTPException(400, "Invalid file type — expected video")
        
    raw_filename = f"raw_{uuid.uuid4()}{ext}"
    raw_dest = UPLOAD_DIR / raw_filename

    # Save raw upload with size limit
    size = 0
    async with aiofiles.open(raw_dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > MAX_VIDEO_BYTES:
                raw_dest.unlink(missing_ok=True)
                raise HTTPException(400, f"Video exceeds {MAX_VIDEO_BYTES // (1024*1024)}MB limit")
            await f.write(chunk)

    # Transcode to H.264 MP4 (faststart, capped 1080p, AAC audio)
    from .deps import transcode_video
    final_filename = f"{uuid.uuid4()}.mp4"
    final_dest = UPLOAD_DIR / final_filename
    ok = await transcode_video(raw_dest, final_dest)

    if ok:
        raw_dest.unlink(missing_ok=True)  # delete raw after successful transcode
        return {"url": f"/api/media/{final_filename}"}
    else:
        # Transcode failed — serve raw upload as fallback
        print(f"[FFmpeg] transcode failed, serving raw file: {raw_filename}")
        return {"url": f"/api/media/{raw_filename}"}


@api.post("/upload/image")
async def upload_image(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        raise HTTPException(400, "Only JPG, PNG, WEBP, and GIF images are allowed")
    # Validate MIME type
    content_type = (file.content_type or "").lower()
    if not any(t in content_type for t in ("image/", "application/octet-stream")):
        raise HTTPException(400, "Invalid file type — expected image")
        
    filename = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / filename
    size = 0
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                dest.unlink(missing_ok=True)
                raise HTTPException(400, f"Image exceeds {MAX_IMAGE_BYTES // (1024*1024)}MB limit")
            await f.write(chunk)
    return {"url": f"/api/media/{filename}"}


@api.api_route("/media/{filename}", methods=["GET", "HEAD"])
async def serve_media(filename: str, request: Request):
    # Resolve and validate path to prevent traversal attacks
    resolved = (UPLOAD_DIR / filename).resolve()
    if not str(resolved).startswith(str(UPLOAD_DIR.resolve())):
        raise HTTPException(403, "Access denied")
    if not resolved.exists():
        raise HTTPException(404, "File not found")

    file_size = resolved.stat().st_size
    is_video = filename.lower().endswith((".mp4", ".webm", ".mov", ".avi"))
    video_content_type = "video/mp4"
    if filename.lower().endswith(".webm"):
        video_content_type = "video/webm"
    elif filename.lower().endswith(".mov"):
        video_content_type = "video/quicktime"
    elif filename.lower().endswith(".avi"):
        video_content_type = "video/x-msvideo"
    is_head = request.method == "HEAD"

    # For videos, support range requests so mobile can stream progressively
    if is_video:
        range_header = request.headers.get("range")
        if range_header:
            # Parse "bytes=start-end"
            range_match = range_header.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
            end = min(end, file_size - 1)
            chunk_size = end - start + 1

            range_headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Content-Type": video_content_type,
                "Cache-Control": "public, max-age=2592000, immutable",
            }

            if is_head:
                from starlette.responses import Response
                return Response(status_code=206, headers=range_headers)

            async def stream_range():
                async with aiofiles.open(str(resolved), "rb") as f:
                    await f.seek(start)
                    remaining = chunk_size
                    while remaining > 0:
                        read_size = min(remaining, 1024 * 1024)
                        data = await f.read(read_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            return StreamingResponse(
                stream_range(),
                status_code=206,
                headers=range_headers,
            )

        # No range header — full response with Accept-Ranges header
        if is_head:
            from starlette.responses import Response
            return Response(status_code=200, headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Content-Type": video_content_type,
                "Cache-Control": "public, max-age=2592000, immutable",
            })

        return FileResponse(
            str(resolved),
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=2592000, immutable",
            },
        )

    # Non-video media — cache for 30 days
    if is_head:
        from starlette.responses import Response
        content_type = "image/jpeg"
        if filename.lower().endswith(".png"):
            content_type = "image/png"
        elif filename.lower().endswith(".webp"):
            content_type = "image/webp"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"
        return Response(status_code=200, headers={
            "Content-Length": str(file_size),
            "Content-Type": content_type,
            "Cache-Control": "public, max-age=2592000, immutable",
        })

    return FileResponse(
        str(resolved),
        headers={
            "Cache-Control": "public, max-age=2592000, immutable",
        },
    )
