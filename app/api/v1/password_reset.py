"""
Sanaie Platform — Password Reset Routes
Email-based password reset with time-limited tokens.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import hash_password, verify_token, create_access_token
from app.models.user import User
from app.services.user_service import UserService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ── Schemas ──
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Endpoints ──

@router.post(
    "/forgot-password",
    summary="Request password reset",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset link. A time-limited token is generated.

    In production, this token would be emailed to the user.
    For now, it's returned in the response for testing.
    """
    user = UserService.get_by_email(db, data.email)

    # Always return success to prevent email enumeration
    if not user:
        return {
            "message": "If an account with that email exists, a reset link has been sent.",
            "detail": "Check your email for the reset link.",
        }

    # Generate a short-lived reset token (15 minutes)
    reset_token = create_access_token(
        data={"sub": user.user_id, "type": "password_reset"},
        expires_delta=timedelta(minutes=15),
    )

    # TODO: In production, send this via email (SendGrid/SES)
    # For now, return the token directly for testing
    return {
        "message": "If an account with that email exists, a reset link has been sent.",
        "reset_token": reset_token,  # Remove in production — send via email instead
    }


@router.post(
    "/reset-password",
    summary="Reset password with token",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    data: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """
    Reset password using the token from forgot-password.
    Token must be valid and not expired (15 minute window).
    """
    # Verify the reset token
    payload = verify_token(data.token, expected_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token. Please request a new one.",
        )

    # Extra check: verify it's actually a reset token
    token_type = payload.get("type", "")
    if token_type != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type.",
        )

    user_id = payload.get("sub")
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate password strength
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Update password
    user.password_hash = hash_password(data.new_password)
    db.commit()

    return {"message": "Password has been reset successfully. You can now log in."}


@router.post(
    "/change-password",
    summary="Change password (authenticated)",
    status_code=status.HTTP_200_OK,
)
def change_password(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(lambda: None),  # Will be overridden by deps
):
    """
    Change password for the currently logged-in user.
    Requires the current password for verification.
    """
    from app.api.deps import get_current_user
    # This endpoint should be used with get_current_user dependency
    raise HTTPException(
        status_code=501,
        detail="Use /api/v1/users/me/change-password instead",
    )
