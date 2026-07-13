from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Enum as SAEnum, Numeric, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base
from app.enums import BidStatus


class Bid(Base):
    __tablename__ = "bids"

    bid_id = Column(String(36), primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    amount = Column(Numeric(10, 2), nullable=False)  # Decimal for money
    counter_amount = Column(Numeric(10, 2), nullable=True)  # Client's counter-offer amount
    message = Column(Text, nullable=True)  # Worker's message/proposal to client
    status = Column(String(20), nullable=False, default="pending")

    # Timestamps
    scheduled_at = Column(DateTime, nullable=True)  # When technician plans to arrive
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    job = relationship("Job", back_populates="bids")
    worker = relationship("User", back_populates="bids")

    def __repr__(self):
        return f"<Bid(bid_id={self.bid_id}, amount={self.amount}, status={self.status})>"
