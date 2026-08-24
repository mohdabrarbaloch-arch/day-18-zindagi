"""Admin router — stats, verification, donor management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import BloodRequest, DonationEvent, DonorProfile, User
from app.schemas import AdminStats, DonorProfileOut

router = APIRouter(prefix="/api/admin", tags=["admin"])

admin_only = require_roles("admin")


@router.get("/stats", response_model=AdminStats)
def stats(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """Aggregate platform stats for the admin dashboard."""
    donors = db.query(DonorProfile).count()
    available = db.query(DonorProfile).filter(DonorProfile.is_available.is_(True)).count()
    verified = db.query(DonorProfile).filter(DonorProfile.is_verified.is_(True)).count()
    open_reqs = db.query(BloodRequest).filter(BloodRequest.status == "open").count()
    fulfilled = db.query(BloodRequest).filter(BloodRequest.status == "fulfilled").count()
    donations = db.query(DonationEvent).count()
    return AdminStats(
        donors=donors,
        available_donors=available,
        verified_donors=verified,
        open_requests=open_reqs,
        fulfilled_requests=fulfilled,
        total_donations=donations,
    )


@router.post("/donors/{user_id}/verify", response_model=DonorProfileOut)
def verify_donor(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    """Mark a donor profile as verified (admin only)."""
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user_id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")
    profile.is_verified = True
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/donors", response_model=list[DonorProfileOut])
def list_donors(
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    """List all donor profiles (admin)."""
    return db.query(DonorProfile).order_by(DonorProfile.created_at.desc()).limit(200).all()
