"""
Sanaie Platform — Job Schemas (Pydantic v2)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from app.enums import JobCategory, JobStatus


# --- Input Schemas ---

class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    category: JobCategory
    initial_price: float = Field(..., gt=0, description="Client's proposed price")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = Field(None, min_length=10)
    category: Optional[JobCategory] = None
    initial_price: Optional[float] = Field(None, gt=0)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)


# --- Output Schemas ---

class JobResponse(BaseModel):
    job_id: str
    client_id: str
    client_name: Optional[str] = None
    title: str
    description: str
    category: JobCategory
    status: JobStatus
    image_url: Optional[str] = None
    initial_price: float
    accepted_bid_amount: Optional[float] = None  # The accepted bid price (what worker actually earns)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    assigned_worker_name: Optional[str] = None
    bid_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobWithWorkerLocationResponse(JobResponse):
    """Job response enriched with the assigned worker's GPS coordinates."""
    worker_latitude: Optional[float] = None
    worker_longitude: Optional[float] = None
    worker_name_display: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
