"""
Sanaie Platform — Conversation & Message Models
Stores real-time chat between clients and technicians.
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Conversation(Base):
    """A chat thread between two users, optionally linked to a job."""
    __tablename__ = "conversations"

    conversation_id = Column(String(36), primary_key=True, index=True)
    participant_1_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    participant_2_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.job_id"), nullable=True, index=True)

    # Cached last message for list display
    last_message_text = Column(String(500), nullable=True)
    last_message_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    participant_1 = relationship("User", foreign_keys=[participant_1_id])
    participant_2 = relationship("User", foreign_keys=[participant_2_id])
    job = relationship("Job", foreign_keys=[job_id])
    messages = relationship("Message", back_populates="conversation",
                            order_by="Message.created_at", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation({self.conversation_id}, {self.participant_1_id} <-> {self.participant_2_id})>"


class Message(Base):
    """A single message within a conversation."""
    __tablename__ = "messages"

    message_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, index=True)
    content = Column(Text, nullable=True)  # Text content (nullable if attachment-only)

    # Attachment support
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    attachment_type = Column(String(50), nullable=True)  # e.g. "PDF Document", "Image"

    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<Message({self.message_id}, from={self.sender_id})>"
