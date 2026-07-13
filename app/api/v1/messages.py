"""
Sanaie Platform — Messages API Router
Real chat between clients and technicians.
All messages are persisted in MySQL.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.job import Job
from app.models.conversation import Conversation, Message
from app.services.asset_service import AssetService
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    ConversationParticipant,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)

router = APIRouter()


# ═══════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════

def _other_participant(conv: Conversation, current_user_id: str) -> User:
    """Return the other user in a conversation."""
    if conv.participant_1_id == current_user_id:
        return conv.participant_2
    return conv.participant_1


def _conv_response(conv: Conversation, current_user: User, db: Session) -> ConversationResponse:
    """Build a ConversationResponse with unread count."""
    other = _other_participant(conv, current_user.user_id)

    # Count unread messages (sent by the other person, not yet read)
    unread = db.query(func.count(Message.message_id)).filter(
        Message.conversation_id == conv.conversation_id,
        Message.sender_id != current_user.user_id,
        Message.is_read == False,
    ).scalar() or 0

    # Get job title if linked
    job_title = None
    if conv.job_id and conv.job:
        job_title = conv.job.title

    role_value = other.role.value if hasattr(other.role, "value") else other.role

    return ConversationResponse(
        conversation_id=conv.conversation_id,
        other_participant=ConversationParticipant(
            user_id=other.user_id,
            name=other.name,
            role=role_value,
            profile_image_url=other.profile_image_url,
        ),
        job_id=conv.job_id,
        job_title=job_title,
        last_message_text=conv.last_message_text,
        last_message_at=conv.last_message_at,
        unread_count=unread,
        created_at=conv.created_at,
    )


# ═══════════════════════════════════════════
# List Conversations
# ═══════════════════════════════════════════

@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List my conversations",
)
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all conversations the current user participates in, newest first."""
    query = db.query(Conversation).filter(
        or_(
            Conversation.participant_1_id == current_user.user_id,
            Conversation.participant_2_id == current_user.user_id,
        )
    ).order_by(
        # MySQL doesn't support NULLS LAST — use CASE to push NULLs to the end
        func.coalesce(Conversation.last_message_at, '1970-01-01').desc(),
    )

    total = query.count()
    convs = query.offset(skip).limit(limit).all()

    return ConversationListResponse(
        conversations=[_conv_response(c, current_user, db) for c in convs],
        total=total,
    )


# ═══════════════════════════════════════════
# Create / Get Conversation
# ═══════════════════════════════════════════

@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a conversation with another user.
    If a conversation between the two users (optionally for the same job) already exists,
    return the existing one instead of creating a duplicate.
    """
    if data.participant_id == current_user.user_id:
        raise HTTPException(400, "Cannot start a conversation with yourself")

    # Check participant exists
    other = db.query(User).filter(User.user_id == data.participant_id).first()
    if not other:
        raise HTTPException(404, "User not found")

    # Check for existing conversation between these two users
    existing = db.query(Conversation).filter(
        or_(
            and_(
                Conversation.participant_1_id == current_user.user_id,
                Conversation.participant_2_id == data.participant_id,
            ),
            and_(
                Conversation.participant_1_id == data.participant_id,
                Conversation.participant_2_id == current_user.user_id,
            ),
        )
    )

    # If job_id is specified, narrow to that job
    if data.job_id:
        existing = existing.filter(Conversation.job_id == data.job_id)

    existing_conv = existing.first()
    if existing_conv:
        # Send initial message if provided
        if data.initial_message:
            _create_message(db, existing_conv, current_user.user_id, data.initial_message)
        return _conv_response(existing_conv, current_user, db)

    # Create new conversation
    conv = Conversation(
        conversation_id=str(uuid.uuid4()),
        participant_1_id=current_user.user_id,
        participant_2_id=data.participant_id,
        job_id=data.job_id,
    )
    db.add(conv)
    db.flush()

    # Send initial message if provided
    if data.initial_message:
        _create_message(db, conv, current_user.user_id, data.initial_message)

    db.commit()
    db.refresh(conv)

    return _conv_response(conv, current_user, db)


# ═══════════════════════════════════════════
# Get Messages
# ═══════════════════════════════════════════

@router.get(
    "/conversations/{conversation_id}",
    response_model=MessageListResponse,
    summary="Get messages in a conversation",
)
def get_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve all messages in a conversation.
    Also marks unread messages from the other participant as read.
    """
    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(404, "Conversation not found")

    # Verify the current user is a participant
    if current_user.user_id not in (conv.participant_1_id, conv.participant_2_id):
        raise HTTPException(403, "You are not part of this conversation")

    # Mark all unread messages from the OTHER person as read
    db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.sender_id != current_user.user_id,
        Message.is_read == False,
    ).update({"is_read": True})
    db.commit()

    # Fetch messages (oldest first for chat display)
    query = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at)

    total = query.count()
    msgs = query.offset(skip).limit(limit).all()

    other = _other_participant(conv, current_user.user_id)
    role_value = other.role.value if hasattr(other.role, "value") else other.role

    return MessageListResponse(
        messages=[
            MessageResponse(
                message_id=m.message_id,
                conversation_id=m.conversation_id,
                sender_id=m.sender_id,
                sender_name=m.sender.name if m.sender else None,
                content=m.content,
                attachment_url=m.attachment_url,
                attachment_name=m.attachment_name,
                attachment_type=m.attachment_type,
                is_read=m.is_read,
                created_at=m.created_at,
            )
            for m in msgs
        ],
        total=total,
        conversation_id=conversation_id,
        other_participant=ConversationParticipant(
            user_id=other.user_id,
            name=other.name,
            role=role_value,
            profile_image_url=other.profile_image_url,
        ),
    )


