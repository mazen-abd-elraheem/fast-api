"""
Sanaie Platform — Job Routes
Job CRUD with image upload, filtering, search, and status transitions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_user, require_role, handle_service_exception
from app.models.user import User
from app.enums import UserRole, JobCategory, JobStatus
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    JobListResponse,
    JobWithWorkerLocationResponse,
)
from app.services.job_service import JobService
from app.services.asset_service import AssetService
from app.core.exceptions import SanaieException

router = APIRouter()


# ==========================================
# Job CRUD
# ==========================================

@router.post(
    "/",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job posting (Client only)",
)
async def create_job(
    title: str = Form(...),
    description: str = Form(...),
    category: JobCategory = Form(...),
    initial_price: float = Form(..., gt=0),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    address: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(UserRole.CLIENT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Submit a new service request with optional photo and location.

    - Only **clients** and **admins** can create jobs.
    - Photos are saved to the local server.
    - Location indicates where the work needs to be done.
    """
    # Handle image upload
    image_url = None
    if image and image.filename:
        image_url = await AssetService.save_upload(image, subfolder="jobs")

    try:
        job_data = JobCreate(
            title=title,
            description=description,
            category=category,
            initial_price=initial_price,
            latitude=latitude,
            longitude=longitude,
            address=address,
        )
    except Exception as validation_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(validation_err),
        )

    try:
        return JobService.create_job(db, job_data, current_user.user_id, image_url)
    except SanaieException as e:
        handle_service_exception(e)


@router.get(
    "/",
    response_model=JobListResponse,
    summary="List all jobs",
)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    category: Optional[JobCategory] = Query(None),
    search: Optional[str] = Query(None, min_length=2, max_length=100, description="Search in title/description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of jobs with optional filters.

    - **status**: Filter by open/in_progress/completed/canceled
    - **category**: Filter by plumbing/electrical/etc.
    - **search**: Full-text search on title and description
    """
    s = status_filter.value if status_filter else None
    c = category.value if category else None
    return JobService.list_jobs(db, skip=skip, limit=limit, status_filter=s, category=c, search=search)


@router.get(
    "/my/client",
    response_model=JobListResponse,
    summary="My jobs as client",
)
def get_my_client_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all jobs I posted as a client, optionally filtered by status."""
    s = status_filter.value if status_filter else None
    return JobService.get_client_jobs(db, current_user.user_id, skip, limit, status_filter=s)


@router.get(
    "/my/worker",
    response_model=JobListResponse,
    summary="My assigned jobs as worker",
)
def get_my_worker_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all jobs assigned to me as a worker."""
    return JobService.get_worker_jobs(db, current_user.user_id, skip, limit)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a job by ID",
)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed information about a specific job."""
    job = JobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get(
    "/{job_id}/with-worker-location",
    response_model=JobWithWorkerLocationResponse,
    summary="Get job details with assigned worker GPS coordinates",
)
def get_job_with_worker_location(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns job details plus the assigned worker's latitude/longitude.
    Used by the client map to show the technician's location after bid acceptance.
    """
    from app.models.job import Job as JobModel
    from app.models.user import User as UserModel

    job_resp = JobService.get_job(db, job_id)
    if not job_resp:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch assigned worker's coordinates
    worker_lat = None
    worker_lng = None
    worker_display_name = None
    if job_resp.assigned_worker_id:
        worker = db.query(UserModel).filter(
            UserModel.user_id == job_resp.assigned_worker_id
        ).first()
        if worker:
            worker_lat = worker.latitude
            worker_lng = worker.longitude
            worker_display_name = worker.name

    return JobWithWorkerLocationResponse(
        **job_resp.model_dump(),
        worker_latitude=worker_lat,
        worker_longitude=worker_lng,
        worker_name_display=worker_display_name,
    )


@router.put(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update a job (owner, if open)",
)
def update_job(
    job_id: str,
    update_data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update job title, description, category, price, or location. Only by the owner while open."""
    try:
        result = JobService.update_job(db, job_id, current_user.user_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result
    except SanaieException as e:
        handle_service_exception(e)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job (owner, if open)",
)
def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a job. Only by the owner while it is still open."""
    try:
        success = JobService.delete_job(db, job_id, current_user.user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        return None
    except SanaieException as e:
        handle_service_exception(e)


# ==========================================
# Job Status Transitions
# ==========================================

@router.put(
    "/{job_id}/complete",
    response_model=JobResponse,
    summary="Mark job as completed",
)
def complete_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Client or technician confirms the job is completed."""
    try:
        result = JobService.complete_job(db, job_id, current_user.user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{job_id}/on-the-way",
    response_model=JobResponse,
    summary="Technician marks on the way",
)
def mark_on_the_way(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Technician marks they are heading to the job location."""
    try:
        result = JobService.mark_on_the_way(db, job_id, current_user.user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{job_id}/start-work",
    response_model=JobResponse,
    summary="Technician marks work started",
)
def start_work(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Technician marks that they have started working on the job."""
    try:
        result = JobService.start_work(db, job_id, current_user.user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{job_id}/cancel",
    response_model=JobResponse,
    summary="Cancel a job",
)
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a job (cannot cancel if already completed)."""
    try:
        result = JobService.cancel_job(db, job_id, current_user.user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")
        return result
    except SanaieException as e:
        handle_service_exception(e)
