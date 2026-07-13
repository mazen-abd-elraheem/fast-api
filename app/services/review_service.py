"""
Sanaie Platform — Review Service
Handles post-completion reviews and rating aggregation.
Uses domain exceptions instead of HTTPException.
"""
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.review import Review
from app.models.job import Job
from app.models.user import User
from app.enums import JobStatus
from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
    WorkerRatingResponse,
)
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    DuplicateException,
)


class ReviewService:
    """Handles post-completion reviews and rating aggregation."""

    @staticmethod
    def _build_response(review: Review, db: Session) -> ReviewResponse:
        """Build a ReviewResponse with client name."""
        client = db.query(User).filter(User.user_id == review.client_id).first()

        return ReviewResponse(
            review_id=review.review_id,
            job_id=review.job_id,
            client_id=review.client_id,
            client_name=client.name if client else None,
            worker_id=review.worker_id,
            rating_score=review.rating_score,
            comment=review.comment,
            created_at=review.created_at,
        )

    @staticmethod
    def create_review(db: Session, review_data: ReviewCreate, client_id: str) -> ReviewResponse:
        """
        Client submits a review after job completion.
        Constraints: job must be completed, only the job owner,
        and only one review per job.
        """
        job = db.query(Job).filter(Job.job_id == review_data.job_id).first()
        if not job:
            raise NotFoundException("Job", review_data.job_id)
        if job.status != JobStatus.COMPLETED.value:
            raise BadRequestException("Can only review completed jobs")
        if job.client_id != client_id:
            raise ForbiddenException("Not the job owner")
        if job.assigned_worker_id != review_data.worker_id:
            raise BadRequestException("Worker does not match assigned worker")

        existing = db.query(Review).filter(Review.job_id == review_data.job_id).first()
        if existing:
            raise DuplicateException("A review already exists for this job")

        db_review = Review(
            review_id=str(uuid.uuid4()),
            job_id=review_data.job_id,
            client_id=client_id,
            worker_id=review_data.worker_id,
            rating_score=review_data.rating_score,
            comment=review_data.comment,
        )

        db.add(db_review)
        db.commit()
        db.refresh(db_review)

        return ReviewService._build_response(db_review, db)

    @staticmethod
    def get_reviews_for_worker(
        db: Session, worker_id: str, skip: int = 0, limit: int = 10
    ) -> ReviewListResponse:
        """Get paginated reviews for a worker."""
        query = db.query(Review).filter(Review.worker_id == worker_id)
        total = query.count()
        reviews = query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()

        return ReviewListResponse(
            reviews=[ReviewService._build_response(r, db) for r in reviews],
            total=total,
            page=(skip // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            total_pages=(total + limit - 1) // limit if limit > 0 else 1,
        )

    @staticmethod
    def get_review_for_job(db: Session, job_id: str) -> Optional[ReviewResponse]:
        """Get the review for a specific job."""
        review = db.query(Review).filter(Review.job_id == job_id).first()
        if not review:
            return None
        return ReviewService._build_response(review, db)

    @staticmethod
    def get_worker_rating(db: Session, worker_id: str) -> WorkerRatingResponse:
        """Get aggregated rating for a worker."""
        result = (
            db.query(
                func.avg(Review.rating_score).label("avg_rating"),
                func.count(Review.review_id).label("total_reviews"),
            )
            .filter(Review.worker_id == worker_id)
            .first()
        )

        return WorkerRatingResponse(
            worker_id=worker_id,
            avg_rating=round(float(result.avg_rating), 2) if result.avg_rating else 0.0,
            total_reviews=result.total_reviews or 0,
        )
