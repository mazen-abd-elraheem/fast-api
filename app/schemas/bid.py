"""
Sanaie Platform — Bid Schemas (Pydantic v2)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from app.enums import BidStatus


# --- Input Schemas ---

class BidCreate(BaseModel):
    job_id: str
    amount: float = Field(..., gt=0, description="Worker's bid amount")
    message: Optional[str] = Field(None, max_length=2000, description="Worker's proposal message")
    scheduled_at: Optional[datetime] = Field(None, description="When technician plans to arrive")


class BidCounterOffer(BaseModel):
    counter_amount: float = Field(..., gt=0, description="Client's counter-offer amount")


# --- Output Schemas ---

class BidResponse(BaseModel):
    bid_id: str
    job_id: str
    worker_id: str
    worker_name: Optional[str] = None
    worker_avg_rating: Optional[float] = None
    worker_latitude: Optional[float] = None
    worker_longitude: Optional[float] = None
    amount: float
    message: Optional[str] = None
    counter_amount: Optional[float] = None
    status: str
    scheduled_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BidListResponse(BaseModel):
    bids: List[BidResponse]
    total: int
