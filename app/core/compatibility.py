"""Blood compatibility engine — pure, tested, no surprises.

ABO/Rh compatibility rules encoded as explicit maps so the logic is
readable and unit-testable. A donor can give to a patient when the
donor's group is in COMPATIBLE_DONORS_FOR[patient_group].
"""

from __future__ import annotations

from datetime import date

from app.config import get_settings

BLOOD_GROUPS: list[str] = [
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-",
]

# Donor group -> patient groups that can receive from this donor.
CAN_DONATE_TO: dict[str, set[str]] = {
    "O-": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
    "O+": {"O+", "A+", "B+", "AB+"},
    "A-": {"A-", "A+", "AB-", "AB+"},
    "A+": {"A+", "AB+"},
    "B-": {"B-", "B+", "AB-", "AB+"},
    "B+": {"B+", "AB+"},
    "AB-": {"AB-", "AB+"},
    "AB+": {"AB+"},
}

# Patient group -> donor groups that can donate to this patient.
COMPATIBLE_DONORS_FOR: dict[str, set[str]] = {
    patient: {donor for donor, patients in CAN_DONATE_TO.items() if patient in patients}
    for patient in BLOOD_GROUPS
}

# Universal facts used by the UI/guide.
UNIVERSAL_DONOR = "O-"
UNIVERSAL_RECIPIENT = "AB+"


def is_valid_blood_group(group: str) -> bool:
    """Return True if the string is a valid blood group."""
    return group in BLOOD_GROUPS


def compatible_donors_for(patient_group: str) -> list[str]:
    """Return donor blood groups that can donate to a patient group."""
    if not is_valid_blood_group(patient_group):
        return []
    return sorted(COMPATIBLE_DONORS_FOR[patient_group])


def can_donate_to(donor_group: str, patient_group: str) -> bool:
    """Return True if donor_group can donate to patient_group."""
    if not is_valid_blood_group(donor_group) or not is_valid_blood_group(patient_group):
        return False
    return patient_group in CAN_DONATE_TO[donor_group]


def age_from_birth_year(birth_year: int) -> int:
    """Compute age as of today from a birth year."""
    return date.today().year - birth_year


def is_eligible_donor(
    birth_year: int | None,
    weight_kg: int | None,
    last_donation_date: date | None,
    is_available: bool,
    settings=None,
) -> tuple[bool, list[str]]:
    """Check donor eligibility against the configured rules.

    Returns (eligible, list_of_reasons) — reasons empty when eligible.
    """
    s = settings or get_settings()
    reasons: list[str] = []

    if birth_year is None:
        reasons.append("Date of birth not provided")
    else:
        age = age_from_birth_year(birth_year)
        if age < s.min_age:
            reasons.append(f"Donor is under {s.min_age} ({age})")
        if age > s.max_age:
            reasons.append(f"Donor is over {s.max_age} ({age})")

    if weight_kg is None:
        reasons.append("Weight not provided")
    elif weight_kg < s.min_weight_kg:
        reasons.append(f"Donor is under {s.min_weight_kg} kg ({weight_kg})")

    if last_donation_date is not None:
        days_since = (date.today() - last_donation_date).days
        if days_since < s.donation_cooldown_days:
            reasons.append(
                f"Donated {days_since} days ago — {s.donation_cooldown_days}-day cooldown"
            )

    if not is_available:
        reasons.append("Donor is not currently available")

    return (len(reasons) == 0, reasons)


def expiry_hours_for_urgency(urgency: str, settings=None) -> int:
    """Return request expiry window in hours for an urgency level."""
    s = settings or get_settings()
    return {
        "normal": s.expiry_normal_hours,
        "urgent": s.expiry_urgent_hours,
        "emergency": s.expiry_emergency_hours,
    }.get(urgency, s.expiry_normal_hours)
