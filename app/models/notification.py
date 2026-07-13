"""
Sanaie Platform — Notification Model
Stores real notifications (bid updates, job status, system alerts).
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from datetime import datetime, timezone

from app.core.database import Base


class Notification(Base):
    """A notification for a user (bid received, job assigned, system alert, etc.)."""
    __tablename__ = "notifications"

    notification_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Notification content
    notif_type = Column(String(50), nullable=False, default="system")
    # Types: bid_received, bid_accepted, bid_rejected, job_assigned,
    #        job_completed, job_canceled, message, system, welcome
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)

    # Optional references for deep-linking
    reference_id = Column(String(36), nullable=True)   # job_id, bid_id, conversation_id…
    reference_type = Column(String(50), nullable=True)  # "job", "bid", "conversation"

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Notification({self.notification_id}, type={self.notif_type}, user={self.user_id})>"
