"""End-to-end API tests using a temporary SQLite database."""

import os
import tempfile

# Must be set before app imports.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from datetime import UTC  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def _register_donor(email="donor@test.pk", name="Ali Donor", password="password123"):
    r = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": name,
            "phone": "0311-1234567",
            "role": "donor",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _register_requester(email="req@test.pk"):
    r = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Ahmed Family",
            "phone": "0321-7654321",
            "role": "requester",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_profile(token, **overrides):
    body = {
        "blood_group": "O-",
        "city": "Karachi",
        "area": "Clifton",
        "birth_year": 1995,
        "weight_kg": 70,
        "is_available": True,
    }
    body.update(overrides)
    r = client.put("/api/donors/profile", json=body, headers=_auth_header(token))
    assert r.status_code == 200, r.text
    return r.json()


class TestAuth:
    def test_register_returns_token(self):
        data = _register_donor()
        assert data["token_type"] == "bearer"
        assert data["role"] == "donor"
        assert data["user_id"] > 0

    def test_duplicate_email_rejected(self):
        _register_donor()
        r = client.post(
            "/api/auth/register",
            json={
                "email": "donor@test.pk",
                "password": "password123",
                "full_name": "Dup",
                "phone": "0311-0000000",
                "role": "donor",
            },
        )
        assert r.status_code == 409

    def test_login_roundtrip(self):
        _register_donor()
        r = client.post(
            "/api/auth/login", json={"email": "donor@test.pk", "password": "password123"}
        )
        assert r.status_code == 200
        assert r.json()["access_token"]

    def test_login_wrong_password(self):
        _register_donor()
        r = client.post("/api/auth/login", json={"email": "donor@test.pk", "password": "wrongpass"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_returns_user(self):
        data = _register_donor()
        r = client.get("/api/auth/me", headers=_auth_header(data["access_token"]))
        assert r.status_code == 200
        assert r.json()["email"] == "donor@test.pk"


class TestDonorProfile:
    def test_profile_roundtrip(self):
        data = _register_donor()
        prof = _create_profile(data["access_token"])
        assert prof["blood_group"] == "O-"
        assert prof["is_available"] is True
        assert prof["donation_count"] == 0

    def test_profile_update(self):
        data = _register_donor()
        _create_profile(data["access_token"])
        r = client.put(
            "/api/donors/profile",
            json={
                "blood_group": "B+",
                "city": "Lahore",
                "area": "Gulberg",
                "birth_year": 1990,
                "weight_kg": 80,
                "is_available": False,
            },
            headers=_auth_header(data["access_token"]),
        )
        assert r.status_code == 200
        prof = r.json()
        assert prof["blood_group"] == "B+"
        assert prof["city"] == "Lahore"
        assert prof["is_available"] is False

    def test_invalid_blood_group_rejected(self):
        data = _register_donor()
        r = client.put(
            "/api/donors/profile",
            json={
                "blood_group": "XX",
                "city": "Karachi",
                "area": "Clifton",
                "birth_year": 1995,
                "weight_kg": 70,
                "is_available": True,
            },
            headers=_auth_header(data["access_token"]),
        )
        assert r.status_code == 422

    def test_underage_donor_rejected(self):
        data = _register_donor()
        r = client.put(
            "/api/donors/profile",
            json={
                "blood_group": "O+",
                "city": "Karachi",
                "area": "Clifton",
                "birth_year": 2015,
                "weight_kg": 70,
                "is_available": True,
            },
            headers=_auth_header(data["access_token"]),
        )
        assert r.status_code == 400

    def test_requester_cannot_create_donor_profile(self):
        data = _register_requester()
        r = client.put(
            "/api/donors/profile",
            json={
                "blood_group": "O+",
                "city": "Karachi",
                "area": "Clifton",
                "birth_year": 1995,
                "weight_kg": 70,
                "is_available": True,
            },
            headers=_auth_header(data["access_token"]),
        )
        assert r.status_code == 403

    def test_availability_toggle(self):
        data = _register_donor()
        _create_profile(data["access_token"])
        r = client.patch(
            "/api/donors/availability",
            json={"is_available": False},
            headers=_auth_header(data["access_token"]),
        )
        assert r.status_code == 200
        assert r.json()["is_available"] is False


class TestRequests:
    def _create_request(self, token, **overrides):
        body = {
            "patient_name": "Fatima Ahmed",
            "blood_group": "O-",
            "units_needed": 2,
            "hospital": "AKUH",
            "city": "Karachi",
            "area": "Clifton",
            "urgency": "emergency",
            "notes": "Accident victim",
        }
        body.update(overrides)
        r = client.post("/api/requests", json=body, headers=_auth_header(token))
        assert r.status_code == 201, r.text
        return r.json()

    def test_create_request(self):
        data = _register_requester()
        req = self._create_request(data["access_token"])
        assert req["status"] == "open"
        assert req["blood_group"] == "O-"
        assert req["urgency"] == "emergency"
        assert req["requester_name"] == "Ahmed Family"

    def test_emergency_expiry_short(self):
        data = _register_requester()
        req = self._create_request(data["access_token"])
        from datetime import datetime

        expires = datetime.fromisoformat(req["expires_at"].replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        window = (expires - datetime.now(UTC)).total_seconds() / 3600
        assert 0 < window <= 6

    def test_list_requests_public(self):
        data = _register_requester()
        self._create_request(data["access_token"])
        r = client.get("/api/requests")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_matches_finds_compatible_donor(self):
        donor_data = _register_donor()
        _create_profile(donor_data["access_token"], blood_group="O-", city="Karachi")
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])
        r = client.get(
            f"/api/requests/{req['id']}/matches",
            headers=_auth_header(req_data["access_token"]),
        )
        assert r.status_code == 200
        matches = r.json()
        assert len(matches) == 1
        assert matches[0]["blood_group"] == "O-"
        assert matches[0]["city"] == "Karachi"

    def test_matches_excludes_incompatible_group(self):
        donor_data = _register_donor()
        _create_profile(donor_data["access_token"], blood_group="A+", city="Karachi")
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])  # O- request
        r = client.get(
            f"/api/requests/{req['id']}/matches",
            headers=_auth_header(req_data["access_token"]),
        )
        assert r.json() == []

    def test_matches_excludes_unavailable_donor(self):
        donor_data = _register_donor()
        _create_profile(donor_data["access_token"], blood_group="O-", is_available=False)
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])
        r = client.get(
            f"/api/requests/{req['id']}/matches",
            headers=_auth_header(req_data["access_token"]),
        )
        assert r.json() == []

    def test_fulfill_flow(self):
        donor_data = _register_donor()
        prof = _create_profile(donor_data["access_token"], blood_group="O-")
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])
        r = client.post(
            f"/api/requests/{req['id']}/fulfill",
            json={"donor_id": prof["id"], "units": 1},
            headers=_auth_header(req_data["access_token"]),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "fulfilled"

    def test_fulfill_incompatible_donor_rejected(self):
        donor_data = _register_donor()
        prof = _create_profile(donor_data["access_token"], blood_group="AB+")
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])  # O- request
        r = client.post(
            f"/api/requests/{req['id']}/fulfill",
            json={"donor_id": prof["id"], "units": 1},
            headers=_auth_header(req_data["access_token"]),
        )
        assert r.status_code == 409

    def test_fulfill_updates_donor_cooldown(self):
        donor_data = _register_donor()
        prof = _create_profile(donor_data["access_token"], blood_group="O-")
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])
        client.post(
            f"/api/requests/{req['id']}/fulfill",
            json={"donor_id": prof["id"], "units": 1},
            headers=_auth_header(req_data["access_token"]),
        )
        r = client.get("/api/donors/profile", headers=_auth_header(donor_data["access_token"]))
        assert r.json()["donation_count"] == 1
        assert r.json()["is_available"] is False
        assert r.json()["last_donation_date"] is not None

    def test_cancel_flow(self):
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])
        r = client.post(
            f"/api/requests/{req['id']}/cancel",
            headers=_auth_header(req_data["access_token"]),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_cancel_fulfilled_rejected(self):
        donor_data = _register_donor()
        prof = _create_profile(donor_data["access_token"], blood_group="O-")
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])
        client.post(
            f"/api/requests/{req['id']}/fulfill",
            json={"donor_id": prof["id"], "units": 1},
            headers=_auth_header(req_data["access_token"]),
        )
        r = client.post(
            f"/api/requests/{req['id']}/cancel",
            headers=_auth_header(req_data["access_token"]),
        )
        assert r.status_code == 409

    def test_foreign_user_cannot_fulfill(self):
        donor_data = _register_donor()
        prof = _create_profile(donor_data["access_token"], blood_group="O-")
        req_data = _register_requester()
        req = self._create_request(req_data["access_token"])
        other = _register_requester("other@test.pk")
        r = client.post(
            f"/api/requests/{req['id']}/fulfill",
            json={"donor_id": prof["id"], "units": 1},
            headers=_auth_header(other["access_token"]),
        )
        assert r.status_code == 403


