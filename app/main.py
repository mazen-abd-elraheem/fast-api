"""
Sanaie Platform — Application Entry Point
FastAPI app with lifespan, middleware, global exception handler, and router registration.
"""
import os
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.database import engine, test_connection
from app.core.exceptions import (
    SanaieException,
    NotFoundException,
    DuplicateException,
    ForbiddenException,
    BadRequestException,
    UnauthorizedException,
)
from app.models import Base
from app.api.v1 import auth, users, jobs, bids, reviews, messages, notifications, admin, password_reset, contractor

settings = get_settings()
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


# ==========================================
# Application Lifespan
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f" Starting {settings.APP_NAME}")

    try:
        Base.metadata.create_all(bind=engine)
        logger.info(" Database tables created/verified")
        test_connection()
    except Exception as e:
        logger.warning(f" MySQL not available on startup: {e}")
        logger.warning("  → Start MySQL and the app will connect on first request.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f" Upload directory ready: {settings.UPLOAD_DIR}")

    yield

    logger.info(" Shutting down...")
    engine.dispose()


# ==========================================
# FastAPI Application
# ==========================================
app = FastAPI(
    title=settings.APP_NAME,
    description="A decentralized marketplace for home and professional services. "
                "Connects clients with verified technicians through competitive bidding.",
    version="2.0.0",
    lifespan=lifespan,
    # Hide API docs in production
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)


# ==========================================
# Global Exception Handlers
# ==========================================
@app.exception_handler(SanaieException)
async def sanaie_exception_handler(request: Request, exc: SanaieException):
    """Convert domain exceptions to proper HTTP responses."""
    status_map = {
        NotFoundException: 404,
        DuplicateException: 409,
        ForbiddenException: 403,
        BadRequestException: 400,
        UnauthorizedException: 401,
    }
    status_code = status_map.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content={"detail": exc.message})


# ==========================================
# Rate Limiting
# ==========================================
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ==========================================
# Middleware
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Request Logging Middleware
# ==========================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, duration, and status."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    if not request.url.path.startswith("/static"):
        logger.info(
            "%s %s → %s (%.2fs)",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
    else:
        # Add cache headers for static files (uploads)
        response.headers["Cache-Control"] = "public, max-age=2592000, immutable"
    return response


# ==========================================
# Root Redirect
# ==========================================
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# ==========================================
# Health Check
# ==========================================
@app.get("/health", tags=["Health"])
async def health_check():
    db_status = "unknown"
    try:
        test_connection()
        db_status = "connected"
    except Exception:
        db_status = "disconnected — start MySQL with: net start MySQL80"
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "database": db_status,
    }


# ==========================================
# Register Routers
# ==========================================
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(bids.router, prefix="/api/v1/bids", tags=["Bids"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["Reviews"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Messages"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(password_reset.router, prefix="/api/v1/auth/password", tags=["Password Reset"])
app.include_router(contractor.router, prefix="/api/v1/contractor", tags=["Contractor"])


# ==========================================
# Static Files (uploaded images) — must be AFTER routers
# ==========================================
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount(
    "/static/uploads",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)

logger.info(f" {settings.APP_NAME} v2.0.0 — all routers registered")
