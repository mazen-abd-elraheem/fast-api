"""
Sanaie Platform — Admin API Routes
Admin-only endpoints for:
  - User management (list, change roles, create admins/editors/moderators)
  - Certification review (approve/reject)
  - Support ticket overview
  - Platform statistics
  - Job management
  - Audit logging
  - Staff management
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.core.database import get_db
from app.api.deps import get_current_user, require_role, handle_service_exception
from app.models.user import User
from app.models.job import Job
from app.models.certification import Certification
from app.models.review import Review
from app.models.admin_audit_log import AdminAuditLog
from app.enums import UserRole
from app.schemas.user import UserCreate, UserResponse, AdminUserUpdate, AdminCreateStaff
from app.schemas.certification import CertificationCreate, CertificationUpdate, CertificationResponse
from app.services.user_service import UserService
from app.core.security import hash_password
from app.core.exceptions import SanaieException
from datetime import datetime, timezone

router = APIRouter()

# Staff roles that can access admin endpoints
STAFF_ROLES = [UserRole.ADMIN, UserRole.EDITOR, UserRole.MODERATOR]
EDITOR_ROLES = [UserRole.ADMIN, UserRole.EDITOR]


def _log_action(db: Session, admin: User, action: str, target_type: str = None,
                target_id: str = None, target_name: str = None,
                description: str = None, details: dict = None,
                severity: str = "info"):
    """Record an admin action in the audit log."""
    log = AdminAuditLog(
        log_id=str(uuid.uuid4()),
        admin_id=admin.user_id,
        admin_name=admin.name,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        description=description,
        details=details,
        severity=severity,
    )
    db.add(log)


# ==========================================
# Admin: Edit Any User Profile
# ==========================================
@router.get(
    "/users/{user_id}",
    summary="Get full user details (admin only)",
)
def admin_get_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get complete user profile for admin editing."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": user.role,
        "latitude": user.latitude,
        "longitude": user.longitude,
        "skills": user.skills or [],
        "profile_image_url": user.profile_image_url,
        "is_available": user.is_available,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


@router.put(
    "/users/{user_id}",
    summary="Update any user profile (admin/editor)",
)
def admin_update_user(
    user_id: str,
    update_data: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Admin/Editor can update name, phone, email, role, location, password, skills, availability."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = []

    if update_data.name is not None:
        user.name = update_data.name
        changes.append("name")
    if update_data.phone_number is not None:
        user.phone_number = update_data.phone_number if update_data.phone_number else None
        changes.append("phone_number")
    if update_data.email is not None:
        existing = db.query(User).filter(User.email == update_data.email, User.user_id != user_id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use by another user")
        user.email = update_data.email
        changes.append("email")
    if update_data.role is not None:
        if user_id == admin.user_id:
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        # Only full admins can assign admin/editor/moderator roles
        admin_role = admin.role.value if hasattr(admin.role, 'value') else admin.role
        if update_data.role in ('admin', 'editor', 'moderator') and admin_role != 'admin':
            raise HTTPException(status_code=403, detail="Only admins can assign staff roles")
        user.role = update_data.role
        changes.append("role")
    if update_data.latitude is not None:
        user.latitude = update_data.latitude
        changes.append("latitude")
    if update_data.longitude is not None:
        user.longitude = update_data.longitude
        changes.append("longitude")
    if update_data.new_password is not None:
        user.password_hash = hash_password(update_data.new_password)
        changes.append("password")
    if update_data.skills is not None:
        user.skills = update_data.skills
        changes.append("skills")
    if update_data.is_available is not None:
        user.is_available = update_data.is_available
        changes.append("is_available")

    _log_action(db, admin, "user_updated", "user", user_id, user.name,
                f"Updated: {', '.join(changes)}", {"changes": changes})
    db.commit()
    db.refresh(user)

    return {
        "message": f"User '{user.name}' updated ({', '.join(changes)})",
        "user_id": user_id,
        "changes": changes,
    }


# ==========================================
# Platform Statistics
# ==========================================
@router.get(
    "/stats",
    summary="Get platform statistics (admin only)",
)
def get_platform_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Overview statistics for the admin dashboard."""
    total_users = db.query(func.count(User.user_id)).scalar() or 0
    total_clients = db.query(func.count(User.user_id)).filter(User.role == "client").scalar() or 0
    total_workers = db.query(func.count(User.user_id)).filter(User.role == "worker").scalar() or 0
    total_admins = db.query(func.count(User.user_id)).filter(User.role == "admin").scalar() or 0
    total_jobs = db.query(func.count(Job.job_id)).scalar() or 0
    completed_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "completed").scalar() or 0
    open_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "open").scalar() or 0
    pending_certs = db.query(func.count(Certification.cert_id)).filter(
        Certification.status == "pending").scalar() or 0
    verified_certs = db.query(func.count(Certification.cert_id)).filter(
        Certification.status == "verified").scalar() or 0

    return {
        "total_users": total_users,
        "total_clients": total_clients,
        "total_workers": total_workers,
        "total_admins": total_admins,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "open_jobs": open_jobs,
        "pending_certs": pending_certs,
        "verified_certs": verified_certs,
    }