class TestPublicAndAdmin:
    def test_health(self):
        assert client.get("/api/health").status_code == 200

    def test_blood_groups_reference(self):
        r = client.get("/api/blood-groups")
        assert r.status_code == 200
        data = r.json()
        assert len(data["groups"]) == 8
        assert data["universal_donor"] == "O-"
        assert data["universal_recipient"] == "AB+"

    def test_spa_served(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_admin_stats_requires_admin(self):
        data = _register_requester()
        r = client.get("/api/admin/stats", headers=_auth_header(data["access_token"]))
        assert r.status_code == 403

    def test_admin_verify_donor(self):
        donor_data = _register_donor()
        prof = _create_profile(donor_data["access_token"])
        admin_data = client.post(
            "/api/auth/register",
            json={
                "email": "boss@zindagi.pk",
                "password": "adminpass123",
                "full_name": "Boss",
                "phone": "0333-0000000",
                "role": "donor",
            },
        ).json()
        # promote to admin in DB
        from app.database import SessionLocal
        from app.models import User

        db = SessionLocal()
        u = db.query(User).filter(User.email == "boss@zindagi.pk").first()
        u.role = "admin"
        db.commit()
        db.close()

        r = client.post(
            f"/api/admin/donors/{prof['id']}/verify",
            headers=_auth_header(admin_data["access_token"]),
        )
        assert r.status_code == 200
        assert r.json()["is_verified"] is True
