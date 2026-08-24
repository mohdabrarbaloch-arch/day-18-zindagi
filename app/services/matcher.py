"""Matcher service — finds compatible, eligible, available donors."""

from datetime import date, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.compatibility import (
    COMPATIBLE_DONORS_FOR,
    age_from_birth_year,
    can_donate_to,
    is_valid_blood_group,
)
from app.models import DonorProfile, User


def find_matching_donors(
    db: Session, blood_group: str, city: str | None = None
) -> list[DonorProfile]:
    """Return compatible + eligible + available donors, best match first.

    Sorting: verified donors first, then same-city, then most recent
    availability. The engine is pure SQL + in-Python eligibility so the
    rules stay testable.
    """
    settings = get_settings()
    if not is_valid_blood_group(blood_group):
        return []

    donor_groups = COMPATIBLE_DONORS_FOR[blood_group]
    cooldown_cutoff = date.today() - timedelta(days=settings.donation_cooldown_days)
    min_age_cutoff = date.today().year - settings.max_age
    max_age_cutoff = date.today().year - settings.min_age

    query = (
        db.query(DonorProfile)
        .join(User, DonorProfile.user_id == User.id)
        .filter(
            DonorProfile.blood_group.in_(donor_groups),
            DonorProfile.is_available.is_(True),
            DonorProfile.birth_year >= min_age_cutoff,
            DonorProfile.birth_year <= max_age_cutoff,
            DonorProfile.weight_kg >= settings.min_weight_kg,
            or_(
                DonorProfile.last_donation_date.is_(None),
                DonorProfile.last_donation_date <= cooldown_cutoff,
            ),
        )
    )

    # City priority handled in Python so we can keep ordering stable.
    donors = query.all()
    donors.sort(
        key=lambda d: (
            not d.is_verified,  # verified first
            d.city != (city or ""),  # same city first
            d.last_donation_date is not None,  # longest-cooldown donors first
        )
    )
    return donors


def donor_match_payload(donor: DonorProfile) -> dict:
    """Serialize a matched donor for the API response."""
    return {
        "donor_id": donor.user_id,
        "name": donor.user.full_name,
        "phone": donor.user.phone,
        "blood_group": donor.blood_group,
        "city": donor.city,
        "area": donor.area,
        "is_verified": donor.is_verified,
        "donation_count": donor.donation_count,
        "last_donation_date": donor.last_donation_date,
        "age": age_from_birth_year(donor.birth_year),
    }


def is_compatible(donor_group: str, patient_group: str) -> bool:
    """Expose the engine check for the public guide endpoint."""
    return can_donate_to(donor_group, patient_group)
