"""
Sanaie Platform — Contractor Service
Business logic for contractor team management, job assignments, and tracking.
"""
import uuid
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.contractor_group import ContractorGroup
from app.models.job_assignment import JobAssignment
from app.models.job import Job
from app.enums import UserRole
from app.schemas.contractor import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentListResponse,
    GroupMemberResponse,
    TechnicianLocationResponse,
)
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    DuplicateException,
)


class ContractorService:
    """Handles contractor team management, assignments, and tracking."""

    # ══════════════════════════════════════════
    # Team Management
    # ══════════════════════════════════════════

    @staticmethod
    def get_team_members(db: Session, contractor_id: str) -> List[GroupMemberResponse]:
        """Get all active members in a contractor's team."""
        memberships = (
            db.query(ContractorGroup)
            .filter(
                ContractorGroup.contractor_id == contractor_id,
                ContractorGroup.status == "active",
            )
            .all()
        )

        members = []
        for m in memberships:
            tech = db.query(User).filter(User.user_id == m.technician_id).first()
            if tech:
                members.append(GroupMemberResponse(
                    user_id=tech.user_id,
                    name=tech.name,
                    email=tech.email,
                    phone_number=tech.phone_number,
                    profile_image_url=tech.profile_image_url,
                    is_available=tech.is_available,
                    latitude=tech.latitude,
                    longitude=tech.longitude,
                    joined_at=m.joined_at,
                ))

        return members

    @staticmethod
    def add_member(db: Session, contractor_id: str, technician_email: str) -> GroupMemberResponse:
        """Add a technician to the contractor's team by email."""
        # Find the technician
        tech = db.query(User).filter(User.email == technician_email).first()
        if not tech:
            raise NotFoundException("User", technician_email)

        # Verify the user is not a contractor or admin (they could be in client mode but work as a technician)
        tech_role = tech.role.value if hasattr(tech.role, 'value') else tech.role
        if tech_role in ("contractor", "admin"):
            raise BadRequestException("Contractors and admins cannot be added to a contractor group")

        # Prevent adding yourself
        if tech.user_id == contractor_id:
            raise BadRequestException("Cannot add yourself to your own group")

        # Check if already an active member of THIS contractor's group
        existing = (
            db.query(ContractorGroup)
            .filter(
                ContractorGroup.contractor_id == contractor_id,
                ContractorGroup.technician_id == tech.user_id,
                ContractorGroup.status == "active",
            )
            .first()
        )
        if existing:
            raise DuplicateException("This technician is already in your team")

        # Get contractor name for the notification
        contractor = db.query(User).filter(User.user_id == contractor_id).first()
        contractor_name = contractor.name if contractor else "A contractor"

        # Create membership (technician can belong to multiple groups)
        membership = ContractorGroup(
            contractor_group_id=str(uuid.uuid4()),
            contractor_id=contractor_id,
            technician_id=tech.user_id,
            status="active",
        )
        db.add(membership)

        # Send notification to the technician (visible in any mode)
        from app.api.v1.notifications import create_notification
        create_notification(
            db,
            user_id=tech.user_id,
            notif_type="team_invite",
            title=f"{contractor_name} added you to their team",
            message=f"You've been added to {contractor_name}'s contractor team. Switch to Technician mode to see assigned jobs.",
            reference_id=contractor_id,
            reference_type="contractor_team",
        )

        db.commit()

        return GroupMemberResponse(
            user_id=tech.user_id,
            name=tech.name,
            email=tech.email,
            phone_number=tech.phone_number,
            profile_image_url=tech.profile_image_url,
            is_available=tech.is_available,
            latitude=tech.latitude,
            longitude=tech.longitude,
            joined_at=membership.joined_at,
        )

    @staticmethod
    def remove_member(db: Session, contractor_id: str, technician_id: str) -> dict:
        """Remove a technician from the contractor's team."""
        membership = (
            db.query(ContractorGroup)
            .filter(
                ContractorGroup.contractor_id == contractor_id,
                ContractorGroup.technician_id == technician_id,
                ContractorGroup.status == "active",
            )
            .first()
        )
        if not membership:
            raise NotFoundException("Team member", technician_id)

        membership.status = "removed"
        membership.removed_at = datetime.now(timezone.utc)
        db.commit()

        return {"message": "Member removed from team"}

    # ══════════════════════════════════════════
    # Assignment Management
    # ══════════════════════════════════════════

    @staticmethod
    def _build_assignment_response(assignment: JobAssignment, db: Session) -> AssignmentResponse:
        """Build response from assignment model."""
        tech = db.query(User.name).filter(User.user_id == assignment.technician_id).first()
        return AssignmentResponse(
            assignment_id=assignment.assignment_id,
            contractor_id=assignment.contractor_id,
            technician_id=assignment.technician_id,
            technician_name=tech.name if tech else None,
            job_id=assignment.job_id,
            title=assignment.title,
            description=assignment.description,
            status=assignment.status,
            latitude=assignment.latitude,
            longitude=assignment.longitude,
            address=assignment.address,
            started_at=assignment.started_at,
            completed_at=assignment.completed_at,
            duration_minutes=assignment.duration_minutes,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )

    @staticmethod
    def create_assignment(db: Session, contractor_id: str, data: AssignmentCreate) -> AssignmentResponse:
        """Create a new assignment for a team member."""
        # Verify the technician is in this contractor's team
        membership = (
            db.query(ContractorGroup)
            .filter(
                ContractorGroup.contractor_id == contractor_id,
                ContractorGroup.technician_id == data.technician_id,
                ContractorGroup.status == "active",
            )
            .first()
        )
        if not membership:
            raise BadRequestException("This technician is not in your team")

        # If job_id is provided, verify it exists
        if data.job_id:
            job = db.query(Job).filter(Job.job_id == data.job_id).first()
            if not job:
                raise NotFoundException("Job", data.job_id)

        assignment = JobAssignment(
            assignment_id=f"A-{uuid.uuid4().hex[:8].upper()}",
            contractor_id=contractor_id,
            technician_id=data.technician_id,
            job_id=data.job_id,
            title=data.title,
            description=data.description,
            status="pending",
            latitude=data.latitude,
            longitude=data.longitude,
            address=data.address,
        )
        db.add(assignment)

        # Notify the technician about the new assignment
        contractor = db.query(User).filter(User.user_id == contractor_id).first()
        contractor_name = contractor.name if contractor else "Your contractor"
        from app.api.v1.notifications import create_notification
        create_notification(
            db,
            user_id=data.technician_id,
            notif_type="assignment",
            title=f"New assignment: {data.title}",
            message=f"{contractor_name} assigned you a job. Switch to Technician mode to view and start.",
            reference_id=assignment.assignment_id,
            reference_type="assignment",
        )

        db.commit()
        db.refresh(assignment)

        return ContractorService._build_assignment_response(assignment, db)

    @staticmethod
    def get_assignments(db: Session, contractor_id: str) -> AssignmentListResponse:
        """Get all assignments created by this contractor."""
        assignments = (
            db.query(JobAssignment)
            .filter(JobAssignment.contractor_id == contractor_id)
            .order_by(JobAssignment.created_at.desc())
            .all()
        )
        return AssignmentListResponse(
            assignments=[ContractorService._build_assignment_response(a, db) for a in assignments],
            total=len(assignments),
        )

    @staticmethod
    def get_assignment(db: Session, assignment_id: str, contractor_id: str) -> AssignmentResponse:
        """Get a single assignment."""
        assignment = db.query(JobAssignment).filter(JobAssignment.assignment_id == assignment_id).first()
        if not assignment:
            raise NotFoundException("Assignment", assignment_id)
        if assignment.contractor_id != contractor_id:
            raise ForbiddenException("Not your assignment")
        return ContractorService._build_assignment_response(assignment, db)

    @staticmethod
    def delete_assignment(db: Session, assignment_id: str, contractor_id: str) -> dict:
        """Cancel/delete an assignment."""
        assignment = db.query(JobAssignment).filter(JobAssignment.assignment_id == assignment_id).first()
        if not assignment:
            raise NotFoundException("Assignment", assignment_id)
        if assignment.contractor_id != contractor_id:
            raise ForbiddenException("Not your assignment")
        if assignment.status == "completed":
            raise BadRequestException("Cannot delete a completed assignment")

        assignment.status = "canceled"
        db.commit()
        return {"message": "Assignment canceled"}

    # ══════════════════════════════════════════
    # Technician-side assignment operations
    # ══════════════════════════════════════════

    @staticmethod
    def get_my_assignments(db: Session, technician_id: str) -> AssignmentListResponse:
        """Get assignments assigned to this technician."""
        assignments = (
            db.query(JobAssignment)
            .filter(
                JobAssignment.technician_id == technician_id,
                JobAssignment.status.notin_(["canceled"]),
            )
            .order_by(JobAssignment.created_at.desc())
            .all()
        )
        return AssignmentListResponse(
            assignments=[ContractorService._build_assignment_response(a, db) for a in assignments],
            total=len(assignments),
        )

    @staticmethod
    def assignment_on_the_way(db: Session, assignment_id: str, technician_id: str) -> AssignmentResponse:
        """Technician marks on the way."""
        assignment = db.query(JobAssignment).filter(JobAssignment.assignment_id == assignment_id).first()
        if not assignment:
            raise NotFoundException("Assignment", assignment_id)
        if assignment.technician_id != technician_id:
            raise ForbiddenException("Not your assignment")
        if assignment.status not in ("pending", "in_progress"):
            raise BadRequestException("Assignment must be pending or in_progress to mark on the way")

        assignment.status = "on_the_way"
        db.commit()
        db.refresh(assignment)
        return ContractorService._build_assignment_response(assignment, db)

    @staticmethod
    def assignment_start_work(db: Session, assignment_id: str, technician_id: str) -> AssignmentResponse:
        """Technician marks work started — records started_at timestamp."""
        assignment = db.query(JobAssignment).filter(JobAssignment.assignment_id == assignment_id).first()
        if not assignment:
            raise NotFoundException("Assignment", assignment_id)
        if assignment.technician_id != technician_id:
            raise ForbiddenException("Not your assignment")
        if assignment.status != "on_the_way":
            raise BadRequestException("Must be on the way before starting work")

        assignment.status = "work_started"
        assignment.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(assignment)
        return ContractorService._build_assignment_response(assignment, db)

    @staticmethod
    def assignment_complete(db: Session, assignment_id: str, technician_id: str) -> AssignmentResponse:
        """Technician marks done — records completed_at and computes duration_minutes."""
        assignment = db.query(JobAssignment).filter(JobAssignment.assignment_id == assignment_id).first()
        if not assignment:
            raise NotFoundException("Assignment", assignment_id)
        if assignment.technician_id != technician_id:
            raise ForbiddenException("Not your assignment")
        if assignment.status != "work_started":
            raise BadRequestException("Must have started work before completing")

        now = datetime.now(timezone.utc)
        assignment.status = "completed"
        assignment.completed_at = now

        # Auto-compute duration from started_at
        if assignment.started_at:
            delta = now - assignment.started_at
            assignment.duration_minutes = max(1, int(delta.total_seconds() / 60))
        else:
            assignment.duration_minutes = 0

        db.commit()
        db.refresh(assignment)
        return ContractorService._build_assignment_response(assignment, db)

    # ══════════════════════════════════════════
    # Tracking
    # ══════════════════════════════════════════

    @staticmethod
    def get_team_locations(db: Session, contractor_id: str) -> List[TechnicianLocationResponse]:
        """Get live GPS locations of all active team members with current assignments."""
        memberships = (
            db.query(ContractorGroup)
            .filter(
                ContractorGroup.contractor_id == contractor_id,
                ContractorGroup.status == "active",
            )
            .all()
        )

        results = []
        for m in memberships:
            tech = db.query(User).filter(User.user_id == m.technician_id).first()
            if not tech:
                continue

            # Find current active assignment (non-completed, non-canceled)
            current = (
                db.query(JobAssignment)
                .filter(
                    JobAssignment.contractor_id == contractor_id,
                    JobAssignment.technician_id == tech.user_id,
                    JobAssignment.status.in_(["pending", "in_progress", "on_the_way", "work_started"]),
                )
                .order_by(JobAssignment.created_at.desc())
                .first()
            )

            current_assignment = None
            if current:
                current_assignment = ContractorService._build_assignment_response(current, db)

            results.append(TechnicianLocationResponse(
                user_id=tech.user_id,
                name=tech.name,
                latitude=tech.latitude,
                longitude=tech.longitude,
                is_available=tech.is_available,
                profile_image_url=tech.profile_image_url,
                current_assignment=current_assignment,
            ))

        return results

    @staticmethod
    def get_member_location(db: Session, contractor_id: str, technician_id: str) -> TechnicianLocationResponse:
        """Get a single member's GPS + current assignment."""
        membership = (
            db.query(ContractorGroup)
            .filter(
                ContractorGroup.contractor_id == contractor_id,
                ContractorGroup.technician_id == technician_id,
                ContractorGroup.status == "active",
            )
            .first()
        )
        if not membership:
            raise NotFoundException("Team member", technician_id)

        tech = db.query(User).filter(User.user_id == technician_id).first()
        if not tech:
            raise NotFoundException("User", technician_id)

        current = (
            db.query(JobAssignment)
            .filter(
                JobAssignment.contractor_id == contractor_id,
                JobAssignment.technician_id == technician_id,
                JobAssignment.status.in_(["pending", "in_progress", "on_the_way", "work_started"]),
            )
            .order_by(JobAssignment.created_at.desc())
            .first()
        )

        current_assignment = None
        if current:
            current_assignment = ContractorService._build_assignment_response(current, db)

        return TechnicianLocationResponse(
            user_id=tech.user_id,
            name=tech.name,
            latitude=tech.latitude,
            longitude=tech.longitude,
            is_available=tech.is_available,
            profile_image_url=tech.profile_image_url,
            current_assignment=current_assignment,
        )
