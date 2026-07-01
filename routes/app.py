"""FastAPI app factory for Day Shift Marketplace."""
import io
import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import qrcode
from PIL import Image as PILImage

from .deps import init_db, get_conn

from .auth import api as auth_router
from .videos import api as videos_router
from .matches import api as matches_router
from .chat import api as chat_router
from .users import api as users_router
from .upload import api as upload_router
from .bookmarks import api as bookmarks_router
from .blocks import api as blocks_router
from .reports import api as reports_router
from .support import api as support_router
from .sponsors import api as sponsors_router
from .advertiser import api as advertiser_router
from .admin import api as admin_router
from .webhooks import api as webhooks_router
from .push import api as push_router
from .import_url import api as import_url_router
from .legal import api as legal_router
from .ai import api as ai_router
from .paypal import api as paypal_router



def create_app(static_dir: str = "./dist") -> FastAPI:
    try:
        init_db()
    except Exception as e:
        print(f"[DB] FATAL: Could not initialize DB: {e}")
        # Don't crash — let the app start so /api/health can report the DB is down

    app = FastAPI()

    @app.get("/")
    async def root_redirect():
        return RedirectResponse(url="https://app.dayshiftnow.me", status_code=302)

    # ── Rate limiting ─────────────────────────────────────────────────────
    def _get_client_ip(request: Request) -> str:
        """Use X-Forwarded-For when behind a proxy (Cloudflare), fallback to direct IP."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return get_remote_address(request)

    limiter = Limiter(key_func=_get_client_ip, default_limits=["60/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── Security headers ──────────────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        # Skip security headers for promo QR images (browsers need to load them directly)
        if request.url.path.startswith("/api/promo/"):
            return response
        response.headers["X-Content-Type-Options"] = "nosniff"
        # X-Frame-Options must be SAMEORIGIN (not DENY) for embedded video iframes
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # CSP — allow inline styles/scripts (needed for Vite/Tailwind), self for images/media, video platforms + Stripe for frames
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://us.i.posthog.com https://us.posthog.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "media-src 'self' blob: https:; "
            "frame-src https://www.youtube.com https://youtube.com https://youtu.be https://player.vimeo.com https://vimeo.com https://www.tiktok.com https://tiktok.com https://www.instagram.com https://instagram.com https://platform.x.com https://twitter.com https://js.stripe.com https://hooks.stripe.com; "
            "connect-src 'self' https://api.stripe.com https://us.i.posthog.com https://us.posthog.com; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        return response

    # ── CORS ──────────────────────────────────────────────────────────────
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    allowed_origins = []
    if custom_domain:
        allowed_origins.append(f"https://{custom_domain}")
    # Allow preview/sandbox origins
    allowed_origins.extend([
        "https://day-shift.workshop.build",
        "http://localhost:3001",
        "http://localhost:5173",
    ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return {"ok": True, "db": "connected"}
        except Exception:
            return {"ok": False, "db": "unreachable"}

    # ── QR Code Promo Generator ───────────────────────────────────────────
    @app.get("/api/promo/qr/{style}")
    async def promo_qr(style: str, request: Request):
        """Generate a promotional QR code image that links to the Day Shift landing page.

        Styles:
          - flyer     : Print-ready 8.5×11 inch (2550×3300px) with logo-as-QR, tagline, features
          - social    : Square 1080×1080 for Instagram/LinkedIn/TikTok
          - story     : Portrait 1080×1920 for Instagram Stories/Snapchat
          - sticker   : Small 612×612 for print stickers (Avery 22806)
        """
        custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN", "")
        if custom_domain:
            base_url = f"https://{custom_domain}"
        else:
            origin = request.headers.get("origin", "")
            base_url = origin or "https://day-shift.workshop.build"

        target_url = base_url.rstrip("/")

        # ── Build the QR code with embedded logo ──────────────────────
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=20,
            border=2,
        )
        qr.add_data(target_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#f97316", back_color="transparent").convert("RGBA")

        # Load logo and composite into center of QR
        try:
            logo_path = os.path.join(static_dir, "dayshift-logo.png")
            if not os.path.isfile(logo_path):
                logo_path = "./public/dayshift-logo.png"
            logo = PILImage.open(logo_path).convert("RGBA")

            # Calculate logo size (~25% of QR dimension)
            qr_w, qr_h = qr_img.size
            logo_size = int(qr_w * 0.25)
            logo_resized = logo.resize((logo_size, logo_size), PILImage.LANCZOS)

            # Create circular mask for logo
            mask = PILImage.new("L", (logo_size, logo_size), 0)
            from PIL import ImageDraw as PILDraw
            draw = PILDraw.Draw(mask)
            draw.ellipse([0, 0, logo_size - 1, logo_size - 1], fill=255)

            # White padding behind logo so QR is readable through it
            pad = int(logo_size * 0.15)
            padded_size = logo_size + 2 * pad
            white_bg = PILImage.new("RGBA", (padded_size, padded_size), (255, 255, 255, 255))
            paste_x = (padded_size - logo_size) // 2
            white_bg.paste(logo_resized, (paste_x, paste_x), mask)
            padded_mask = PILImage.new("L", (padded_size, padded_size), 0)
            mdraw = PILDraw.Draw(padded_mask)
            mdraw.ellipse([0, 0, padded_size - 1, padded_size - 1], fill=255)

            pos = ((qr_w - padded_size) // 2, (qr_h - padded_size) // 2)
            qr_img.paste(white_bg, pos, padded_mask)
        except Exception:
            pass  # QR without logo still works

        # ── Compose final image based on style ─────────────────────────
        if style == "flyer":
            W, H = 2550, 3300
        elif style == "social":
            W, H = 1080, 1080
        elif style == "story":
            W, H = 1080, 1920
        elif style == "sticker":
            W, H = 612, 612
        else:
            # Return raw QR code for unknown styles
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            return Response(content=buf.getvalue(), media_type="image/png")

        canvas = PILImage.new("RGB", (W, H), "#0c0a09")  # bg-background equivalent

        from PIL import ImageFont, ImageDraw as PILDraw
        draw = PILDraw.Draw(canvas)

        # Try to load fonts; fall back to default
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(W * 0.08))
            font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(W * 0.03))
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(W * 0.022))
            font_tagline = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", int(W * 0.035))
        except Exception:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tagline = ImageFont.load_default()

        orange = "#f97316"
        white = "#fafaf9"
        gray = "#a8a29e"
        dark_bg = "#1c1917"

        # ── FLYER layout ──────────────────────────────────────────────
        if style == "flyer":
            # Top accent bar
            draw.rectangle([0, 0, W, int(H * 0.04)], fill=orange)

            # Title block
            y = int(H * 0.08)
            draw.text((W // 2, y), "DAY SHIFT", fill=orange, font=font_title, anchor="mt")
            y += int(W * 0.10)
            draw.text((W // 2, y), "Built for Culinarians That Move Fast.", fill=white, font=font_tagline, anchor="mt")

            # Subtitle
            y += int(W * 0.06)
            for line in ["The video-first marketplace connecting culinary", "workers with kitchens — in real time."]:
                bbox = draw.textbbox((0, 0), line, font=font_body)
                lw = bbox[2] - bbox[0]
                draw.text(((W - lw) // 2, y), line, fill=gray, font=font_body)
                y += int(W * 0.04)

            # QR Code centered
            qr_size = int(W * 0.45)
            qr_resized = qr_img.resize((qr_size, qr_size), PILImage.LANCZOS)
            qr_x = (W - qr_size) // 2
            y_qr = int(H * 0.28)
            canvas.paste(qr_resized, (qr_x, y_qr), qr_resized.convert("RGBA"))

            # Scan instruction below QR
            draw.text((W // 2, y_qr + qr_size + int(W * 0.02)),
                "SCAN TO DOWNLOAD THE APP",
                fill=orange, font=font_body, anchor="mt")

            # Feature bullets
            features_flyer = [
                "Post 60-second video profiles — show your skills, not just paper.",
                "Swipe & match with kitchens instantly — no more waiting on callbacks.",
                "In-app chat to confirm shifts, coordinate details, get paid.",
                "Reviews & ratings build your reputation — top talent gets seen first.",
                "Sell equipment, find gigs, promote events — your culinary community hub.",
            ]
            bullet_y = int(H * 0.58)
            for feat in features_flyer:
                # Bullet dot
                draw.ellipse([int(W * 0.18), bullet_y + int(W * 0.008), int(W * 0.185), bullet_y + int(W * 0.023)], fill=orange)
                draw.text((int(W * 0.21), bullet_y), feat, fill=white, font=font_body)
                bullet_y += int(W * 0.055)

            # Bottom CTA bar
            bar_y = int(H * 0.88)
            draw.rectangle([0, bar_y, W, H], fill=dark_bg)
            draw.text((W // 2, bar_y + int(W * 0.02)),
                "dayshiftnow.me", fill=orange, font=font_title, anchor="mt")
            draw.text((W // 2, bar_y + int(W * 0.08)),
                "Available on iOS & Android — Download Free Today",
                fill=gray, font=font_small, anchor="mt")

        # ── SOCIAL / SQUARE layout ─────────────────────────────────────
        elif style == "social":
            # Gradient-like background using rectangles
            for i in range(H):
                alpha = int(20 + (i / H) * 40)
                r, g, b = 249, 115, 22  # orange tint
                draw.line([(0, i), (W, i)], fill=(12 + int(r * i / H * 0.05), 10 + int(g * i / H * 0.02), 9, 255))

            # Brand at top
            draw.text((W // 2, int(H * 0.07)), "DAY SHIFT", fill=orange, font=font_title, anchor="mt")
            draw.text((W // 2, int(H * 0.15)), "Scan to Join the Crew", fill=white, font=font_body, anchor="mt")

            # Large QR
            qr_size = int(W * 0.58)
            qr_resized = qr_img.resize((qr_size, qr_size), PILImage.LANCZOS)
            canvas.paste(qr_resized, ((W - qr_size) // 2, int(H * 0.22)), qr_resized.convert("RGBA"))

            # Tagline at bottom
            draw.text((W // 2, int(H * 0.85)),
                "Culinary Staff Marketplace",
                fill=gray, font=font_body, anchor="mt")
            draw.text((W // 2, int(H * 0.92)),
                "@dayshiftnow.me", fill=orange, font=font_body, anchor="mt")

        # ── STORY / PORTRAIT layout ────────────────────────────────────
        elif style == "story":
            # Dark gradient background
            for i in range(H):
                shade = int(12 + (i / H) * 8)
                draw.line([(0, i), (W, i)], fill=(shade, int(shade * 0.85), int(shade * 0.75), 255))

            # Brand header
            draw.text((W // 2, int(H * 0.06)), "DAY SHIFT", fill=orange, font=font_title, anchor="mt")
            draw.text((W // 2, int(H * 0.13)), "The Culinary Staff App", fill=white, font=font_tagline, anchor="mt")

            # QR takes center stage
            qr_size = int(W * 0.70)
            qr_resized = qr_img.resize((qr_size, qr_size), PILImage.LANCZOS)
            canvas.paste(qr_resized, ((W - qr_size) // 2, int(H * 0.22)), qr_resized.convert("RGBA"))

            # Scan prompt
            draw.text((W // 2, int(H * 0.63)), "SCAN TO DOWNLOAD", fill=orange, font=font_body, anchor="mt")

            # Features list
            feats = ["Video Profiles", "Instant Matching", "In-App Chat", "Reviews & Ratings"]
            fy = int(H * 0.70)
            for f in feats:
                draw.text((W // 2, fy), f"✦  {f}", fill=white, font=font_body, anchor="mt")
                fy += int(W * 0.06)

            # Footer
            draw.text((W // 2, int(H * 0.94)), "dayshiftnow.me", fill=gray, font=font_small, anchor="mt")

        # ── STICKER layout ─────────────────────────────────────────────
        elif style == "sticker":
            # Rounded rect effect (simplified with filled rect)
            margin = int(W * 0.06)
            draw.rectangle([margin, margin, W - margin, H - margin], fill=dark_bg, outline=orange, width=int(W * 0.02))

            inner_margin = int(W * 0.10)
            # Small brand text
            draw.text((W // 2, inner_margin), "DAY SHIFT", fill=orange, font=font_body, anchor="mt")

            # QR fills most of the space
            qr_size = int(W * 0.55)
            qr_resized = qr_img.resize((qr_size, qr_size), PILImage.LANCZOS)
            canvas.paste(qr_resized, ((W - qr_size) // 2, int(H * 0.25)), qr_resized.convert("RGBA"))

            draw.text((W // 2, int(H * 0.84)), "SCAN ME", fill=orange, font=font_small, anchor="mt")

        # Save to buffer and return
        buf = io.BytesIO()
        canvas.save(buf, format="PNG", optimize=True)
        return Response(content=buf.getvalue(), media_type="image/png")

    app.include_router(auth_router, prefix="/api")
    app.include_router(videos_router, prefix="/api")
    app.include_router(matches_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")
    app.include_router(bookmarks_router, prefix="/api")
    app.include_router(blocks_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(support_router, prefix="/api")
    app.include_router(sponsors_router, prefix="/api")
    app.include_router(advertiser_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(webhooks_router, prefix="/api")
    app.include_router(push_router, prefix="/api")
    app.include_router(import_url_router, prefix="/api")
    app.include_router(legal_router)  # No prefix — serves /terms and /privacy at root
    # AI features are gated behind AI_ENABLED env var (default off)
    if os.environ.get("AI_ENABLED", "").lower() in ("1", "true", "yes"):
        app.include_router(ai_router, prefix="/api")
    app.include_router(paypal_router, prefix="/api")

    if os.path.isdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        _resolved_static = os.path.realpath(static_dir)

        @app.get("/{path:path}")
        async def spa_fallback(request: Request, path: str):
            # Don't intercept /api/ routes — let the routers handle them
            if path.startswith("api/"):
                raise HTTPException(404)

            # Resolve and validate path stays within static_dir
            resolved = os.path.realpath(os.path.join(static_dir, path))
            if path and os.path.isfile(resolved) and resolved.startswith(_resolved_static + os.sep):
                return FileResponse(resolved)
            return FileResponse(
                os.path.join(static_dir, "index.html"),
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )

    return app