# ═══════════════════════════════════════════
# Send Message
# ═══════════════════════════════════════════

def _create_message(
    db: Session,
    conv: Conversation,
    sender_id: str,
    content: str = None,
    attachment_url: str = None,
    attachment_name: str = None,
    attachment_type: str = None,
) -> Message:
    """Internal: create a message and update conversation's last_message."""
    now = datetime.now(timezone.utc)
    msg = Message(
        message_id=str(uuid.uuid4()),
        conversation_id=conv.conversation_id,
        sender_id=sender_id,
        content=content,
        attachment_url=attachment_url,
        attachment_name=attachment_name,
        attachment_type=attachment_type,
        is_read=False,
        created_at=now,
    )
    db.add(msg)

    # Update conversation cache
    conv.last_message_text = (content or attachment_name or "Attachment")[:500]
    conv.last_message_at = now
    conv.updated_at = now

    return msg


@router.post(
    "/conversations/{conversation_id}/send",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
)
def send_message(
    conversation_id: str,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a text message or attachment in a conversation."""
    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(404, "Conversation not found")

    if current_user.user_id not in (conv.participant_1_id, conv.participant_2_id):
        raise HTTPException(403, "You are not part of this conversation")

    if not data.content and not data.attachment_url:
        raise HTTPException(400, "Message must have content or an attachment")

    msg = _create_message(
        db, conv, current_user.user_id,
        content=data.content,
        attachment_url=data.attachment_url,
        attachment_name=data.attachment_name,
        attachment_type=data.attachment_type,
    )
    db.commit()
    db.refresh(msg)

    return MessageResponse(
        message_id=msg.message_id,
        conversation_id=msg.conversation_id,
        sender_id=msg.sender_id,
        sender_name=current_user.name,
        content=msg.content,
        attachment_url=msg.attachment_url,
        attachment_name=msg.attachment_name,
        attachment_type=msg.attachment_type,
        is_read=msg.is_read,
        created_at=msg.created_at,
    )


# ═══════════════════════════════════════════
# Mark Messages as Read
# ═══════════════════════════════════════════

@router.put(
    "/conversations/{conversation_id}/read",
    summary="Mark all messages in a conversation as read",
)
def mark_read(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all messages from the other user as read."""
    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(404, "Conversation not found")

    if current_user.user_id not in (conv.participant_1_id, conv.participant_2_id):
        raise HTTPException(403, "You are not part of this conversation")

    updated = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.sender_id != current_user.user_id,
        Message.is_read == False,
    ).update({"is_read": True})
    db.commit()

    return {"marked_read": updated}


# ═══════════════════════════════════════════
# Delete Conversation(s)
# ═══════════════════════════════════════════

@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete a conversation",
)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and all its messages (only participants can delete)."""
    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(404, "Conversation not found")

    if current_user.user_id not in (conv.participant_1_id, conv.participant_2_id):
        raise HTTPException(403, "You are not part of this conversation")

    db.delete(conv)  # CASCADE deletes all messages
    db.commit()

    return {"status": "deleted", "conversation_id": conversation_id}


@router.post(
    "/conversations/batch-delete",
    summary="Delete multiple conversations",
)
def batch_delete_conversations(
    conversation_ids: list[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete multiple conversations at once. Only conversations the user participates in will be deleted."""
    deleted = []
    for cid in conversation_ids:
        conv = db.query(Conversation).filter(
            Conversation.conversation_id == cid,
            or_(
                Conversation.participant_1_id == current_user.user_id,
                Conversation.participant_2_id == current_user.user_id,
            ),
        ).first()
        if conv:
            db.delete(conv)
            deleted.append(cid)

    db.commit()
    return {"deleted": deleted, "count": len(deleted)}


# ═══════════════════════════════════════════
# Delete Individual Message
# ═══════════════════════════════════════════

@router.delete(
    "/messages/{message_id}",
    summary="Delete a single message",
)
def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a single message. Only the sender can delete their own messages."""
    msg = db.query(Message).filter(Message.message_id == message_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")
    if msg.sender_id != current_user.user_id:
        raise HTTPException(403, "You can only delete your own messages")

    db.delete(msg)
    db.commit()
    return {"status": "deleted", "message_id": message_id}


# ═══════════════════════════════════════════
# Upload Chat Attachment
# ═══════════════════════════════════════════

@router.post(
    "/upload-attachment",
    summary="Upload a chat attachment (image, document)",
)
async def upload_chat_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file to be sent as a chat attachment.
    Returns the URL, filename, and detected type so the client
    can pass them to the send_message endpoint.
    """
    if not file or not file.filename:
        raise HTTPException(400, "No file provided")

    # Detect attachment type from extension
    filename = file.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    type_map = {
        "jpg": "Image", "jpeg": "Image", "png": "Image",
        "gif": "Image", "webp": "Image",
        "mp4": "Video", "mov": "Video",
        "pdf": "PDF Document",
    }
    attachment_type = type_map.get(ext, "File")

    url = await AssetService.save_upload(file, subfolder="chat")
    if not url:
        raise HTTPException(400, "File upload failed — unsupported type or too large (max 10MB)")

    return {
        "attachment_url": url,
        "attachment_name": filename,
        "attachment_type": attachment_type,
    }
