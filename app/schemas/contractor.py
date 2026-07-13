"""
Sanaie Platform — Contractor Schemas (Pydantic v2)
Request/Response models for contractor team management and job assignments.
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime


# ── Team Management ──

class AddMemberRequest(BaseModel):
    technician_email: EmailStr = Field(..., description="Email of the technician to add")


class GroupMemberResponse(BaseModel):
    user_id: str
    name: str
    email: str
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_available: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Assignment Management ──

class AssignmentCreate(BaseModel):
    technician_id: str = Field(..., description="ID of the technician to assign")
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    job_id: Optional[str] = Field(None, description="Optional platform job to link")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)


class AssignmentResponse(BaseModel):
    assignment_id: str
    contractor_id: str
    technician_id: str
    technician_name: Optional[str] = None
    job_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignmentListResponse(BaseModel):
    assignments: List[AssignmentResponse]
    total: int


# ── Tracking ──

class TechnicianLocationResponse(BaseModel):
    user_id: str
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: Optional[str] = None
    profile_image_url: Optional[str] = None
    current_assignment: Optional[AssignmentResponse] = None

    model_config = ConfigDict(from_attributes=True)
