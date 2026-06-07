"""FastAPI app factory for Day Shift Marketplace."""
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .deps import init_db

from .auth import api as auth_router
from .videos import api as videos_router
from .matches import api as matches_router
from .chat import api as chat_router
from .users import api as users_router
from .upload import api as upload_router
from .bookmarks import api as bookmarks_router
from .blocks import api as blocks_router
from .tips import api as tips_router
from .reports import api as reports_router
from .support import api as support_router
from .sponsors import api as sponsors_router
from .advertiser import api as advertiser_router
from .admin import api as admin_router
from .webhooks import api as webhooks_router


def create_app(static_dir: str = "./dist") -> FastAPI:
    try:
        init_db()
    except Exception as e:
        print(f"[DB] Warning: Could not initialize DB: {e}")

    app = FastAPI()

    # ── Rate limiting ─────────────────────────────────────────────────────
    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── Security headers ──────────────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        return response

    # ── CORS ──────────────────────────────────────────────────────────────
    custom_domain = os.environ.get("WORKSHOP_CUSTOM_DOMAIN")
    allowed_origins = [f"https://{custom_domain}"] if custom_domain else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"ok": True}

    app.include_router(auth_router, prefix="/api")
    app.include_router(videos_router, prefix="/api")
    app.include_router(matches_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")
    app.include_router(bookmarks_router, prefix="/api")
    app.include_router(blocks_router, prefix="/api")
    app.include_router(tips_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(support_router, prefix="/api")
    app.include_router(sponsors_router, prefix="/api")
    app.include_router(advertiser_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(webhooks_router, prefix="/api")

    if os.path.isdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{path:path}")
        async def spa_fallback(request: Request, path: str):
            file_path = os.path.join(static_dir, path)
            if path and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(
                os.path.join(static_dir, "index.html"),
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )

    return app
