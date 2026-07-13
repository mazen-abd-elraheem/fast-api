"""
Sanaie Platform — Contractor Group Model
Tracks membership of technicians in contractor teams.
A technician can belong to multiple contractor groups simultaneously.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class ContractorGroup(Base):
    __tablename__ = "contractor_groups"

    contractor_group_id = Column(String(36), primary_key=True, index=True)
    contractor_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    technician_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active")  # active, removed

    # Timestamps
    joined_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    removed_at = Column(DateTime, nullable=True)

    # Relationships
    contractor = relationship("User", foreign_keys=[contractor_id])
    technician = relationship("User", foreign_keys=[technician_id])

    def __repr__(self):
        return f"<ContractorGroup(id={self.contractor_group_id}, contractor={self.contractor_id}, tech={self.technician_id}, status={self.status})>"
