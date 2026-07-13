"""
Sanaie Platform — Review Routes
Post-completion reviews and worker ratings.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_role, handle_service_exception
from app.models.user import User
from app.enums import UserRole
from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
    WorkerRatingResponse,
)
from app.services.review_service import ReviewService
from app.core.exceptions import SanaieException

router = APIRouter()


@router.post(
    "/",
    response_model=ReviewResponse,
    status_code=201,
    summary="Submit a review (Client only, after completion)",
)
def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(require_role(UserRole.CLIENT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Submit a review for a completed job.

    - Only the **client** who owns the job can submit.
    - The job must be **completed**.
    - One review per job.
    - Rating is 1–5.
    """
    try:
        return ReviewService.create_review(db, review_data, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.get(
    "/worker/{worker_id}",
    response_model=ReviewListResponse,
    summary="Get reviews for a worker",
)
def get_worker_reviews(
    worker_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated reviews received by a worker."""
    return ReviewService.get_reviews_for_worker(db, worker_id, skip, limit)


@router.get(
    "/worker/{worker_id}/rating",
    response_model=WorkerRatingResponse,
    summary="Get worker's average rating",
)
def get_worker_rating(
    worker_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get aggregated rating (average + total reviews) for a worker."""
    return ReviewService.get_worker_rating(db, worker_id)


@router.get(
    "/job/{job_id}",
    response_model=ReviewResponse,
    summary="Get review for a job",
)
def get_job_review(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the review associated with a specific job."""
    review = ReviewService.get_review_for_job(db, job_id)
    if not review:
        raise HTTPException(status_code=404, detail="No review found for this job")
    return review