# ==========================================
# User Management
# ==========================================
@router.get(
    "/users",
    summary="List all users (admin only)",
)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all platform users with optional role/name filter."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "users": [
            {
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "phone_number": u.phone_number,
                "is_available": u.is_available,
                "is_verified": u.is_verified,
                "latitude": u.latitude,
                "longitude": u.longitude,
                "profile_image_url": u.profile_image_url,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
    }


@router.put(
    "/users/{user_id}/role",
    summary="Change user role (admin only)",
)
def change_user_role(
    user_id: str,
    new_role: str = Query(..., pattern=r'^(client|worker|admin)$'),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Change a user's role. Cannot demote yourself."""
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role
    user.role = new_role
    db.commit()

    return {
        "message": f"Role changed from {old_role} to {new_role}",
        "user_id": user_id,
        "new_role": new_role,
    }


@router.post(
    "/users/create-admin",
    summary="Create a new admin user",
)
def create_admin_user(
    name: str = Query(..., min_length=2),
    email: str = Query(...),
    password: str = Query(..., min_length=8),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new admin user directly."""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    new_admin = User(
        user_id=str(uuid.uuid4()),
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return {
        "message": f"Admin '{name}' created",
        "user_id": new_admin.user_id,
        "email": email,
        "role": "admin",
    }


@router.delete(
    "/users/{user_id}",
    summary="Delete a user (admin only)",
)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a user from the platform."""
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": f"User '{user.name}' deleted"}


# ==========================================
# Certification Management
# ==========================================
@router.get(
    "/certifications",
    summary="List all certifications (admin only)",
)
def list_certifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None, pattern=r'^(pending|verified|rejected)$'),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List certifications, optionally filtered by status."""
    query = db.query(Certification)
    if status:
        query = query.filter(Certification.status == status)
    total = query.count()
    certs = query.order_by(Certification.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for c in certs:
        worker = db.query(User.name).filter(User.user_id == c.worker_id).first()
        result.append({
            "cert_id": c.cert_id,
            "worker_id": c.worker_id,
            "worker_name": worker.name if worker else "Unknown",
            "name": c.name,
            "category": c.category,
            "status": c.status,
            "file_url": c.file_url,
            "rejection_reason": c.rejection_reason,
            "reviewed_by": c.reviewed_by,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    return {"certifications": result, "total": total}


@router.put(
    "/certifications/{cert_id}/approve",
    summary="Approve a certification (admin only)",
)
def approve_certification(
    cert_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Mark a certification as verified."""
    cert = db.query(Certification).filter(Certification.cert_id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert.status = "verified"
    cert.reviewed_by = admin.user_id
    cert.rejection_reason = None
    db.commit()

    return {"message": f"Certification '{cert.name}' approved", "cert_id": cert_id, "status": "verified"}


@router.put(
    "/certifications/{cert_id}/reject",
    summary="Reject a certification (admin only)",
)
def reject_certification(
    cert_id: str,
    reason: str = Query("Did not meet requirements"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Reject a certification with a reason."""
    cert = db.query(Certification).filter(Certification.cert_id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert.status = "rejected"
    cert.reviewed_by = admin.user_id
    cert.rejection_reason = reason
    db.commit()

    return {"message": f"Certification '{cert.name}' rejected", "cert_id": cert_id, "status": "rejected"}


# ==========================================
# Worker Certifications (non-admin — for technicians)
# ==========================================
@router.get(
    "/my-certifications",
    summary="Get my certifications (worker)",
)
def get_my_certifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all certifications for the current worker."""
    certs = (
        db.query(Certification)
        .filter(Certification.worker_id == current_user.user_id)
        .order_by(Certification.created_at.desc())
        .all()
    )
    return {
        "certifications": [
            {
                "cert_id": c.cert_id,
                "worker_id": c.worker_id,
                "name": c.name,
                "category": c.category,
                "status": c.status,
                "file_url": c.file_url,
                "rejection_reason": c.rejection_reason,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in certs
        ]
    }


@router.post(
    "/my-certifications",
    summary="Submit a new certification (worker)",
)
def submit_certification(
    cert_data: CertificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new certification for admin review."""
    cert = Certification(
        cert_id=str(uuid.uuid4()),
        worker_id=current_user.user_id,
        name=cert_data.name,
        category=cert_data.category,
        status="pending",
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    return {
        "message": f"Certification '{cert.name}' submitted for review",
        "cert_id": cert.cert_id,
        "status": "pending",
    }


@router.delete(
    "/my-certifications/{cert_id}",
    summary="Delete my certification (worker)",
)
def delete_my_certification(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one of your certifications."""
    cert = db.query(Certification).filter(
        Certification.cert_id == cert_id,
        Certification.worker_id == current_user.user_id,
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    db.delete(cert)
    db.commit()
    return {"message": f"Certification '{cert.name}' deleted"}


# ==========================================
# Worker's certifications (public - for client view)
# ==========================================
@router.get(
    "/worker/{worker_id}/certifications",
    summary="Get a worker's verified certifications",
)
def get_worker_certifications(
    worker_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get verified certifications for a worker (client view)."""
    certs = (
        db.query(Certification)
        .filter(
            Certification.worker_id == worker_id,
            Certification.status.in_(["verified", "pending"]),
        )
        .order_by(Certification.created_at.desc())
        .all()
    )
    return {
        "certifications": [
            {
                "cert_id": c.cert_id,
                "name": c.name,
                "category": c.category,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in certs
        ]
    }


# ==========================================
# Bids Monitoring (Admin)
# ==========================================
@router.get(
    "/bids",
    summary="List all bids (admin only)",
)
def admin_list_bids(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all marketplace bids with technician and client info."""
    from app.models.bid import Bid

    query = db.query(Bid)
    if status:
        query = query.filter(Bid.status == status)
    total = query.count()
    bids = query.order_by(Bid.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for b in bids:
        worker = db.query(User.name).filter(User.user_id == b.worker_id).first()
        job = db.query(Job).filter(Job.job_id == b.job_id).first()
        client_name = None
        if job:
            client = db.query(User.name).filter(User.user_id == job.client_id).first()
            client_name = client.name if client else None

        result.append({
            "bid_id": b.bid_id,
            "job_id": b.job_id,
            "job_title": job.title if job else "Unknown Job",
            "worker_id": b.worker_id,
            "worker_name": worker.name if worker else "Unknown",
            "client_name": client_name or "Unknown",
            "amount": float(b.amount) if b.amount else 0,
            "status": b.status,
            "message": b.message,
            "scheduled_at": b.scheduled_at.isoformat() if b.scheduled_at else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })

    return {"bids": result, "total": total}


@router.delete(
    "/bids/{bid_id}",
    summary="Delete a bid with reason (admin only)",
)
def admin_delete_bid(
    bid_id: str,
    reason: str = Query("Removed by admin"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete a bid and notify both the client and technician with the reason.
    Creates a notification for each party explaining why the bid was removed.
    """
    from app.models.bid import Bid
    from app.api.v1.notifications import create_notification

    bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    # Get related info before deleting
    job = db.query(Job).filter(Job.job_id == bid.job_id).first()
    worker = db.query(User).filter(User.user_id == bid.worker_id).first()
    job_title = job.title if job else "Unknown Job"
    worker_name = worker.name if worker else "Unknown"
    client_id = job.client_id if job else None

    # Notify the technician (bid owner)
    create_notification(
        db,
        user_id=bid.worker_id,
        notif_type="bid_removed",
        title="Your bid has been removed",
        message=f"Your bid of {float(bid.amount):,.0f} EGP on \"{job_title}\" was removed by an administrator. Reason: {reason}",
        reference_id=bid.job_id,
        reference_type="job",
    )

    # Notify the client (job owner)
    if client_id:
        create_notification(
            db,
            user_id=client_id,
            notif_type="bid_removed",
            title="A bid on your job was removed",
            message=f"A bid from {worker_name} on \"{job_title}\" was removed by an administrator. Reason: {reason}",
            reference_id=bid.job_id,
            reference_type="job",
        )

    # Delete the bid
    db.delete(bid)
    db.commit()

    return {
        "message": f"Bid deleted and notifications sent",
        "bid_id": bid_id,
        "reason": reason,
    }


# ==========================================
# Chat Monitoring (Admin)
# ==========================================
@router.get(
    "/chats",
    summary="List all chat threads (admin only)",
)
def admin_list_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all active chat conversations for admin monitoring."""
    from app.models.conversation import Conversation, Message

    query = db.query(Conversation).order_by(Conversation.updated_at.desc())
    total = query.count()
    convos = query.offset(skip).limit(limit).all()

    result = []
    for c in convos:
        p1 = db.query(User).filter(User.user_id == c.participant_1_id).first()
        p2 = db.query(User).filter(User.user_id == c.participant_2_id).first()
        msg_count = db.query(func.count(Message.message_id)).filter(
            Message.conversation_id == c.conversation_id).scalar() or 0

        result.append({
            "conversation_id": c.conversation_id,
            "participant_1": {"user_id": c.participant_1_id, "name": p1.name if p1 else "Unknown", "role": p1.role if p1 else ""},
            "participant_2": {"user_id": c.participant_2_id, "name": p2.name if p2 else "Unknown", "role": p2.role if p2 else ""},
            "job_id": c.job_id,
            "last_message": c.last_message_text,
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            "message_count": msg_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"chats": result, "total": total}


@router.get(
    "/chats/{conversation_id}/messages",
    summary="View chat messages (admin only)",
)
def admin_get_chat_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """View all messages in a conversation thread."""
    from app.models.conversation import Message

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(skip).limit(limit).all()
    )

    result = []
    for m in msgs:
        sender = db.query(User).filter(User.user_id == m.sender_id).first()
        result.append({
            "message_id": m.message_id,
            "sender_id": m.sender_id,
            "sender_name": sender.name if sender else "Unknown",
            "sender_role": sender.role if sender else "",
            "content": m.content,
            "attachment_url": m.attachment_url,
            "is_read": m.is_read,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    return {"messages": result, "total": len(result)}


@router.delete(
    "/chats/{conversation_id}",
    summary="Delete a conversation with reason (admin only)",
)
def admin_delete_conversation(
    conversation_id: str,
    reason: str = Query("Removed by admin"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete a conversation and all its messages.
    Sends notifications to both participants explaining the removal.
    """
    from app.models.conversation import Conversation, Message
    from app.api.v1.notifications import create_notification

    conv = db.query(Conversation).filter(
        Conversation.conversation_id == conversation_id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    p1 = db.query(User).filter(User.user_id == conv.participant_1_id).first()
    p2 = db.query(User).filter(User.user_id == conv.participant_2_id).first()
    p1_name = p1.name if p1 else "Unknown"
    p2_name = p2.name if p2 else "Unknown"

    # Notify participant 1
    create_notification(
        db,
        user_id=conv.participant_1_id,
        notif_type="conversation_deleted",
        title="Conversation removed by admin",
        message=f"Your conversation with {p2_name} has been removed by an administrator. Reason: {reason}",
        reference_id=conversation_id,
        reference_type="conversation",
    )

    # Notify participant 2
    create_notification(
        db,
        user_id=conv.participant_2_id,
        notif_type="conversation_deleted",
        title="Conversation removed by admin",
        message=f"Your conversation with {p1_name} has been removed by an administrator. Reason: {reason}",
        reference_id=conversation_id,
        reference_type="conversation",
    )

    # Delete all messages then the conversation
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conv)
    db.commit()

    return {
        "message": f"Conversation between {p1_name} and {p2_name} deleted",
        "conversation_id": conversation_id,
        "reason": reason,
    }


@router.delete(
    "/chats/{conversation_id}/messages/{message_id}",
    summary="Delete a single message (admin/editor)",
)
def admin_delete_message(
    conversation_id: str,
    message_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Delete a single message from a conversation."""
    from app.models.conversation import Message

    msg = db.query(Message).filter(
        Message.message_id == message_id,
        Message.conversation_id == conversation_id
    ).first()
    
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    content = msg.content
    db.delete(msg)
    _log_action(db, admin, "message_deleted", "chat", message_id, content,
                f"Deleted message in conv {conversation_id}: {content[:50]}...",
                {"conversation_id": conversation_id, "content": content}, severity="warning")
    db.commit()

    return {"message": "Message deleted", "message_id": message_id}

@router.put(
    "/users/{user_id}/ban",
    summary="Ban a user (admin only)",
)
def admin_ban_user(
    user_id: str,
    reason: str = Query("Banned by admin"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Ban a user — sets is_available to 'banned' and notifies them."""
    from app.api.v1.notifications import create_notification

    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_available == "banned":
        raise HTTPException(status_code=400, detail="User is already banned")

    user.is_available = "banned"

    create_notification(
        db,
        user_id=user_id,
        notif_type="account_banned",
        title="Your account has been banned",
        message=f"Your account has been banned by an administrator. Reason: {reason}",
    )
    _log_action(db, admin, "user_banned", "user", user_id, user.name,
                f"Banned user '{user.name}'. Reason: {reason}",
                {"reason": reason}, severity="critical")
    db.commit()

    return {
        "message": f"User '{user.name}' has been banned",
        "user_id": user_id,
        "reason": reason,
    }


@router.put(
    "/users/{user_id}/unban",
    summary="Unban a user (admin only)",
)
def admin_unban_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Unban a user — restores is_available to 'available'."""
    from app.api.v1.notifications import create_notification

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_available != "banned":
        raise HTTPException(status_code=400, detail="User is not banned")

    user.is_available = "available"

    create_notification(
        db,
        user_id=user_id,
        notif_type="account_unbanned",
        title="Your account has been unbanned",
        message="Your account has been restored by an administrator. You can now use the platform again.",
    )
    db.commit()

    return {
        "message": f"User '{user.name}' has been unbanned",
        "user_id": user_id,
    }


# ==========================================
# Reports & Complaints (Admin)
# ==========================================
@router.get(
    "/reports",
    summary="List all reports (admin only)",
)
def admin_list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List user-submitted problem reports."""
    from app.models.report import Report

    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    total = query.count()
    reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "reports": [
            {
                "report_id": r.report_id,
                "user_id": r.user_id,
                "user_name": r.user_name,
                "subject": r.subject,
                "description": r.description,
                "category": r.category,
                "status": r.status,
                "priority": r.priority,
                "assigned_to": r.assigned_to,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            }
            for r in reports
        ],
        "total": total,
    }


@router.put(
    "/reports/{report_id}/resolve",
    summary="Resolve a report (admin only)",
)
def admin_resolve_report(
    report_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Mark a report as resolved."""
    from app.models.report import Report

    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = "resolved"
    report.resolved_at = datetime.now(timezone.utc)
    report.assigned_to = admin.user_id
    db.commit()

    return {"message": f"Report '{report.subject}' resolved", "report_id": report_id}


# ==========================================
# Submit Report (any user)
# ==========================================
@router.post(
    "/reports/submit",
    summary="Submit a problem report",
)
def submit_report(
    subject: str = Query(..., min_length=3),
    description: str = Query(""),
    category: str = Query("general"),
    priority: str = Query("medium"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a problem report (any authenticated user)."""
    from app.models.report import Report

    report = Report(
        report_id=str(uuid.uuid4()),
        user_id=current_user.user_id,
        user_name=current_user.name,
        subject=subject,
        description=description,
        category=category,
        priority=priority,
        status="open",
    )
    db.add(report)
    db.commit()

    return {"message": "Report submitted", "report_id": report.report_id}


# ==========================================
# Technician Management (Admin)
# ==========================================
@router.get(
    "/technicians",
    summary="List technicians with details (admin only)",
)
def admin_list_technicians(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all technicians with ratings and certification counts."""
    query = db.query(User).filter(User.role == "worker")
    if status:
        query = query.filter(User.is_available == status)
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    total = query.count()
    techs = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for t in techs:
        # Get rating
        avg_rating = db.query(func.avg(Review.rating_score)).filter(
            Review.worker_id == t.user_id).scalar()
        review_count = db.query(func.count(Review.review_id)).filter(
            Review.worker_id == t.user_id).scalar() or 0
        cert_count = db.query(func.count(Certification.cert_id)).filter(
            Certification.worker_id == t.user_id).scalar() or 0
        pending_certs = db.query(func.count(Certification.cert_id)).filter(
            Certification.worker_id == t.user_id,
            Certification.status == "pending").scalar() or 0

        result.append({
            "user_id": t.user_id,
            "name": t.name,
            "email": t.email,
            "phone_number": t.phone_number,
            "skills": t.skills or [],
            "is_available": t.is_available,
            "avg_rating": round(float(avg_rating), 1) if avg_rating else None,
            "review_count": review_count,
            "cert_count": cert_count,
            "pending_certs": pending_certs,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {"technicians": result, "total": total}


@router.put(
    "/technicians/{user_id}/suspend",
    summary="Suspend a technician (admin only)",
)
def admin_suspend_technician(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Suspend a technician account."""
    user = db.query(User).filter(User.user_id == user_id, User.role == "worker").first()
    if not user:
        raise HTTPException(status_code=404, detail="Technician not found")

    user.is_available = "suspended"
    db.commit()
    return {"message": f"Technician '{user.name}' suspended", "user_id": user_id}


@router.put(
    "/technicians/{user_id}/reactivate",
    summary="Reactivate a technician (admin only)",
)
def admin_reactivate_technician(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Reactivate a suspended technician."""
    user = db.query(User).filter(User.user_id == user_id, User.role == "worker").first()
    if not user:
        raise HTTPException(status_code=404, detail="Technician not found")

    user.is_available = "available"
    db.commit()
    return {"message": f"Technician '{user.name}' reactivated", "user_id": user_id}


# ==========================================
# System Health (Admin)
# ==========================================
@router.get(
    "/health",
    summary="System health metrics (admin only)",
)
def admin_system_health(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get system health metrics for admin dashboard."""
    import platform
    import time

    # Database check
    db_healthy = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_healthy = False

    # Basic system info
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        mem_used_gb = round(memory.used / (1024**3), 1)
        mem_total_gb = round(memory.total / (1024**3), 1)
    except ImportError:
        cpu_percent = 0
        mem_percent = 0
        mem_used_gb = 0
        mem_total_gb = 0

    # Count stats
    total_users = db.query(func.count(User.user_id)).scalar() or 0
    total_jobs = db.query(func.count(Job.job_id)).scalar() or 0
    from app.models.bid import Bid
    total_bids = db.query(func.count(Bid.bid_id)).scalar() or 0

    return {
        "status": "operational" if db_healthy else "degraded",
        "database": "healthy" if db_healthy else "disconnected",
        "cpu_percent": cpu_percent,
        "memory_percent": mem_percent,
        "memory_used_gb": mem_used_gb,
        "memory_total_gb": mem_total_gb,
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "total_users": total_users,
        "total_jobs": total_jobs,
        "total_bids": total_bids,
        "app_version": "2.4.0",
    }


# ==========================================
# Activity Feed (Admin)
# ==========================================
@router.get(
    "/activity-feed",
    summary="Recent activity feed (admin only)",
)
def admin_activity_feed(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get recent platform activity for the admin dashboard."""
    from app.models.bid import Bid
    from app.models.notification import Notification

    activities = []

    # Recent users
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    for u in recent_users:
        activities.append({
            "type": "user_registered",
            "title": f"New {u.role} registered",
            "description": f"{u.name} joined the platform",
            "timestamp": u.created_at.isoformat() if u.created_at else None,
            "icon": "person_add",
        })

    # Recent jobs
    recent_jobs = db.query(Job).order_by(Job.created_at.desc()).limit(5).all()
    for j in recent_jobs:
        activities.append({
            "type": "job_created",
            "title": f"New job posted: {j.title}",
            "description": f"Category: {j.category or 'general'}",
            "timestamp": j.created_at.isoformat() if j.created_at else None,
            "icon": "work",
        })

    # Recent bids
    recent_bids = db.query(Bid).order_by(Bid.created_at.desc()).limit(5).all()
    for b in recent_bids:
        worker = db.query(User.name).filter(User.user_id == b.worker_id).first()
        activities.append({
            "type": "bid_submitted",
            "title": f"Bid submitted: {float(b.amount):.0f} EGP",
            "description": f"By {worker.name if worker else 'Unknown'}",
            "timestamp": b.created_at.isoformat() if b.created_at else None,
            "icon": "gavel",
        })

    # Sort by timestamp descending
    activities.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    return {"activities": activities[:limit]}


# ==========================================
# ID Verification Review (Admin)
# ==========================================
@router.get(
    "/verifications",
    summary="List ID verifications (admin only)",
)
def admin_list_verifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all ID verification requests for admin review."""
    from app.models.id_verification import IDVerification

    query = db.query(IDVerification)
    if status:
        query = query.filter(IDVerification.status == status)
    total = query.count()
    items = query.order_by(IDVerification.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for v in items:
        user = db.query(User).filter(User.user_id == v.user_id).first()
        result.append({
            "verification_id": v.verification_id,
            "user_id": v.user_id,
            "user_name": user.name if user else "Unknown",
            "user_role": user.role if user else "",
            "user_email": user.email if user else "",
            "profile_image_url": user.profile_image_url if user else None,
            "front_image_url": v.front_image_url,
            "back_image_url": v.back_image_url,
            "status": v.status,
            "rejection_reason": v.rejection_reason,
            "reviewed_by": v.reviewed_by,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        })

    return {"verifications": result, "total": total}


@router.put(
    "/verifications/{verification_id}/approve",
    summary="Approve ID verification (admin only)",
)
def admin_approve_verification(
    verification_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Approve an ID verification and mark the user as verified."""
    from app.models.id_verification import IDVerification
    from app.api.v1.notifications import create_notification

    v = db.query(IDVerification).filter(
        IDVerification.verification_id == verification_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")

    v.status = "approved"
    v.reviewed_by = admin.user_id
    v.rejection_reason = None

    user = db.query(User).filter(User.user_id == v.user_id).first()
    if user:
        user.is_verified = "verified"

    create_notification(
        db,
        user_id=v.user_id,
        notif_type="id_verified",
        title="Identity Verified ✓",
        message="Your ID has been verified. You now have a verified badge on your profile.",
    )
    db.commit()

    return {
        "message": f"ID verification approved for {user.name if user else 'user'}",
        "verification_id": verification_id,
        "status": "approved",
    }


@router.put(
    "/verifications/{verification_id}/reject",
    summary="Reject ID verification (admin only)",
)
def admin_reject_verification(
    verification_id: str,
    reason: str = Query("ID document could not be verified"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Reject an ID verification with a reason."""
    from app.models.id_verification import IDVerification
    from app.api.v1.notifications import create_notification

    v = db.query(IDVerification).filter(
        IDVerification.verification_id == verification_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")

    v.status = "rejected"
    v.reviewed_by = admin.user_id
    v.rejection_reason = reason

    user = db.query(User).filter(User.user_id == v.user_id).first()
    if user:
        user.is_verified = "rejected"

    create_notification(
        db,
        user_id=v.user_id,
        notif_type="id_rejected",
        title="ID Verification Rejected",
        message=f"Your ID verification was rejected. Reason: {reason}. You can re-submit with a clearer photo.",
    )
    db.commit()

    return {
        "message": f"ID verification rejected",
        "verification_id": verification_id,
        "status": "rejected",
        "reason": reason,
    }


# ==========================================
# Staff Management (Admin only)
# ==========================================
@router.post(
    "/staff/create",
    summary="Create a staff account (admin only)",
)
def create_staff_user(
    staff_data: AdminCreateStaff,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a new admin, editor, or moderator account."""
    existing = db.query(User).filter(User.email == staff_data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = User(
        user_id=str(uuid.uuid4()),
        name=staff_data.name,
        email=staff_data.email,
        password_hash=hash_password(staff_data.password),
        role=staff_data.role,
    )
    db.add(new_user)
    _log_action(db, admin, "staff_created", "user", new_user.user_id, new_user.name,
                f"Created {staff_data.role} account: {staff_data.name}",
                {"role": staff_data.role, "email": staff_data.email})
    db.commit()
    db.refresh(new_user)

    return {
        "message": f"{staff_data.role.capitalize()} '{staff_data.name}' created",
        "user_id": new_user.user_id,
        "email": staff_data.email,
        "role": staff_data.role,
    }


@router.get(
    "/staff",
    summary="List all staff accounts (admin only)",
)
def list_staff(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all admin, editor, and moderator accounts."""
    staff = db.query(User).filter(
        User.role.in_(["admin", "editor", "moderator"])
    ).order_by(User.created_at.desc()).all()

    return {
        "staff": [
            {
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "is_available": u.is_available,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in staff
        ],
        "total": len(staff),
    }


@router.put(
    "/staff/{user_id}/demote",
    summary="Demote staff to client (admin only)",
)
def demote_staff(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Remove staff access by demoting to client role."""
    if user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role
    user.role = "client"
    _log_action(db, admin, "staff_demoted", "user", user_id, user.name,
                f"Demoted '{user.name}' from {old_role} to client",
                {"old_role": old_role}, severity="warning")
    db.commit()

    return {"message": f"'{user.name}' demoted from {old_role} to client", "user_id": user_id}


# ==========================================
# Audit Log (Admin/Editor)
# ==========================================
@router.get(
    "/audit-log",
    summary="View admin audit log",
)
def get_audit_log(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: str = Query(None),
    admin_id: str = Query(None),
    severity: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Fetch audit trail entries with optional filters."""
    query = db.query(AdminAuditLog)
    if action:
        query = query.filter(AdminAuditLog.action == action)
    if admin_id:
        query = query.filter(AdminAuditLog.admin_id == admin_id)
    if severity:
        query = query.filter(AdminAuditLog.severity == severity)

    total = query.count()
    logs = query.order_by(AdminAuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "logs": [
            {
                "log_id": l.log_id,
                "admin_id": l.admin_id,
                "admin_name": l.admin_name,
                "action": l.action,
                "target_type": l.target_type,
                "target_id": l.target_id,
                "target_name": l.target_name,
                "description": l.description,
                "details": l.details,
                "severity": l.severity,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "total": total,
    }


# ==========================================
# Job Management (Admin/Editor)
# ==========================================
@router.get(
    "/jobs",
    summary="List all jobs (admin/editor)",
)
def admin_list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """List all jobs with client/worker info."""
    from app.models.bid import Bid

    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if search:
        query = query.filter(Job.title.ilike(f"%{search}%"))

    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for j in jobs:
        client = db.query(User).filter(User.user_id == j.client_id).first()
        worker = db.query(User).filter(User.user_id == j.assigned_worker_id).first() if j.assigned_worker_id else None
        bid_count = db.query(func.count(Bid.bid_id)).filter(Bid.job_id == j.job_id).scalar() or 0

        result.append({
            "job_id": j.job_id,
            "title": j.title,
            "description": j.description[:200] if j.description else "",
            "category": j.category,
            "status": j.status,
            "initial_price": float(j.initial_price) if j.initial_price else 0,
            "client_id": j.client_id,
            "client_name": client.name if client else "Unknown",
            "assigned_worker_id": j.assigned_worker_id,
            "worker_name": worker.name if worker else None,
            "bid_count": bid_count,
            "address": j.address,
            "image_url": j.image_url,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        })

    return {"jobs": result, "total": total}


@router.put(
    "/jobs/{job_id}/status",
    summary="Change job status (admin/editor)",
)
def admin_update_job_status(
    job_id: str,
    new_status: str = Query(..., pattern=r'^(open|in_progress|on_the_way|work_started|completed|canceled)$'),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Force-change a job's status."""
    from app.api.v1.notifications import create_notification

    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    old_status = job.status
    job.status = new_status

    create_notification(db, user_id=job.client_id, notif_type="job_status_changed",
                        title=f"Job status updated by admin",
                        message=f'Your job "{job.title}" status changed from {old_status} to {new_status}.',
                        reference_id=job_id, reference_type="job")

    _log_action(db, admin, "job_status_changed", "job", job_id, job.title,
                f"Changed status from {old_status} to {new_status}",
                {"old_status": old_status, "new_status": new_status})
    db.commit()

    return {"message": f"Job status changed to {new_status}", "job_id": job_id}


@router.delete(
    "/jobs/{job_id}",
    summary="Delete a job (admin only)",
)
def admin_delete_job(
    job_id: str,
    reason: str = Query("Removed by admin"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a job and notify all parties."""
    from app.api.v1.notifications import create_notification

    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    title = job.title
    client_id = job.client_id

    create_notification(db, user_id=client_id, notif_type="job_deleted",
                        title="Your job was removed",
                        message=f'Your job "{title}" was removed by an administrator. Reason: {reason}',
                        reference_id=job_id, reference_type="job")

    if job.assigned_worker_id:
        create_notification(db, user_id=job.assigned_worker_id, notif_type="job_deleted",
                            title="Assigned job was removed",
                            message=f'The job "{title}" was removed by an administrator. Reason: {reason}',
                            reference_id=job_id, reference_type="job")

    _log_action(db, admin, "job_deleted", "job", job_id, title,
                f"Deleted job '{title}'. Reason: {reason}",
                {"reason": reason}, severity="critical")

    db.delete(job)
    db.commit()

    return {"message": f"Job '{title}' deleted", "job_id": job_id, "reason": reason}


# ==========================================
# Reports Enhancement (Admin/Editor)
# ==========================================
@router.put(
    "/reports/{report_id}/escalate",
    summary="Escalate a report (admin/editor)",
)
def admin_escalate_report(
    report_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Escalate a report to critical priority."""
    from app.models.report import Report

    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.priority = "escalated"
    report.status = "in_progress"
    _log_action(db, admin, "report_escalated", "report", report_id, report.subject,
                f"Escalated report: {report.subject}", severity="warning")
    db.commit()

    return {"message": f"Report '{report.subject}' escalated", "report_id": report_id}


@router.put(
    "/reports/{report_id}/assign",
    summary="Assign report to staff (admin/editor)",
)
def admin_assign_report(
    report_id: str,
    staff_id: str = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR)),
):
    """Assign a report to a specific staff member."""
    from app.models.report import Report

    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    staff = db.query(User).filter(User.user_id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    report.assigned_to = staff_id
    if report.status == "open":
        report.status = "in_progress"
    db.commit()

    return {"message": f"Report assigned to {staff.name}", "report_id": report_id}


# ==========================================
# Enhanced Stats (with banned/staff counts)
# ==========================================
@router.get(
    "/stats/extended",
    summary="Extended platform statistics",
)
def get_extended_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN, UserRole.EDITOR, UserRole.MODERATOR)),
):
    """Extended statistics including banned users, staff counts, job values."""
    from app.models.bid import Bid
    from app.models.report import Report

    total_users = db.query(func.count(User.user_id)).scalar() or 0
    total_clients = db.query(func.count(User.user_id)).filter(User.role == "client").scalar() or 0
    total_workers = db.query(func.count(User.user_id)).filter(User.role == "worker").scalar() or 0
    total_admins = db.query(func.count(User.user_id)).filter(User.role == "admin").scalar() or 0
    total_editors = db.query(func.count(User.user_id)).filter(User.role == "editor").scalar() or 0
    total_moderators = db.query(func.count(User.user_id)).filter(User.role == "moderator").scalar() or 0
    banned_users = db.query(func.count(User.user_id)).filter(User.is_available == "banned").scalar() or 0
    suspended_users = db.query(func.count(User.user_id)).filter(User.is_available == "suspended").scalar() or 0

    total_jobs = db.query(func.count(Job.job_id)).scalar() or 0
    open_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "open").scalar() or 0
    in_progress_jobs = db.query(func.count(Job.job_id)).filter(Job.status.in_(["in_progress", "on_the_way", "work_started"])).scalar() or 0
    completed_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "completed").scalar() or 0
    canceled_jobs = db.query(func.count(Job.job_id)).filter(Job.status == "canceled").scalar() or 0

    total_bids = db.query(func.count(Bid.bid_id)).scalar() or 0
    total_job_value = db.query(func.sum(Job.initial_price)).scalar() or 0
    completed_value = db.query(func.sum(Job.initial_price)).filter(Job.status == "completed").scalar() or 0

    open_reports = db.query(func.count(Report.report_id)).filter(Report.status == "open").scalar() or 0
    escalated_reports = db.query(func.count(Report.report_id)).filter(Report.priority == "escalated").scalar() or 0

    pending_certs = db.query(func.count(Certification.cert_id)).filter(
        Certification.status == "pending").scalar() or 0

    return {
        "users": {
            "total": total_users, "clients": total_clients, "workers": total_workers,
            "admins": total_admins, "editors": total_editors, "moderators": total_moderators,
            "banned": banned_users, "suspended": suspended_users,
        },
        "jobs": {
            "total": total_jobs, "open": open_jobs, "in_progress": in_progress_jobs,
            "completed": completed_jobs, "canceled": canceled_jobs,
            "total_value": float(total_job_value), "completed_value": float(completed_value),
        },
        "bids": {"total": total_bids},
        "reports": {"open": open_reports, "escalated": escalated_reports},
        "certs": {"pending": pending_certs},
    }
