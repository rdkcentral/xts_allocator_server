"""Unit tests for state machine logic — all transitions, edge cases, helper functions."""

import pytest
from state_machine import (
    DeviceState,
    STATE_TRANSITIONS,
    is_valid_state,
    can_transition,
    get_valid_transitions,
    get_state_description,
    transition_device,
)


class TestIsValidState:
    """Test is_valid_state helper."""

    @pytest.mark.parametrize("state", [s.value for s in DeviceState])
    def test_all_valid_states(self, state):
        assert is_valid_state(state) is True

    @pytest.mark.parametrize("state", ["invalid", "", "ALLOCATED", "Free", "123", None])
    def test_invalid_states(self, state):
        assert is_valid_state(state) is False


class TestCanTransition:
    """Test every valid and invalid transition defined in STATE_TRANSITIONS."""

    # ── Valid transitions ────────────────────────────────────────────
    @pytest.mark.parametrize("src,dst", [
        ("free", "allocated"),
        ("free", "maintenance"),
        ("free", "offline"),
        ("allocated", "free"),
        ("allocated", "testing"),
        ("allocated", "busy"),
        ("allocated", "resetting"),
        ("allocated", "maintenance"),
        ("allocated", "offline"),
        ("testing", "allocated"),
        ("testing", "resetting"),
        ("testing", "offline"),
        ("busy", "allocated"),
        ("busy", "resetting"),
        ("busy", "offline"),
        ("resetting", "free"),
        ("resetting", "offline"),
        ("resetting", "maintenance"),
        ("maintenance", "free"),
        ("maintenance", "offline"),
        ("offline", "free"),
        ("offline", "maintenance"),
    ])
    def test_valid_transition(self, src, dst):
        assert can_transition(src, dst) is True

    # ── Invalid transitions ──────────────────────────────────────────
    @pytest.mark.parametrize("src,dst", [
        ("free", "testing"),
        ("free", "busy"),
        ("free", "resetting"),
        ("free", "free"),
        ("allocated", "allocated"),
        ("testing", "free"),
        ("testing", "busy"),
        ("testing", "maintenance"),
        ("testing", "testing"),
        ("busy", "free"),
        ("busy", "testing"),
        ("busy", "maintenance"),
        ("busy", "busy"),
        ("resetting", "allocated"),
        ("resetting", "testing"),
        ("resetting", "busy"),
        ("resetting", "resetting"),
        ("maintenance", "allocated"),
        ("maintenance", "testing"),
        ("maintenance", "busy"),
        ("maintenance", "resetting"),
        ("maintenance", "maintenance"),
        ("offline", "allocated"),
        ("offline", "testing"),
        ("offline", "busy"),
        ("offline", "resetting"),
        ("offline", "offline"),
    ])
    def test_invalid_transition(self, src, dst):
        assert can_transition(src, dst) is False

    def test_invalid_state_strings(self):
        assert can_transition("bogus", "free") is False
        assert can_transition("free", "bogus") is False
        assert can_transition("bogus", "bogus") is False


class TestGetValidTransitions:
    """Test get_valid_transitions returns correct options for each state."""

    def test_free_transitions(self):
        result = get_valid_transitions("free")
        assert set(result) == {"allocated", "maintenance", "offline"}

    def test_allocated_transitions(self):
        result = get_valid_transitions("allocated")
        assert set(result) == {"free", "testing", "busy", "resetting", "maintenance", "offline"}

    def test_testing_transitions(self):
        result = get_valid_transitions("testing")
        assert set(result) == {"allocated", "resetting", "offline"}

    def test_busy_transitions(self):
        result = get_valid_transitions("busy")
        assert set(result) == {"allocated", "resetting", "offline"}

    def test_resetting_transitions(self):
        result = get_valid_transitions("resetting")
        assert set(result) == {"free", "offline", "maintenance"}

    def test_maintenance_transitions(self):
        result = get_valid_transitions("maintenance")
        assert set(result) == {"free", "offline"}

    def test_offline_transitions(self):
        result = get_valid_transitions("offline")
        assert set(result) == {"free", "maintenance"}

    def test_invalid_state_returns_empty(self):
        assert get_valid_transitions("bogus") == []

    def test_completeness(self):
        """Every DeviceState must appear in STATE_TRANSITIONS."""
        for state in DeviceState:
            assert state in STATE_TRANSITIONS


class TestGetStateDescription:
    """Test state descriptions cover all states."""

    @pytest.mark.parametrize("state", [s.value for s in DeviceState])
    def test_all_states_have_description(self, state):
        desc = get_state_description(state)
        assert isinstance(desc, str)
        assert desc != "Unknown state"

    def test_unknown_state(self):
        assert get_state_description("nonsense") == "Unknown state"


class TestTransitionDevice:
    """Test transition_device with a real DB session."""

    def test_valid_transition_updates_device(self, db_session, sample_devices):
        device = sample_devices[0]  # state=free
        assert device.state == "free"

        ok, msg = transition_device(device, "maintenance", db_session)
        assert ok is True
        assert device.state == "maintenance"
        assert device.state_changed_at is not None

    def test_invalid_state_rejected(self, db_session, sample_devices):
        device = sample_devices[0]
        ok, msg = transition_device(device, "nonsense", db_session)
        assert ok is False
        assert "Invalid state" in msg

    def test_disallowed_transition_rejected(self, db_session, sample_devices):
        device = sample_devices[0]  # state=free
        ok, msg = transition_device(device, "testing", db_session)
        assert ok is False
        assert "Cannot transition" in msg

    def test_transition_to_free_clears_owner(self, db_session, sample_devices):
        device = sample_devices[0]
        device.state = "maintenance"
        device.owner_email = "someone@example.com"
        db_session.commit()

        ok, _ = transition_device(device, "free", db_session)
        assert ok is True
        assert device.owner_email is None
        assert device.allocation_expiry is None

    def test_transition_to_resetting_clears_owner(self, db_session, sample_devices):
        device = sample_devices[0]
        # free -> allocated (set manually to avoid needing allocation route)
        device.state = "allocated"
        device.owner_email = "owner@example.com"
        db_session.commit()

        ok, _ = transition_device(device, "resetting", db_session)
        assert ok is True
        assert device.owner_email is None
