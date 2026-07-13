"""
Sanaie Platform — Notifications API Router
Real alerts for bid updates, job status changes, system messages.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    SendNotification,
)

router = APIRouter()


# ═══════════════════════════════════════════
# Helper — create notification (used internally)
# ═══════════════════════════════════════════

def create_notification(
    db: Session,
    user_id: str,
    notif_type: str,
    title: str,
    message: str = None,
    reference_id: str = None,
    reference_type: str = None,
) -> Notification:
    """Create and persist a notification. Can be called from any service."""
    notif = Notification(
        notification_id=str(uuid.uuid4()),
        user_id=user_id,
        notif_type=notif_type,
        title=title,
        message=message,
        reference_id=reference_id,
        reference_type=reference_type,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notif)
    return notif


# ═══════════════════════════════════════════
# List Notifications
# ═══════════════════════════════════════════

@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="List my notifications",
)
def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all notifications for the current user, newest first."""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
    )

    if unread_only:
        query = query.filter(Notification.is_read == False)

    total = query.count()
    unread_count = db.query(func.count(Notification.notification_id)).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,
    ).scalar() or 0

    notifs = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                notification_id=n.notification_id,
                user_id=n.user_id,
                notif_type=n.notif_type,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                reference_id=n.reference_id,
                reference_type=n.reference_type,
                created_at=n.created_at,
            )
            for n in notifs
        ],
        total=total,
        unread_count=unread_count,
    )


# ═══════════════════════════════════════════
# Mark as Read
# ═══════════════════════════════════════════

@router.put(
    "/{notification_id}/read",
    summary="Mark a notification as read",
)
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id,
    ).first()

    if not notif:
        raise HTTPException(404, "Notification not found")

    notif.is_read = True
    db.commit()
    return {"status": "ok"}


@router.put(
    "/read-all",
    summary="Mark all notifications as read",
)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications for the current user as read."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"marked_read": count}


# ═══════════════════════════════════════════
# Send Notification (admin / internal)
# ═══════════════════════════════════════════

@router.post(
    "/",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a notification (for testing)",
)
def send_notification(
    data: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a notification for the current user (useful for testing)."""
    notif = create_notification(
        db,
        user_id=current_user.user_id,
        notif_type=data.notif_type,
        title=data.title,
        message=data.message,
        reference_id=data.reference_id,
        reference_type=data.reference_type,
    )
    db.commit()
    db.refresh(notif)

    return NotificationResponse(
        notification_id=notif.notification_id,
        user_id=notif.user_id,
        notif_type=notif.notif_type,
        title=notif.title,
        message=notif.message,
        is_read=notif.is_read,
        reference_id=notif.reference_id,
        reference_type=notif.reference_type,
        created_at=notif.created_at,
    )


# ═══════════════════════════════════════════
# Send Notification to Another User
# ═══════════════════════════════════════════

@router.post(
    "/send",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a notification to another user",
)
def send_notification_to_user(
    data: SendNotification,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a notification to a specific user (e.g. technician notifies client
    of job status updates). The target user must exist.
    """
    # Verify target user exists
    target = db.query(User).filter(User.user_id == data.target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    notif = create_notification(
        db,
        user_id=data.target_user_id,
        notif_type=data.notification_type,
        title=data.title,
        message=data.message,
        reference_id=data.reference_id,
        reference_type="job",
    )
    db.commit()
    db.refresh(notif)

    return NotificationResponse(
        notification_id=notif.notification_id,
        user_id=notif.user_id,
        notif_type=notif.notif_type,
        title=notif.title,
        message=notif.message,
        is_read=notif.is_read,
        reference_id=notif.reference_id,
        reference_type=notif.reference_type,
        created_at=notif.created_at,
    )
