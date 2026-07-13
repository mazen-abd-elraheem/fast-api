"""
Sanaie Platform — User Schemas (Pydantic v2)
"""
import re
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime

from app.enums import UserRole


# --- Input Schemas ---

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.CLIENT
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[0-9]{7,15}$')
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    skills: Optional[List[str]] = None  # JSON array: ["plumbing", "electrical"]

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[0-9]{7,15}$')
    skills: Optional[List[str]] = None
    profile_image_url: Optional[str] = None
    is_available: Optional[str] = Field(None, pattern=r'^(available|busy|offline)$')
    role: Optional[str] = Field(None, pattern=r'^(client|worker|contractor|moderator|editor|admin)$')


class UserLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class AdminUserUpdate(BaseModel):
    """Admin-level profile update — can change any field including password."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern=r'^(client|worker|contractor|moderator|editor|admin)$')
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    new_password: Optional[str] = Field(None, min_length=6, max_length=128)
    skills: Optional[List[str]] = None
    is_available: Optional[str] = Field(None, pattern=r'^(available|busy|offline|banned|suspended)$')


class AdminCreateStaff(BaseModel):
    """Schema for creating admin/editor/moderator accounts."""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., pattern=r'^(moderator|editor|admin)$')


# --- Output Schemas ---

class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    phone_number: Optional[str] = None
    role: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    skills: Optional[List[str]] = None
    profile_image_url: Optional[str] = None
    is_available: Optional[str] = None
    is_verified: Optional[str] = "unverified"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPublicResponse(BaseModel):
    """Public profile — no email/phone exposed"""
    user_id: str
    name: str
    role: str
    skills: Optional[List[str]] = None
    profile_image_url: Optional[str] = None
    is_available: Optional[str] = None
    is_verified: Optional[str] = "unverified"
    avg_rating: Optional[float] = None
    total_reviews: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class WorkerNearbyResponse(UserPublicResponse):
    """Worker with distance info for geo-filtering"""
    distance_km: Optional[float] = None
