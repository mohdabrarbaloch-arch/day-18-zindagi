"""Seed the database with demo users, donors and requests.

Run: python -m scripts.seed
"""

import sys
from datetime import UTC, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.compatibility import BLOOD_GROUPS
from app.database import Base, SessionLocal, engine
from app.models import BloodRequest, DonorProfile, User
from app.security import hash_password

CITIES = ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad"]
AREAS = {
    "Karachi": ["Gulshan-e-Iqbal", "Clifton", "Saddar", "North Nazimabad", "Malir"],
    "Lahore": ["Gulberg", "DHA", "Johar Town", "Model Town", "Wapda Town"],
    "Islamabad": ["F-8", "G-10", "I-8", "E-11", "F-11"],
    "Rawalpindi": ["Saddar", "Bahria Town", "Satellite Town", "Gulraiz"],
    "Faisalabad": ["Peoples Colony", "Jaranwala Road", "D Ground", "Madina Town"],
}
HOSPITALS = [
    "Aga Khan University Hospital",
    "Liaquat National Hospital",
    "Shaukat Khanum Memorial",
    "Jinnah Hospital",
    "Pakistan Institute of Medical Sciences",
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(User).count() > 0:
        print("DB already seeded — skipping.")
        db.close()
        return

    # Admin
    admin = User(
        email="admin@zindagi.pk",
        password_hash=hash_password("admin12345"),
        full_name="Zindagi Admin",
        phone="0300-0000000",
        role="admin",
    )
    db.add(admin)

    # Donors — one per blood group across cities
    donors: list[DonorProfile] = []
    for i, bg in enumerate(BLOOD_GROUPS):
        city = CITIES[i % len(CITIES)]
        area = AREAS[city][i % len(AREAS[city])]
        user = User(
            email=f"donor{i + 1}@zindagi.pk",
            password_hash=hash_password("donor12345"),
            full_name=f"Donor {bg}",
            phone=f"0311-{1000000 + i * 11111:07d}",
            role="donor",
        )
        db.add(user)
        db.flush()
        profile = DonorProfile(
            user_id=user.id,
            blood_group=bg,
            city=city,
            area=area,
            birth_year=1992 + (i % 15),
            weight_kg=65 + (i % 20),
            last_donation_date=date.today() - timedelta(days=100 + i * 5),
            is_available=True,
            is_verified=(i % 3 == 0),
            donation_count=i % 5,
        )
        db.add(profile)
        donors.append(profile)

    # Requester
    requester = User(
        email="requester@zindagi.pk",
        password_hash=hash_password("requester12345"),
        full_name="Ahmed Family",
        phone="0321-1234567",
        role="requester",
    )
    db.add(requester)
    db.flush()

    # Two open requests
    from datetime import datetime

    req1 = BloodRequest(
        requester_id=requester.id,
        patient_name="Fatima Ahmed",
        blood_group="O-",
        units_needed=2,
        hospital=HOSPITALS[0],
        city="Karachi",
        area="Clifton",
        urgency="emergency",
        notes="Accident victim at AKUH, need O- urgently.",
        expires_at=datetime.now(UTC) + timedelta(hours=6),
    )
    req2 = BloodRequest(
        requester_id=requester.id,
        patient_name="Bilal Ahmed",
        blood_group="B+",
        units_needed=1,
        hospital=HOSPITALS[2],
        city="Lahore",
        area="Gulberg",
        urgency="urgent",
        notes="Surgery scheduled tomorrow morning.",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add_all([req1, req2])
    db.commit()
    db.close()

    print(f"Seeded: 1 admin, {len(donors)} donors, 1 requester, 2 open requests.")


if __name__ == "__main__":
    seed()
