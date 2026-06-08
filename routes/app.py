"""FastAPI app factory for Day Shift Marketplace."""
import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .deps import init_db, get_conn

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
from .push import api as push_router


def create_app(static_dir: str = "./dist") -> FastAPI:
    # ── Sentry error monitoring ───────────────────────────────────────────
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=os.environ.get("SENTRY_ENV", "production"),
            release=os.environ.get("SENTRY_RELEASE", "1.0.0"),
        )

    try:
        init_db()
    except Exception as e:
        print(f"[DB] FATAL: Could not initialize DB: {e}")
        # Don't crash — let the app start so /api/health can report the DB is down

    app = FastAPI()

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
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
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
    app.include_router(push_router, prefix="/api")

    if os.path.isdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        _resolved_static = os.path.realpath(static_dir)

        @app.get("/{path:path}")
        async def spa_fallback(request: Request, path: str):
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
