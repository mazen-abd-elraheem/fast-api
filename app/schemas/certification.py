"""
Sanaie Platform — Certification Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class CertificationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    category: str = Field("general", max_length=50)


class CertificationUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r'^(verified|rejected)$')
    rejection_reason: Optional[str] = None


class CertificationResponse(BaseModel):
    cert_id: str
    worker_id: str
    name: str
    category: str
    status: str
    file_url: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    worker_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
