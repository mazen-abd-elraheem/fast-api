"""
Sanaie Platform — Job Assignment Model
Tracks tasks delegated by a contractor to their technicians.
Supports both platform job delegation and internal task creation.
Includes time tracking: started_at, completed_at, auto-computed duration_minutes.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class JobAssignment(Base):
    __tablename__ = "job_assignments"

    assignment_id = Column(String(36), primary_key=True, index=True)
    contractor_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    technician_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional link to a platform job (nullable for internal tasks)
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="SET NULL"), nullable=True, index=True)

    # Assignment details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    # Statuses: pending, in_progress, on_the_way, work_started, completed, canceled

    # Location (where the work needs to be done)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)

    # Time tracking
    started_at = Column(DateTime, nullable=True)     # When tech marks "work started"
    completed_at = Column(DateTime, nullable=True)    # When tech marks "done"
    duration_minutes = Column(Integer, nullable=True)  # Auto-computed on completion

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    contractor = relationship("User", foreign_keys=[contractor_id])
    technician = relationship("User", foreign_keys=[technician_id])
    job = relationship("Job", foreign_keys=[job_id])

    def __repr__(self):
        return f"<JobAssignment(id={self.assignment_id}, title={self.title}, status={self.status})>"
