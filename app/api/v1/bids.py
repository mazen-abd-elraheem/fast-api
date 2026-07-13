"""
Sanaie Platform — Bid Routes
Bid submission, acceptance, rejection, and withdrawal.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_role, handle_service_exception
from app.models.user import User
from app.enums import UserRole
from app.schemas.bid import BidCreate, BidResponse, BidListResponse, BidCounterOffer
from app.services.bid_service import BidService
from app.core.exceptions import SanaieException

router = APIRouter()


@router.post(
    "/",
    response_model=BidResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a bid (Worker only)",
)
def submit_bid(
    bid_data: BidCreate,
    current_user: User = Depends(require_role(UserRole.WORKER)),
    db: Session = Depends(get_db),
):
    """
    Worker submits a bid on an open job.

    - Only **workers** can submit bids.
    - One bid per worker per job (enforced).
    - Include an optional `message` with your proposal.
    """
    try:
        return BidService.submit_bid(db, bid_data, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.get(
    "/job/{job_id}",
    response_model=BidListResponse,
    summary="List bids for a job",
)
def get_bids_for_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all bids submitted for a specific job, sorted by lowest amount."""
    return BidService.get_bids_for_job(db, job_id)


@router.put(
    "/{bid_id}/accept",
    response_model=BidResponse,
    summary="Accept a bid (Client only)",
)
def accept_bid(
    bid_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Client accepts a bid:
    1. The accepted bid status becomes **accepted**
    2. All other pending bids are **rejected**
    3. The job status becomes **in_progress**
    4. The worker is assigned to the job
    """
    try:
        return BidService.accept_bid(db, bid_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{bid_id}/reject",
    response_model=BidResponse,
    summary="Reject a bid (Client only)",
)
def reject_bid(
    bid_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Client rejects a specific bid. Only works on pending bids."""
    try:
        return BidService.reject_bid(db, bid_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{bid_id}/withdraw",
    response_model=BidResponse,
    summary="Withdraw a bid (Worker only)",
)
def withdraw_bid(
    bid_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Worker withdraws their own bid. Only works on pending bids."""
    try:
        return BidService.withdraw_bid(db, bid_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{bid_id}/counter",
    response_model=BidResponse,
    summary="Counter-offer on a bid (Client only)",
)
def counter_offer_bid(
    bid_id: str,
    data: BidCounterOffer,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Client sends a counter-offer on a technician's bid.
    The bid status changes to **counter_offered** and the technician
    can accept or reject the counter.
    """
    try:
        return BidService.counter_offer(db, bid_id, current_user.user_id, data.counter_amount)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{bid_id}/accept-counter",
    response_model=BidResponse,
    summary="Accept counter-offer (Worker only)",
)
def accept_counter_offer(
    bid_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Technician accepts the client's counter-offer:
    1. Bid amount is replaced with counter_amount
    2. Bid status becomes **accepted**
    3. Job is assigned to the technician
    """
    try:
        return BidService.accept_counter_offer(db, bid_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.put(
    "/{bid_id}/reject-counter",
    response_model=BidResponse,
    summary="Reject counter-offer (Worker only)",
)
def reject_counter_offer(
    bid_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Technician rejects the client's counter-offer. Bid returns to pending."""
    try:
        return BidService.reject_counter_offer(db, bid_id, current_user.user_id)
    except SanaieException as e:
        handle_service_exception(e)


@router.get(
    "/my",
    response_model=BidListResponse,
    summary="My bids as worker",
)
def get_my_bids(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all bids submitted by the authenticated worker."""
    return BidService.get_my_bids(db, current_user.user_id)

