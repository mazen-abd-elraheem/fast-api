from sqlalchemy import Column, String, DateTime, Float, Text, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base
from app.enums import UserRole


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone_number = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="client")

    # Geolocation
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Worker-specific fields
    skills = Column(JSON, nullable=True)  # Stored as JSON array: ["plumbing", "electrical"]
    profile_image_url = Column(String(500), nullable=True)

    # Worker availability
    is_available = Column(String(20), nullable=False, default="available")  # available, busy, offline

    # ID verification status
    is_verified = Column(String(20), nullable=False, default="unverified")  # unverified, pending, verified, rejected

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    jobs_as_client = relationship("Job", foreign_keys="Job.client_id", back_populates="client")
    jobs_as_worker = relationship("Job", foreign_keys="Job.assigned_worker_id", back_populates="assigned_worker")
    bids = relationship("Bid", back_populates="worker")
    reviews_given = relationship("Review", foreign_keys="Review.client_id", back_populates="client")
    reviews_received = relationship("Review", foreign_keys="Review.worker_id", back_populates="worker")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, name={self.name}, role={self.role})>"
