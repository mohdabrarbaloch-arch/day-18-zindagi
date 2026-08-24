"""Tests for the compatibility engine — pure logic, no DB needed."""

import pytest

from app.config import get_settings
from app.core.compatibility import (
    BLOOD_GROUPS,
    COMPATIBLE_DONORS_FOR,
    can_donate_to,
    compatible_donors_for,
    expiry_hours_for_urgency,
    is_eligible_donor,
    is_valid_blood_group,
)


class TestCompatibilityMatrix:
    def test_all_groups_valid(self):
        assert len(BLOOD_GROUPS) == 8
        for g in BLOOD_GROUPS:
            assert is_valid_blood_group(g)

    def test_invalid_group_rejected(self):
        assert not is_valid_blood_group("XX")
        assert not is_valid_blood_group("")
        assert not is_valid_blood_group("A++")

    @pytest.mark.parametrize(
        ("donor", "patient", "expected"),
        [
            ("O-", "AB+", True),  # universal donor
            ("O-", "O-", True),
            ("O+", "A+", True),
            ("A-", "A+", True),
            ("B+", "B+", True),
            ("AB+", "AB+", True),  # universal recipient
            ("AB+", "O+", False),  # AB can't donate to O
            ("A+", "O+", False),  # A can't donate to O
            ("B+", "A+", False),  # wrong ABO
            ("O+", "A-", False),  # Rh mismatch
            ("A+", "A-", False),
            ("B-", "AB+", True),
            ("B-", "B+", True),
        ],
    )
    def test_can_donate_to(self, donor, patient, expected):
        assert can_donate_to(donor, patient) is expected

    def test_compatible_donors_for_o_minus(self):
        assert set(compatible_donors_for("O-")) == {"O-"}

    def test_compatible_donors_for_ab_plus(self):
        assert set(compatible_donors_for("AB+")) == set(BLOOD_GROUPS)

    def test_compatibility_map_symmetric(self):
        for patient in BLOOD_GROUPS:
            for donor in COMPATIBLE_DONORS_FOR[patient]:
                assert can_donate_to(donor, patient)

    def test_invalid_group_compatible_empty(self):
        assert compatible_donors_for("XX") == []


class TestEligibility:
    s = get_settings()

    def test_eligible_donor(self):
        ok, reasons = is_eligible_donor(1995, 70, None, True, self.s)
        assert ok is True
        assert reasons == []

    def test_underage_rejected(self):
        ok, reasons = is_eligible_donor(2015, 70, None, True, self.s)
        assert ok is False
        assert any("under" in r for r in reasons)

    def test_overage_rejected(self):
        ok, reasons = is_eligible_donor(1950, 70, None, True, self.s)
        assert ok is False
        assert any("over" in r for r in reasons)

    def test_low_weight_rejected(self):
        ok, reasons = is_eligible_donor(1995, 45, None, True, self.s)
        assert ok is False
        assert any("kg" in r for r in reasons)

    def test_cooldown_rejected(self):
        from datetime import date, timedelta

        recent = date.today() - timedelta(days=10)
        ok, reasons = is_eligible_donor(1995, 70, recent, True, self.s)
        assert ok is False
        assert any("cooldown" in r for r in reasons)

    def test_unavailable_rejected(self):
        ok, reasons = is_eligible_donor(1995, 70, None, False, self.s)
        assert ok is False
        assert any("available" in r for r in reasons)

    def test_multiple_reasons(self):
        from datetime import date, timedelta

        recent = date.today() - timedelta(days=5)
        ok, reasons = is_eligible_donor(2010, 45, recent, False, self.s)
        assert ok is False
        assert len(reasons) >= 3


class TestExpiry:
    s = get_settings()

    def test_normal_window(self):
        assert expiry_hours_for_urgency("normal", self.s) == self.s.expiry_normal_hours

    def test_urgent_window(self):
        assert expiry_hours_for_urgency("urgent", self.s) == self.s.expiry_urgent_hours

    def test_emergency_window(self):
        assert expiry_hours_for_urgency("emergency", self.s) == self.s.expiry_emergency_hours

    def test_unknown_urgency_defaults_normal(self):
        assert expiry_hours_for_urgency("bogus", self.s) == self.s.expiry_normal_hours
