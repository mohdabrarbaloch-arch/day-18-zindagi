"""Pydantic schemas — request/response models with validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.compatibility import BLOOD_GROUPS


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    role: str = Field(default="donner")  # typo guard below

    @field_validator("role")
    @classmethod
    def _role_valid(cls, v: str) -> str:
        v = v.lower()
        if v == "donner":
            v = "donor"
        if v not in {"donor", "requester"}:
            raise ValueError("role must be 'donor' or 'requester'")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str


# ---------- Donor profile ----------
class DonorProfileIn(BaseModel):
    blood_group: str
    city: str = Field(min_length=2, max_length=60)
    area: str = Field(min_length=2, max_length=60)
    birth_year: int = Field(ge=1900, le=2100)
    weight_kg: int = Field(ge=40, le=250)
    is_available: bool = True

    @field_validator("blood_group")
    @classmethod
    def _bg_valid(cls, v: str) -> str:
        v = v.upper().replace(" ", "")
        if v not in BLOOD_GROUPS:
            raise ValueError(f"blood_group must be one of {BLOOD_GROUPS}")
        return v


class DonorProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    blood_group: str
    city: str
    area: str
    birth_year: int
    weight_kg: int
    last_donation_date: datetime | None
    is_available: bool
    is_verified: bool
    donation_count: int


class DonorAvailabilityIn(BaseModel):
    is_available: bool


# ---------- Requests ----------
class BloodRequestIn(BaseModel):
    patient_name: str = Field(min_length=2, max_length=120)
    blood_group: str
    units_needed: int = Field(default=1, ge=1, le=20)
    hospital: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=60)
    area: str = Field(min_length=2, max_length=60)
    urgency: str = Field(default="normal")
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("blood_group")
    @classmethod
    def _bg_valid(cls, v: str) -> str:
        v = v.upper().replace(" ", "")
        if v not in BLOOD_GROUPS:
            raise ValueError(f"blood_group must be one of {BLOOD_GROUPS}")
        return v

    @field_validator("urgency")
    @classmethod
    def _urgency_valid(cls, v: str) -> str:
        v = v.lower()
        if v not in {"normal", "urgent", "emergency"}:
            raise ValueError("urgency must be normal, urgent or emergency")
        return v


class BloodRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_name: str
    blood_group: str
    units_needed: int
    hospital: str
    city: str
    area: str
    urgency: str
    status: str
    notes: str | None
    created_at: datetime
    expires_at: datetime
    requester_name: str | None = None


class FulfillIn(BaseModel):
    donor_id: int
    units: int = Field(default=1, ge=1, le=20)


class DonorMatchOut(BaseModel):
    donor_id: int
    name: str
    phone: str
    blood_group: str
    city: str
    area: str
    is_verified: bool
    donation_count: int
    last_donation_date: datetime | None
    age: int | None = None


# ---------- Admin ----------
class AdminStats(BaseModel):
    donors: int
    available_donors: int
    verified_donors: int
    open_requests: int
    fulfilled_requests: int
    total_donations: int


class DonationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    donor_id: int
    blood_group: str
    units: int
    donated_at: datetime
