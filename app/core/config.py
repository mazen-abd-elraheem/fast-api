"""
Sanaie Platform — Config with new settings for refresh tokens, rate limiting, etc.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
import logging
import json
from typing import List, Any

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

    # CORS — accepts either a JSON array or a comma-separated string
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # Try JSON array first: ["https://a.com","https://b.com"]
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Fall back to comma-separated: https://a.com,https://b.com
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

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
