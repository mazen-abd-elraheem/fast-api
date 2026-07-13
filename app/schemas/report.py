"""
Sanaie Platform — Report Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = "general"
    priority: Optional[str] = "medium"


class ReportResponse(BaseModel):
    report_id: str
    user_id: str
    user_name: Optional[str] = None
    subject: str
    description: Optional[str] = None
    category: Optional[str] = None
    status: str
    priority: str
    assigned_to: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
