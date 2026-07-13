"""
Sanaie Platform — Review Schemas (Pydantic v2)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# --- Input Schemas ---

class ReviewCreate(BaseModel):
    job_id: str
    worker_id: str
    rating_score: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=2000)


# --- Output Schemas ---

class ReviewResponse(BaseModel):
    review_id: str
    job_id: str
    client_id: str
    client_name: Optional[str] = None
    worker_id: str
    rating_score: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkerRatingResponse(BaseModel):
    worker_id: str
    avg_rating: float
    total_reviews: int


class ReviewListResponse(BaseModel):
    reviews: List[ReviewResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
