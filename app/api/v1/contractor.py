"""
Sanaie Platform — Contractor Routes
Team management, job assignments, and live GPS tracking for contractors.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_role, handle_service_exception
from app.models.user import User
from app.enums import UserRole
from app.schemas.contractor import (
    AddMemberRequest,
    GroupMemberResponse,
    AssignmentCreate,
    AssignmentResponse,
    AssignmentListResponse,
    TechnicianLocationResponse,
)
from app.services.contractor_service import ContractorService
from app.core.exceptions import SanaieException

router = APIRouter()


# ══════════════════════════════════════════
# Team Management
# ══════════════════════════════════════════

@router.get(
    "/team",
    response_model=list[GroupMemberResponse],
    summary="List my team members",
)
def get_team(
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Get all active technicians in the contractor's team."""
    return ContractorService.get_team_members(db, current_user.user_id)


@router.post(
    "/team/add",
    response_model=GroupMemberResponse,
    summary="Add a technician to my team",
)
def add_team_member(
    data: AddMemberRequest,
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Add a technician to the contractor's group by email."""
    try:
        return ContractorService.add_member(db, current_user.user_id, data.technician_email)
    except SanaieException as e:
        handle_service_exception(e)


@router.delete(
    "/team/{user_id}",
    summary="Remove a member from my team",
)
def remove_team_member(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Remove a technician from the contractor's group."""
    try:
        return ContractorService.remove_member(db, current_user.user_id, user_id)
    except SanaieException as e:
        handle_service_exception(e)


# ══════════════════════════════════════════
# Assignment Management
# ══════════════════════════════════════════

@router.post(
    "/assignments",
    response_model=AssignmentResponse,
    summary="Create a new assignment",
)
def create_assignment(
    data: AssignmentCreate,
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Create and assign a task to a team member."""
    try:
        return ContractorService.create_assignment(db, current_user.user_id, data)
    except SanaieException as e:
        handle_service_exception(e)


@router.get(
    "/assignments",
    response_model=AssignmentListResponse,
    summary="List my assignments",
)
def list_assignments(
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Get all assignments created by this contractor."""
    return ContractorService.get_assignments(db, current_user.user_id)


@router.get(
    "/assignments/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Get assignment detail",
)
def get_assignment(
    assignment_id: str,
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Get a single assignment by ID."""
    try:
        return ContractorService.get_assignment(db, assignment_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.delete(
    "/assignments/{assignment_id}",
    summary="Cancel an assignment",
)
def delete_assignment(
    assignment_id: str,
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Cancel/delete an assignment."""
    try:
        return ContractorService.delete_assignment(db, assignment_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


# ══════════════════════════════════════════
# Tracking — GPS Locations
# ══════════════════════════════════════════

@router.get(
    "/team/locations",
    response_model=list[TechnicianLocationResponse],
    summary="Get live GPS of all team members",
)
def get_team_locations(
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Get real-time GPS locations of all active team members with current assignments."""
    return ContractorService.get_team_locations(db, current_user.user_id)


@router.get(
    "/team/{user_id}/location",
    response_model=TechnicianLocationResponse,
    summary="Get a member's location",
)
def get_member_location(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Get a single team member's GPS coordinates and current assignment."""
    try:
        return ContractorService.get_member_location(db, current_user.user_id, user_id)
    except SanaieException as e:
        handle_service_exception(e)


# ══════════════════════════════════════════
# Technician-side (for techs in a group)
# ══════════════════════════════════════════

@router.get(
    "/my-assignments",
    response_model=AssignmentListResponse,
    summary="Get my assignments (as technician)",
)
def get_my_assignments(
    current_user: User = Depends(require_role(UserRole.WORKER, UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Get all assignments assigned to this technician."""
    return ContractorService.get_my_assignments(db, current_user.user_id)


@router.put(
    "/my-assignments/{assignment_id}/on-the-way",
    response_model=AssignmentResponse,
    summary="Mark assignment on the way",
)
def assignment_on_the_way(
    assignment_id: str,
    current_user: User = Depends(require_role(UserRole.WORKER, UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Technician marks they are on the way for this assignment."""
    try:
        return ContractorService.assignment_on_the_way(db, assignment_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/my-assignments/{assignment_id}/start-work",
    response_model=AssignmentResponse,
    summary="Mark work started",
)
def assignment_start_work(
    assignment_id: str,
    current_user: User = Depends(require_role(UserRole.WORKER, UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Technician marks work started — records started_at timestamp."""
    try:
        return ContractorService.assignment_start_work(db, assignment_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/my-assignments/{assignment_id}/complete",
    response_model=AssignmentResponse,
    summary="Mark assignment completed",
)
def assignment_complete(
    assignment_id: str,
    current_user: User = Depends(require_role(UserRole.WORKER, UserRole.CONTRACTOR)),
    db: Session = Depends(get_db),
):
    """Technician marks done — records completed_at and computes duration_minutes."""
    try:
        return ContractorService.assignment_complete(db, assignment_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)
