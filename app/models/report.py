"""
Sanaie Platform — Report Model
User-submitted problem reports for admin oversight.
"""
from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime, timezone

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    user_name = Column(String(255), nullable=True)

    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, default="general")

    # Status: open, in_progress, resolved
    status = Column(String(20), nullable=False, default="open")

    # Priority: low, medium, high, escalated
    priority = Column(String(20), nullable=False, default="medium")

    assigned_to = Column(String(36), nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Report(report_id={self.report_id}, subject={self.subject}, status={self.status})>"
