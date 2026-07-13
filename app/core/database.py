from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator
import logging

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# ==========================================
# MySQL Engine
# ==========================================
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10 if settings.ENVIRONMENT == "production" else 5,
    max_overflow=20 if settings.ENVIRONMENT == "production" else 10,
    pool_recycle=3600,
    pool_timeout=30,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for all models
Base = declarative_base()

logger.info("✓ MySQL database engine created")


# ==========================================
# Dependency Injection
# ==========================================
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ==========================================
# Startup Connection Test
# ==========================================
def test_connection():
    """Verify the database is reachable on startup."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✓ MySQL connection successful")
    except Exception as e:
        logger.error(f"✗ MySQL connection failed: {e}")
        raise
