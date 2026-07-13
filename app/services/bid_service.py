"""
Sanaie Platform — Bid Service
Bidding engine — submit, accept, reject, withdraw bids.
Uses domain exceptions and fixes N+1 queries.
"""
import uuid
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.bid import Bid
from app.models.job import Job
from app.models.user import User
from app.models.review import Review
from app.enums import BidStatus, JobStatus
from app.schemas.bid import BidCreate, BidResponse, BidListResponse, BidCounterOffer
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    DuplicateException,
)
from app.api.v1.notifications import create_notification

log = logging.getLogger(__name__)


class BidService:
    """Bidding engine — submit, accept, reject, withdraw bids."""

    @staticmethod
    def _build_response(bid: Bid, db: Session) -> BidResponse:
        """Build a BidResponse with worker name and avg rating."""
        worker = db.query(User).filter(User.user_id == bid.worker_id).first()
        avg_rating = (
            db.query(func.avg(Review.rating_score))
            .filter(Review.worker_id == bid.worker_id)
            .scalar()
        )

        return BidResponse(
            bid_id=bid.bid_id,
            job_id=bid.job_id,
            worker_id=bid.worker_id,
            worker_name=worker.name if worker else None,
            worker_avg_rating=round(float(avg_rating), 2) if avg_rating else None,
            amount=float(bid.amount),
            message=bid.message,
            counter_amount=float(bid.counter_amount) if bid.counter_amount else None,
            status=bid.status.lower() if bid.status else "pending",
            scheduled_at=bid.scheduled_at,
            created_at=bid.created_at,
        )

    @staticmethod
    def _build_list_response(bids: list, db: Session) -> BidListResponse:
        """Build list response with batch-loaded ratings (fixes N+1)."""
        if not bids:
            return BidListResponse(bids=[], total=0)

        # Batch-load worker names and ratings
        worker_ids = list(set(b.worker_id for b in bids))
        workers = {
            u.user_id: u.name
            for u in db.query(User.user_id, User.name).filter(User.user_id.in_(worker_ids)).all()
        }
        ratings = {}
        rating_data = (
            db.query(
                Review.worker_id,
                func.avg(Review.rating_score).label("avg"),
            )
            .filter(Review.worker_id.in_(worker_ids))
            .group_by(Review.worker_id)
            .all()
        )
        for r in rating_data:
            ratings[r.worker_id] = round(float(r.avg), 2)

        bid_responses = []
        for bid in bids:
            bid_responses.append(BidResponse(
                bid_id=bid.bid_id,
                job_id=bid.job_id,
                worker_id=bid.worker_id,
                worker_name=workers.get(bid.worker_id),
                worker_avg_rating=ratings.get(bid.worker_id),
                amount=float(bid.amount),
                message=bid.message,
                counter_amount=float(bid.counter_amount) if bid.counter_amount else None,
                status=bid.status.lower() if bid.status else "pending",
                scheduled_at=bid.scheduled_at,
                created_at=bid.created_at,
            ))

        return BidListResponse(bids=bid_responses, total=len(bid_responses))

    @staticmethod
    def submit_bid(db: Session, bid_data: BidCreate, worker_id: str) -> BidResponse:
        """Worker submits a bid on an open job."""
        job = db.query(Job).filter(Job.job_id == bid_data.job_id).first()
        if not job:
            raise NotFoundException("Job", bid_data.job_id)
        if job.status != JobStatus.OPEN.value:
            raise BadRequestException("Can only bid on open jobs")
        if job.client_id == worker_id:
            raise BadRequestException("Cannot bid on your own job")

        # Auto-withdraw any existing pending/counter-offered bid from the same worker
        existing = (
            db.query(Bid)
            .filter(
                Bid.job_id == bid_data.job_id,
                Bid.worker_id == worker_id,
                Bid.status.in_([BidStatus.PENDING.value, BidStatus.COUNTER_OFFERED.value]),
            )
            .first()
        )
        if existing:
            existing.status = BidStatus.WITHDRAWN.value
            log.info("Auto-withdrew previous bid %s (was %s) for worker %s",
                     existing.bid_id, existing.amount, worker_id)

        db_bid = Bid(
            bid_id=str(uuid.uuid4()),
            job_id=bid_data.job_id,
            worker_id=worker_id,
            amount=bid_data.amount,
            message=bid_data.message,
            scheduled_at=bid_data.scheduled_at,
            status=BidStatus.PENDING.value,
        )

        db.add(db_bid)

        # Notify the client that a new bid was received
        worker = db.query(User).filter(User.user_id == worker_id).first()
        worker_name = worker.name if worker else "A technician"
        create_notification(
            db, user_id=job.client_id,
            notif_type="bid_received",
            title="New Bid Received",
            message=f"{worker_name} submitted a bid of EGP {bid_data.amount:,.0f} on \"{job.title}\"",
            reference_id=job.job_id, reference_type="job",
        )

        db.commit()
        db.refresh(db_bid)

        return BidService._build_response(db_bid, db)

    @staticmethod
    def get_bids_for_job(db: Session, job_id: str) -> BidListResponse:
        """Get all bids for a specific job."""
        bids = (
            db.query(Bid)
            .filter(Bid.job_id == job_id)
            .order_by(Bid.amount.asc())
            .all()
        )
        return BidService._build_list_response(bids, db)

    @staticmethod
    def accept_bid(db: Session, bid_id: str, client_id: str) -> BidResponse:
        """
        Client accepts a bid:
        1. Set bid status to ACCEPTED
        2. Reject all other PENDING bids for the same job
        3. Set job status to IN_PROGRESS
        4. Assign the worker to the job
        5. Auto-create a chat conversation between client and worker
        """
        bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
        if not bid:
            raise NotFoundException("Bid", bid_id)

        job = db.query(Job).filter(Job.job_id == bid.job_id).first()
        if not job:
            raise NotFoundException("Job", bid.job_id)
        if job.client_id != client_id:
            raise ForbiddenException("Not the job owner")
        if job.status != JobStatus.OPEN.value:
            raise BadRequestException("Job is no longer open")

        # Accept this bid
        bid.status = BidStatus.ACCEPTED.value

        # Reject all other pending bids for this job
        db.query(Bid).filter(
            Bid.job_id == bid.job_id,
            Bid.bid_id != bid_id,
            Bid.status == BidStatus.PENDING.value,
        ).update({"status": BidStatus.REJECTED.value})

        # Update job: assign worker & set status
        job.status = JobStatus.IN_PROGRESS.value
        job.assigned_worker_id = bid.worker_id

        # Auto-create conversation between client and worker
        BidService._create_job_conversation(db, job, client_id, bid.worker_id)

        # Notify the technician that their bid was accepted
        create_notification(
            db, user_id=bid.worker_id,
            notif_type="bid_accepted",
            title="Bid Accepted! 🎉",
            message=f"Your bid of EGP {float(bid.amount):,.0f} on \"{job.title}\" has been accepted!",
            reference_id=job.job_id, reference_type="job",
        )

        db.commit()
        db.refresh(bid)

        return BidService._build_response(bid, db)

    @staticmethod
    def _create_job_conversation(db: Session, job: Job, client_id: str, worker_id: str):
        """Create a chat conversation linked to the job when bid is accepted."""
        import uuid
        from datetime import datetime, timezone
        from sqlalchemy import or_, and_
        from app.models.conversation import Conversation, Message

        # Check if a conversation already exists for this job
        existing = db.query(Conversation).filter(
            Conversation.job_id == job.job_id,
            or_(
                and_(
                    Conversation.participant_1_id == client_id,
                    Conversation.participant_2_id == worker_id,
                ),
                and_(
                    Conversation.participant_1_id == worker_id,
                    Conversation.participant_2_id == client_id,
                ),
            ),
        ).first()

        if existing:
            return existing

        now = datetime.now(timezone.utc)
        conv = Conversation(
            conversation_id=str(uuid.uuid4()),
            participant_1_id=client_id,
            participant_2_id=worker_id,
            job_id=job.job_id,
            last_message_text=f"Bid accepted for: {job.title}",
            last_message_at=now,
        )
        db.add(conv)
        db.flush()

        # Auto-send a welcome message
        msg = Message(
            message_id=str(uuid.uuid4()),
            conversation_id=conv.conversation_id,
            sender_id=client_id,
            content=f"Hi! I've accepted your bid for \"{job.title}\". Let's discuss the details!",
            is_read=False,
            created_at=now,
        )
        db.add(msg)

        return conv

    @staticmethod
    def reject_bid(db: Session, bid_id: str, client_id: str) -> BidResponse:
        """Client rejects a specific bid."""
        bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
        if not bid:
            raise NotFoundException("Bid", bid_id)

        job = db.query(Job).filter(Job.job_id == bid.job_id).first()
        if not job or job.client_id != client_id:
            raise ForbiddenException("Not the job owner")
        if bid.status != BidStatus.PENDING.value:
            raise BadRequestException("Can only reject pending bids")

        bid.status = BidStatus.REJECTED.value

        # Notify the technician that their bid was rejected
        create_notification(
            db, user_id=bid.worker_id,
            notif_type="bid_rejected",
            title="Bid Rejected",
            message=f"Your bid on \"{job.title}\" has been rejected by the client.",
            reference_id=job.job_id, reference_type="job",
        )

        db.commit()
        db.refresh(bid)

        return BidService._build_response(bid, db)

    @staticmethod
    def withdraw_bid(db: Session, bid_id: str, worker_id: str) -> BidResponse:
        """Worker withdraws their own bid."""
        bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
        if not bid:
            raise NotFoundException("Bid", bid_id)
        if bid.worker_id != worker_id:
            raise ForbiddenException("Not your bid")
        if bid.status != BidStatus.PENDING.value:
            raise BadRequestException("Can only withdraw pending bids")

        bid.status = BidStatus.WITHDRAWN.value
        db.commit()
        db.refresh(bid)

        return BidService._build_response(bid, db)

    @staticmethod
    def get_my_bids(db: Session, worker_id: str) -> BidListResponse:
        """Get all bids submitted by a worker."""
        bids = (
            db.query(Bid)
            .filter(Bid.worker_id == worker_id)
            .order_by(Bid.created_at.desc())
            .all()
        )
        return BidService._build_list_response(bids, db)

    @staticmethod
    def counter_offer(db: Session, bid_id: str, client_id: str, counter_amount: float) -> BidResponse:
        """Client sends a counter-offer amount on a specific bid."""
        bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
        if not bid:
            raise NotFoundException("Bid", bid_id)

        job = db.query(Job).filter(Job.job_id == bid.job_id).first()
        if not job or job.client_id != client_id:
            raise ForbiddenException("Not the job owner")
        if bid.status not in (BidStatus.PENDING.value, BidStatus.COUNTER_OFFERED.value):
            raise BadRequestException("Can only counter-offer on pending or counter-offered bids")

        bid.counter_amount = counter_amount
        bid.status = BidStatus.COUNTER_OFFERED.value

        # Notify the technician about the counter-offer
        create_notification(
            db, user_id=bid.worker_id,
            notif_type="counter_offer",
            title="Counter-Offer Received",
            message=f"The client sent a counter-offer of EGP {counter_amount:,.0f} on \"{job.title}\"",
            reference_id=bid.bid_id, reference_type="bid",
        )

        db.commit()
        db.refresh(bid)

        return BidService._build_response(bid, db)

    @staticmethod
    def accept_counter_offer(db: Session, bid_id: str, worker_id: str) -> BidResponse:
        """
        Technician accepts the client's counter-offer:
        1. Replace the bid amount with counter_amount
        2. Set bid status to ACCEPTED
        3. Reject all other pending bids for the same job
        4. Set job status to IN_PROGRESS
        5. Assign the worker to the job
        """
        bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
        if not bid:
            raise NotFoundException("Bid", bid_id)
        if bid.worker_id != worker_id:
            raise ForbiddenException("Not your bid")
        if bid.status != BidStatus.COUNTER_OFFERED.value:
            raise BadRequestException("No counter-offer to accept")
        if not bid.counter_amount:
            raise BadRequestException("No counter amount set")

        job = db.query(Job).filter(Job.job_id == bid.job_id).first()
        if not job:
            raise NotFoundException("Job", bid.job_id)
        if job.status != JobStatus.OPEN.value:
            raise BadRequestException("Job is no longer open")

        # Accept with the counter amount
        bid.amount = bid.counter_amount
        bid.counter_amount = None
        bid.status = BidStatus.ACCEPTED.value

        # Reject all other pending/counter bids
        db.query(Bid).filter(
            Bid.job_id == bid.job_id,
            Bid.bid_id != bid_id,
            Bid.status.in_([BidStatus.PENDING.value, BidStatus.COUNTER_OFFERED.value]),
        ).update({"status": BidStatus.REJECTED.value}, synchronize_session="fetch")

        # Update job: assign worker & set status
        job.status = JobStatus.IN_PROGRESS.value
        job.assigned_worker_id = bid.worker_id

        # Auto-create conversation
        BidService._create_job_conversation(db, job, job.client_id, bid.worker_id)

        # Notify the client that the technician accepted their counter-offer
        worker = db.query(User).filter(User.user_id == bid.worker_id).first()
        worker_name = worker.name if worker else "The technician"
        create_notification(
            db, user_id=job.client_id,
            notif_type="counter_accepted",
            title="Counter-Offer Accepted! 🎉",
            message=f"{worker_name} accepted your counter-offer of EGP {float(bid.amount):,.0f} on \"{job.title}\"",
            reference_id=job.job_id, reference_type="job",
        )

        db.commit()
        db.refresh(bid)

        return BidService._build_response(bid, db)

    @staticmethod
    def reject_counter_offer(db: Session, bid_id: str, worker_id: str) -> BidResponse:
        """Technician rejects the client's counter-offer. Bid returns to pending with original amount."""
        bid = db.query(Bid).filter(Bid.bid_id == bid_id).first()
        if not bid:
            raise NotFoundException("Bid", bid_id)
        if bid.worker_id != worker_id:
            raise ForbiddenException("Not your bid")
        if bid.status != BidStatus.COUNTER_OFFERED.value:
            raise BadRequestException("No counter-offer to reject")

        bid.counter_amount = None
        bid.status = BidStatus.PENDING.value

        # Notify the client that the technician rejected their counter-offer
        job = db.query(Job).filter(Job.job_id == bid.job_id).first()
        job_title = job.title if job else "a job"
        worker = db.query(User).filter(User.user_id == bid.worker_id).first()
        worker_name = worker.name if worker else "The technician"
        create_notification(
            db, user_id=job.client_id if job else "",
            notif_type="counter_rejected",
            title="Counter-Offer Declined",
            message=f"{worker_name} declined your counter-offer on \"{job_title}\". The original bid is still active.",
            reference_id=job.job_id if job else "", reference_type="job",
        )

        db.commit()
        db.refresh(bid)

        return BidService._build_response(bid, db)
