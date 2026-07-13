"""
Sanaie Platform — Certification Model
Stores technician certifications with approval workflow.
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Certification(Base):
    __tablename__ = "certifications"

    cert_id = Column(String(36), primary_key=True, index=True)
    worker_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, default="general")
    status = Column(String(20), nullable=False, default="pending")  # pending, verified, rejected
    file_url = Column(String(500), nullable=True)  # URL to uploaded document
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)  # Admin who reviewed

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    worker = relationship("User", foreign_keys=[worker_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
