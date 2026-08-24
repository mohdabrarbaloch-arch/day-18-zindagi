"""Donor router — profile management and availability."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.compatibility import is_eligible_donor
from app.database import get_db
from app.deps import get_current_user
from app.models import DonorProfile, User
from app.schemas import DonorAvailabilityIn, DonorProfileIn, DonorProfileOut

router = APIRouter(prefix="/api/donors", tags=["donors"])


def _get_own_profile(user: User, db: Session) -> DonorProfile:
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor profile not found")
    return profile


@router.put("/profile", response_model=DonorProfileOut)
def upsert_profile(
    payload: DonorProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update the authenticated user's donor profile."""
    if user.role not in {"donor", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only donors can create donor profiles",
        )

    eligible, reasons = is_eligible_donor(payload.birth_year, payload.weight_kg, None, True)
    if not eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Donor not eligible: " + "; ".join(reasons),
        )

    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if profile is None:
        profile = DonorProfile(user_id=user.id, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile", response_model=DonorProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch the authenticated user's donor profile."""
    return _get_own_profile(user, db)


@router.patch("/availability", response_model=DonorProfileOut)
def set_availability(
    payload: DonorAvailabilityIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggle the donor's availability (on/off duty)."""
    profile = _get_own_profile(user, db)
    profile.is_available = payload.is_available
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{user_id}", response_model=DonorProfileOut)
def get_public_profile(user_id: int, db: Session = Depends(get_db)):
    """Fetch any donor profile (public read)."""
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user_id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")
    return profile
