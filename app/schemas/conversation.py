"""
Sanaie Platform — Chat Schemas
Pydantic models for conversation and message endpoints.
"""
from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime, timezone


# ── Message Schemas ──

class MessageCreate(BaseModel):
    content: Optional[str] = Field(None, max_length=2000)
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_type: Optional[str] = None


class MessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    sender_id: str
    sender_name: Optional[str] = None
    content: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_type: Optional[str] = None
    is_read: bool = False
    created_at: datetime

    @field_serializer('created_at')
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    model_config = {"from_attributes": True}


# ── Conversation Schemas ──

class ConversationCreate(BaseModel):
    participant_id: str = Field(..., description="The other user to start a conversation with")
    job_id: Optional[str] = Field(None, description="Optional job to link the conversation to")
    initial_message: Optional[str] = Field(None, description="Optional first message to send")


class ConversationParticipant(BaseModel):
    user_id: str
    name: str
    role: Optional[str] = None
    profile_image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    conversation_id: str
    other_participant: ConversationParticipant
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    last_message_text: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    created_at: datetime

    @field_serializer('created_at', 'last_message_at')
    def serialize_dt(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    conversation_id: str
    other_participant: ConversationParticipant
