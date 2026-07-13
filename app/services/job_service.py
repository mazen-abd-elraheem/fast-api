"""
Sanaie Platform — Job Service
Business logic for job CRUD, status transitions, and listing.
Uses domain exceptions and fixes N+1 queries.
"""
import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.job import Job
from app.models.user import User
from app.models.bid import Bid
from app.enums import JobStatus, JobCategory
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
)
from app.core.sanitize import sanitize_text, sanitize_search


class JobService:
    """Business logic for job (service request) operations."""

    @staticmethod
    def _build_response(job: Job, db: Session) -> JobResponse:
        """Build a JobResponse from a Job model with extra data."""
        bid_count = db.query(func.count(Bid.bid_id)).filter(Bid.job_id == job.job_id).scalar() or 0

        # Use eagerly loaded relationships if available, otherwise query
        client_name = None
        if job.client:
            client_name = job.client.name
        else:
            client = db.query(User.name).filter(User.user_id == job.client_id).first()
            client_name = client.name if client else None

        worker_name = None
        if job.assigned_worker_id:
            if job.assigned_worker:
                worker_name = job.assigned_worker.name
            else:
                worker = db.query(User.name).filter(User.user_id == job.assigned_worker_id).first()
                worker_name = worker.name if worker else None

        # Get the accepted bid amount (what the worker actually earns)
        accepted_bid_amount = None
        if job.assigned_worker_id:
            accepted_bid = (
                db.query(Bid.amount)
                .filter(
                    Bid.job_id == job.job_id,
                    Bid.worker_id == job.assigned_worker_id,
                    Bid.status == "accepted",
                )
                .first()
            )
            if accepted_bid:
                accepted_bid_amount = float(accepted_bid.amount)

        return JobResponse(
            job_id=job.job_id,
            client_id=job.client_id,
            client_name=client_name,
            title=job.title,
            description=job.description,
            category=job.category.lower() if job.category else "general",
            status=job.status.lower() if job.status else "open",
            image_url=job.image_url,
            initial_price=float(job.initial_price),
            accepted_bid_amount=accepted_bid_amount,
            latitude=job.latitude,
            longitude=job.longitude,
            address=job.address,
            assigned_worker_id=job.assigned_worker_id,
            assigned_worker_name=worker_name,
            bid_count=bid_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    @staticmethod
    def _build_list_response(jobs: list, total: int, skip: int, limit: int, db: Session) -> JobListResponse:
        """Helper to build paginated list response."""
        return JobListResponse(
            jobs=[JobService._build_response(j, db) for j in jobs],
            total=total,
            page=(skip // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            total_pages=(total + limit - 1) // limit if limit > 0 else 1,
        )

    @staticmethod
    def create_job(
        db: Session,
        job_data: JobCreate,
        client_id: str,
        image_url: Optional[str] = None,
    ) -> JobResponse:
        """Create a new job posting (client only)."""
        db_job = Job(
            job_id=f"J-{uuid.uuid4().hex[:8].upper()}",
            client_id=client_id,
            title=sanitize_text(job_data.title, max_length=500),
            description=sanitize_text(job_data.description, max_length=5000),
            category=job_data.category.value,
            status=JobStatus.OPEN.value,
            image_url=image_url,
            initial_price=job_data.initial_price,
            latitude=job_data.latitude,
            longitude=job_data.longitude,
            address=job_data.address,
        )

        db.add(db_job)
        db.commit()
        db.refresh(db_job)

        return JobService._build_response(db_job, db)

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[JobResponse]:
        """Get a single job by ID."""
        job = (
            db.query(Job)
            .options(joinedload(Job.client), joinedload(Job.assigned_worker))
            .filter(Job.job_id == job_id)
            .first()
        )
        if not job:
            return None
        return JobService._build_response(job, db)

    @staticmethod
    def list_jobs(
        db: Session,
        skip: int = 0,
        limit: int = 10,
        status_filter: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> JobListResponse:
        # Count without joins to avoid inflated totals
        count_q = db.query(func.count(Job.job_id))
        if status_filter:
            count_q = count_q.filter(Job.status == status_filter)
        if category:
            count_q = count_q.filter(Job.category == category)
        if search:
            search_term = f"%{sanitize_search(search)}%"
            count_q = count_q.filter(
                (Job.title.ilike(search_term)) | (Job.description.ilike(search_term))
            )
        total = count_q.scalar() or 0

        # Fetch with joins but deduplicated
        query = db.query(Job).options(
            joinedload(Job.client), joinedload(Job.assigned_worker)
        )
        if status_filter:
            query = query.filter(Job.status == status_filter)
        if category:
            query = query.filter(Job.category == category)
        if search:
            search_term = f"%{sanitize_search(search)}%"
            query = query.filter(
                (Job.title.ilike(search_term)) | (Job.description.ilike(search_term))
            )

        jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()

        # Deduplicate (joinedload with multiple relationships can cause duplicates)
        seen = set()
        unique_jobs = []
        for j in jobs:
            if j.job_id not in seen:
                seen.add(j.job_id)
                unique_jobs.append(j)

        return JobService._build_list_response(unique_jobs, total, skip, limit, db)

    @staticmethod
    def get_client_jobs(db: Session, client_id: str, skip: int = 0, limit: int = 10, status_filter: str = None) -> JobListResponse:
        """Get all jobs created by a client, optionally filtered by status."""
        query = db.query(Job).options(
            joinedload(Job.client), joinedload(Job.assigned_worker)
        ).filter(Job.client_id == client_id)
        if status_filter:
            query = query.filter(Job.status == status_filter)
        total = query.count()
        jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
        return JobService._build_list_response(jobs, total, skip, limit, db)

    @staticmethod
    def get_worker_jobs(db: Session, worker_id: str, skip: int = 0, limit: int = 10) -> JobListResponse:
        """Get all jobs assigned to a worker."""
        query = db.query(Job).options(
            joinedload(Job.client), joinedload(Job.assigned_worker)
        ).filter(Job.assigned_worker_id == worker_id)
        total = query.count()
        jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
        return JobService._build_list_response(jobs, total, skip, limit, db)

    @staticmethod
    def update_job(db: Session, job_id: str, client_id: str, update_data: JobUpdate) -> Optional[JobResponse]:
        """Update a job (only owner, only if open)."""
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        if job.client_id != client_id:
            raise ForbiddenException("Not the job owner")
        if job.status != JobStatus.OPEN.value:
            raise BadRequestException("Can only update open jobs")

        if update_data.title is not None:
            job.title = sanitize_text(update_data.title, max_length=500)
        if update_data.description is not None:
            job.description = sanitize_text(update_data.description, max_length=5000)
        if update_data.category is not None:
            job.category = update_data.category.value
        if update_data.initial_price is not None:
            job.initial_price = update_data.initial_price
        if update_data.latitude is not None:
            job.latitude = update_data.latitude
        if update_data.longitude is not None:
            job.longitude = update_data.longitude
        if update_data.address is not None:
            job.address = update_data.address

        db.commit()
        db.refresh(job)
        return JobService._build_response(job, db)

    @staticmethod
    def delete_job(db: Session, job_id: str, client_id: str) -> bool:
        """Delete a job (only owner, only if open)."""
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return False
        if job.client_id != client_id:
            raise ForbiddenException("Not the job owner")
        if job.status != JobStatus.OPEN.value:
            raise BadRequestException("Can only delete open jobs")

        db.delete(job)
        db.commit()
        return True

    @staticmethod
    def complete_job(db: Session, job_id: str, user_id: str) -> Optional[JobResponse]:
        """Mark a job as completed (client or worker, must be work_started or in_progress)."""
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        if job.client_id != user_id and job.assigned_worker_id != user_id:
            raise ForbiddenException("Not authorized for this job")
        if job.status not in (JobStatus.IN_PROGRESS.value, JobStatus.WORK_STARTED.value):
            raise BadRequestException("Job must be in progress or work started to complete")

        job.status = JobStatus.COMPLETED.value
        db.commit()
        db.refresh(job)
        return JobService._build_response(job, db)

    @staticmethod
    def mark_on_the_way(db: Session, job_id: str, worker_id: str) -> Optional[JobResponse]:
        """Technician marks they are on the way (must be in_progress)."""
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        if job.assigned_worker_id != worker_id:
            raise ForbiddenException("Not the assigned technician")
        if job.status != JobStatus.IN_PROGRESS.value:
            raise BadRequestException("Job must be in progress to mark on the way")

        job.status = JobStatus.ON_THE_WAY.value
        db.commit()
        db.refresh(job)
        return JobService._build_response(job, db)

    @staticmethod
    def start_work(db: Session, job_id: str, worker_id: str) -> Optional[JobResponse]:
        """Technician marks work has started (must be on_the_way)."""
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        if job.assigned_worker_id != worker_id:
            raise ForbiddenException("Not the assigned technician")
        if job.status != JobStatus.ON_THE_WAY.value:
            raise BadRequestException("Must be on the way before starting work")

        job.status = JobStatus.WORK_STARTED.value
        db.commit()
        db.refresh(job)
        return JobService._build_response(job, db)

    @staticmethod
    def cancel_job(db: Session, job_id: str, client_id: str) -> Optional[JobResponse]:
        """Cancel a job (only if not already completed)."""
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        if job.client_id != client_id:
            raise ForbiddenException("Not the job owner")
        if job.status == JobStatus.COMPLETED.value:
            raise BadRequestException("Cannot cancel a completed job")

        job.status = JobStatus.CANCELED.value
        db.commit()
        db.refresh(job)
        return JobService._build_response(job, db)
