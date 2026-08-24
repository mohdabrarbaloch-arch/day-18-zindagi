"""Blood request router — create, list, match, fulfill, cancel."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.compatibility import can_donate_to, expiry_hours_for_urgency
from app.database import get_db
from app.deps import get_current_user
from app.models import BloodRequest, DonationEvent, DonorProfile, User
from app.schemas import (
    BloodRequestIn,
    BloodRequestOut,
    DonorMatchOut,
    FulfillIn,
)
from app.services.matcher import donor_match_payload, find_matching_donors

router = APIRouter(prefix="/api/requests", tags=["requests"])

REQUEST_STATUSES = {"open", "fulfilled", "cancelled", "expired"}


def _get_request_or_404(request_id: int, db: Session) -> BloodRequest:
    req = db.get(BloodRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return req


def _serialize(req: BloodRequest) -> dict:
    data = BloodRequestOut.model_validate(req).model_dump()
    data["requester_name"] = req.requester.full_name if req.requester else None
    return data


def _apply_expiry(req: BloodRequest, db: Session) -> BloodRequest:
    """Mark an open request expired if past its window (lazy expiry)."""
    if req.status == "open" and req.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        req.status = "expired"
        db.commit()
        db.refresh(req)
    return req


@router.post("", response_model=BloodRequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: BloodRequestIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Post a new blood request with urgency-based expiry."""
    hours = expiry_hours_for_urgency(payload.urgency)
    req = BloodRequest(
        requester_id=user.id,
        patient_name=payload.patient_name.strip(),
        blood_group=payload.blood_group,
        units_needed=payload.units_needed,
        hospital=payload.hospital.strip(),
        city=payload.city.strip(),
        area=payload.area.strip(),
        urgency=payload.urgency,
        notes=payload.notes.strip() if payload.notes else None,
        expires_at=datetime.now(UTC) + timedelta(hours=hours),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _serialize(req)


@router.get("", response_model=list[BloodRequestOut])
def list_requests(
    status_filter: str | None = None,
    blood_group: str | None = None,
    city: str | None = None,
    db: Session = Depends(get_db),
):
    """List requests (optionally filtered), auto-expiring stale ones."""
    query = db.query(BloodRequest)
    if status_filter:
        query = query.filter(BloodRequest.status == status_filter)
    if blood_group:
        query = query.filter(BloodRequest.blood_group == blood_group.upper())
    if city:
        query = query.filter(BloodRequest.city.ilike(f"%{city}%"))

    requests = query.order_by(BloodRequest.created_at.desc()).limit(100).all()
    for req in requests:
        _apply_expiry(req, db)
    return [_serialize(req) for req in requests]


@router.get("/my")
def my_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List the authenticated user's requests."""
    requests = (
        db.query(BloodRequest)
        .filter(BloodRequest.requester_id == user.id)
        .order_by(BloodRequest.created_at.desc())
        .all()
    )
    return [_serialize(req) for req in requests]


@router.get("/{request_id}", response_model=BloodRequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    """Fetch a single request."""
    req = _get_request_or_404(request_id, db)
    req = _apply_expiry(req, db)
    return _serialize(req)


@router.get("/{request_id}/matches", response_model=list[DonorMatchOut])
def get_matches(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find compatible, eligible, available donors for a request."""
    req = _get_request_or_404(request_id, db)
    req = _apply_expiry(req, db)
    if req.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is {req.status} — only open requests can be matched",
        )
    donors = find_matching_donors(db, req.blood_group, req.city)
    return [donor_match_payload(d) for d in donors]


@router.post("/{request_id}/fulfill", response_model=BloodRequestOut)
def fulfill_request(
    request_id: int,
    payload: FulfillIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a request fulfilled by a donor; record the donation event."""
    req = _get_request_or_404(request_id, db)
    if req.requester_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can fulfill this request",
        )
    req = _apply_expiry(req, db)
    if req.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is {req.status} — only open requests can be fulfilled",
        )

    donor = db.query(DonorProfile).filter(DonorProfile.user_id == payload.donor_id).first()
    if donor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")
    if not can_donate_to(donor.blood_group, req.blood_group):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Donor {donor.blood_group} is not compatible with {req.blood_group}",
        )

    req.status = "fulfilled"
    req.fulfilled_at = datetime.now(UTC)
    event = DonationEvent(
        request_id=req.id,
        donor_id=donor.user_id,
        blood_group=donor.blood_group,
        units=payload.units,
    )
    donor.last_donation_date = datetime.now(UTC).date()
    donor.donation_count += 1
    donor.is_available = False  # cooldown — auto-mark unavailable
    db.add(event)
    db.commit()
    db.refresh(req)
    return _serialize(req)


@router.post("/{request_id}/cancel", response_model=BloodRequestOut)
def cancel_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an open request (requester or admin only)."""
    req = _get_request_or_404(request_id, db)
    if req.requester_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can cancel this request",
        )
    if req.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel a {req.status} request",
        )
    req.status = "cancelled"
    db.commit()
    db.refresh(req)
    return _serialize(req)
