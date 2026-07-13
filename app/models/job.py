from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey, Enum as SAEnum, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base
from app.enums import JobCategory, JobStatus


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String(36), primary_key=True, index=True)
    client_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Job details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="open")
    image_url = Column(String(500), nullable=True)
    initial_price = Column(Numeric(10, 2), nullable=False)  # Decimal for money

    # Job location (where the work needs to be done)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)

    # Assigned worker (set when a bid is accepted)
    assigned_worker_id = Column(String(36), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("User", foreign_keys=[client_id], back_populates="jobs_as_client")
    assigned_worker = relationship("User", foreign_keys=[assigned_worker_id], back_populates="jobs_as_worker")
    bids = relationship("Bid", back_populates="job", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(job_id={self.job_id}, title={self.title}, status={self.status})>"
