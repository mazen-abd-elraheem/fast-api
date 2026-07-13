from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating_score >= 1 AND rating_score <= 5", name="ck_rating_range"),
    )

    review_id = Column(String(36), primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    client_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    rating_score = Column(Integer, nullable=False)  # 1–5
    comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    job = relationship("Job", back_populates="reviews")
    client = relationship("User", foreign_keys=[client_id], back_populates="reviews_given")
    worker = relationship("User", foreign_keys=[worker_id], back_populates="reviews_received")

    def __repr__(self):
        return f"<Review(review_id={self.review_id}, rating={self.rating_score})>"
