"""
Sanaie Platform — User Routes
Profile management, location updates, and nearby worker search.
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, handle_service_exception
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserLocationUpdate,
    UserPublicResponse,
    WorkerNearbyResponse,
)
from app.services.user_service import UserService
from app.core.exceptions import SanaieException
from app.core.security import verify_password, hash_password
from pydantic import BaseModel, Field

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get my profile",
)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user's full profile."""
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update my profile",
)
def update_my_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update name, phone, skills, availability, or profile image."""
    try:
        return UserService.update_profile(db, current_user.user_id, update_data)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/me/photo",
    summary="Upload profile photo",
)
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a profile photo. Accepts JPEG/PNG images up to 5MB."""
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if photo.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")

    contents = await photo.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5MB")

    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    ext = ext_map.get(photo.content_type, ".jpg")

    from app.core.config import get_settings
    _settings = get_settings()
    profiles_dir = os.path.join(_settings.UPLOAD_DIR, "profiles")
    os.makedirs(profiles_dir, exist_ok=True)

    filename = f"{current_user.user_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(profiles_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    image_url = f"/static/uploads/profiles/{filename}"
    current_user.profile_image_url = image_url
    db.commit()

    return {"message": "Photo uploaded", "profile_image_url": image_url}


@router.put(
    "/me/location",
    response_model=UserResponse,
    summary="Update my geolocation",
)
def update_my_location(
    location: UserLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update latitude and longitude for proximity features."""
    try:
        return UserService.update_location(db, current_user.user_id, location)
    except SanaieException as e:
        handle_service_exception(e)


@router.get(
    "/workers/nearby",
    response_model=list[WorkerNearbyResponse],
    summary="Find nearby workers",
)
def get_nearby_workers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50.0, gt=0, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Find workers within a specified radius using Haversine distance.

    - **latitude/longitude**: Center point for the search
    - **radius_km**: Maximum distance in km (default 50)
    """
    return UserService.get_nearby_workers(db, latitude, longitude, radius_km)


@router.get(
    "/{user_id}",
    response_model=UserPublicResponse,
    summary="Get user public profile",
)
def get_user_profile(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a user's public profile (no sensitive info)."""
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rating_info = UserService.get_worker_rating(db, user_id)

    return UserPublicResponse(
        user_id=user.user_id,
        name=user.name,
        role=user.role,
        skills=user.skills,
        profile_image_url=user.profile_image_url,
        is_available=user.is_available,
        avg_rating=rating_info["avg_rating"],
        total_reviews=rating_info["total_reviews"],
    )


@router.get(
    "/{user_id}/client-summary",
    summary="Get client summary for technician view",
)
def get_client_summary(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a client's public profile enriched with:
    - Number of jobs they've posted
    - Reviews they've written about technicians (with comments)
    Useful for technicians to assess a client before bidding.
    """
    from app.models.job import Job as JobModel
    from app.models.review import Review as ReviewModel
    from sqlalchemy import func as sqla_func

    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count jobs posted by this client
    jobs_posted = (
        db.query(sqla_func.count(JobModel.job_id))
        .filter(JobModel.client_id == user_id)
        .scalar() or 0
    )

    # Count completed jobs
    jobs_completed = (
        db.query(sqla_func.count(JobModel.job_id))
        .filter(JobModel.client_id == user_id, JobModel.status == "completed")
        .scalar() or 0
    )

    # Get reviews this client has written (their comments about technicians)
    reviews_written = (
        db.query(ReviewModel)
        .filter(ReviewModel.client_id == user_id)
        .order_by(ReviewModel.created_at.desc())
        .limit(10)
        .all()
    )

    reviews_data = []
    for r in reviews_written:
        # Get the worker name for context
        worker = db.query(User.name).filter(User.user_id == r.worker_id).first()
        reviews_data.append({
            "review_id": r.review_id,
            "worker_id": r.worker_id,
            "worker_name": worker.name if worker else "Unknown",
            "rating_score": r.rating_score,
            "comment": r.comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    # Average rating this client gives
    avg_given = (
        db.query(sqla_func.avg(ReviewModel.rating_score))
        .filter(ReviewModel.client_id == user_id)
        .scalar()
    )

    # Member since
    member_since = user.created_at.isoformat() if user.created_at else None

    return {
        "user_id": user.user_id,
        "name": user.name,
        "role": user.role,
        "profile_image_url": user.profile_image_url,
        "member_since": member_since,
        "jobs_posted": jobs_posted,
        "jobs_completed": jobs_completed,
        "avg_rating_given": round(float(avg_given), 1) if avg_given else None,
        "reviews_written": reviews_data,
        "total_reviews_written": len(reviews_data),
    }


# ── Password Change Schema ──
class PasswordChangeBody(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.put(
    "/me/change-password",
    summary="Change my password",
)
def change_my_password(
    data: PasswordChangeBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change the authenticated user's password.
    Requires the current password for verification.
    """
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


# ── ID Verification Endpoints ──

@router.post(
    "/me/id-verification",
    summary="Upload ID for verification",
)
async def upload_id_verification(
    front: UploadFile = File(...),
    back: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload front (required) and back (optional) of government ID for verification.
    Creates a pending verification request for admin review.
    """
    from app.models.id_verification import IDVerification

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if front.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")

    front_data = await front.read()
    if len(front_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 10MB")

    # Save front image
    from app.core.config import get_settings
    _settings = get_settings()
    verify_dir = os.path.join(_settings.UPLOAD_DIR, "verifications")
    os.makedirs(verify_dir, exist_ok=True)

    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

    front_ext = ext_map.get(front.content_type, ".jpg")
    front_filename = f"{current_user.user_id}_front_{uuid.uuid4().hex[:8]}{front_ext}"
    front_path = os.path.join(verify_dir, front_filename)
    with open(front_path, "wb") as f:
        f.write(front_data)
    front_url = f"/static/uploads/verifications/{front_filename}"

    # Save back image if provided
    back_url = None
    if back and back.filename:
        if back.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Back image: Only JPEG, PNG, and WebP allowed")
        back_data = await back.read()
        if len(back_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Back image must be under 10MB")
        back_ext = ext_map.get(back.content_type, ".jpg")
        back_filename = f"{current_user.user_id}_back_{uuid.uuid4().hex[:8]}{back_ext}"
        back_path = os.path.join(verify_dir, back_filename)
        with open(back_path, "wb") as f:
            f.write(back_data)
        back_url = f"/static/uploads/verifications/{back_filename}"

    # Create verification record
    verification = IDVerification(
        verification_id=str(uuid.uuid4()),
        user_id=current_user.user_id,
        front_image_url=front_url,
        back_image_url=back_url,
        status="pending",
    )
    db.add(verification)

    # Update user status
    current_user.is_verified = "pending"
    db.commit()

    return {
        "message": "ID submitted for verification",
        "verification_id": verification.verification_id,
        "status": "pending",
    }


@router.get(
    "/me/id-verification",
    summary="Get my ID verification status",
)
def get_my_verification_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's ID verification status and any rejection reason."""
    from app.models.id_verification import IDVerification

    # Get latest verification request
    verification = (
        db.query(IDVerification)
        .filter(IDVerification.user_id == current_user.user_id)
        .order_by(IDVerification.created_at.desc())
        .first()
    )

    if not verification:
        return {
            "status": current_user.is_verified or "unverified",
            "rejection_reason": None,
            "submitted_at": None,
        }

    return {
        "status": current_user.is_verified or verification.status,
        "rejection_reason": verification.rejection_reason,
        "submitted_at": verification.created_at.isoformat() if verification.created_at else None,
        "verification_id": verification.verification_id,
    }
