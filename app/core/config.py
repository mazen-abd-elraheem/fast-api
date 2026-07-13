"""
Sanaie Platform — Config with new settings for refresh tokens, rate limiting, etc.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging
from typing import List

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from .env file"""

    APP_NAME: str = "Sanaie Platform"
    API_VERSION: str = "v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # MySQL Database
    DATABASE_URL: str = "mysql+pymysql://root:password@127.0.0.1:3306/sanaie_db"

    # Security
    SECRET_KEY: str = "change-this-to-a-secure-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File Uploads
    UPLOAD_DIR: str = "./uploaded_images"
    MAX_UPLOAD_SIZE_MB: int = 10

    # CORS — stored as a plain str so pydantic-settings never tries to JSON-parse it.
    # Set in Railway as a comma-separated string: https://a.com,https://b.com
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list (comma-separated or single value)."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    # Server
    SERVER_HOST: str = "http://localhost:8000"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        case_sensitive = True
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    logger.info(f"✓ Settings loaded for {settings.ENVIRONMENT} environment")
    return settings


settings = get_settings()
