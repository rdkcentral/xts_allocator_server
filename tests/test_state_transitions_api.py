"""Integration tests for state transitions via the /change_device_state API."""

import pytest


class TestStateTransitionsViaAPI:
    """Test device state changes through the HTTP endpoint."""

    def _set_device_state(self, test_client, device_id, state, auth_headers):
        """Helper: force device to a specific state via API."""
        _, resp = test_client.post("/change_device_state", json={
            "device_id": device_id,
            "state": state
        }, headers=auth_headers)
        return resp

    # ── Valid transitions ────────────────────────────────────────────
    @pytest.mark.parametrize("start_state,end_state", [
        ("free", "maintenance"),
        ("free", "offline"),
        ("maintenance", "free"),
        ("maintenance", "offline"),
        ("offline", "free"),
        ("offline", "maintenance"),
    ])
    def test_valid_transitions_from_unowned_states(
        self, test_client, sample_devices, auth_headers_admin, start_state, end_state
    ):
        device = sample_devices[0]
        # Set starting state
        if start_state != "free":
            self._set_device_state(test_client, device.id, start_state, auth_headers_admin)

        resp = self._set_device_state(test_client, device.id, end_state, auth_headers_admin)
        assert resp.status == 200
        assert resp.json["new_state"] == end_state

    def test_allocated_to_maintenance(self, test_client, sample_devices, auth_headers_admin, auth_headers_engineer):
        """Admin can force allocated device to maintenance."""
        device = sample_devices[0]

        # Allocate first
        test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)

        resp = self._set_device_state(test_client, device.id, "maintenance", auth_headers_admin)
        assert resp.status == 200
        assert resp.json["new_state"] == "maintenance"

    def test_allocated_to_offline(self, test_client, sample_devices, auth_headers_admin, auth_headers_engineer):
        """Admin can force allocated device offline."""
        device = sample_devices[0]

        test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)

        resp = self._set_device_state(test_client, device.id, "offline", auth_headers_admin)
        assert resp.status == 200
        assert resp.json["new_state"] == "offline"

    def test_resetting_to_free(self, test_client, sample_devices, auth_headers_admin, auth_headers_engineer):
        """Resetting device can be moved back to free."""
        device = sample_devices[0]

        # free -> allocated -> resetting
        test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        self._set_device_state(test_client, device.id, "resetting", auth_headers_admin)

        resp = self._set_device_state(test_client, device.id, "free", auth_headers_admin)
        assert resp.status == 200
        assert resp.json["new_state"] == "free"

    def test_resetting_to_maintenance(self, test_client, sample_devices, auth_headers_admin, auth_headers_engineer):
        """Resetting device can be put into maintenance."""
        device = sample_devices[0]

        test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        self._set_device_state(test_client, device.id, "resetting", auth_headers_admin)

        resp = self._set_device_state(test_client, device.id, "maintenance", auth_headers_admin)
        assert resp.status == 200
        assert resp.json["new_state"] == "maintenance"

    # ── Invalid transitions ──────────────────────────────────────────
    def test_free_to_testing_rejected(self, test_client, sample_devices, auth_headers_admin):
        """Can't go directly from free to testing."""
        device = sample_devices[0]
        resp = self._set_device_state(test_client, device.id, "testing", auth_headers_admin)
        assert resp.status == 400

    def test_free_to_busy_rejected(self, test_client, sample_devices, auth_headers_admin):
        """Can't go directly from free to busy."""
        device = sample_devices[0]
        resp = self._set_device_state(test_client, device.id, "busy", auth_headers_admin)
        assert resp.status == 400

    def test_free_to_resetting_rejected(self, test_client, sample_devices, auth_headers_admin):
        """Can't reset a free device."""
        device = sample_devices[0]
        resp = self._set_device_state(test_client, device.id, "resetting", auth_headers_admin)
        assert resp.status == 400

    def test_maintenance_to_testing_rejected(self, test_client, sample_devices, auth_headers_admin):
        """Can't start testing on a maintenance device."""
        device = sample_devices[0]
        self._set_device_state(test_client, device.id, "maintenance", auth_headers_admin)

        resp = self._set_device_state(test_client, device.id, "testing", auth_headers_admin)
        assert resp.status == 400

    def test_offline_to_allocated_rejected(self, test_client, sample_devices, auth_headers_admin):
        """Can't allocate an offline device directly."""
        device = sample_devices[0]
        self._set_device_state(test_client, device.id, "offline", auth_headers_admin)

        resp = self._set_device_state(test_client, device.id, "allocated", auth_headers_admin)
        assert resp.status == 400

    def test_nonexistent_state_rejected(self, test_client, sample_devices, auth_headers_admin):
        """Completely invalid state string is rejected."""
        device = sample_devices[0]
        resp = self._set_device_state(test_client, device.id, "on_fire", auth_headers_admin)
        assert resp.status == 400
        assert "Invalid state" in resp.json["error"]

    def test_nonexistent_device_rejected(self, test_client, auth_headers_admin):
        """Changing state on non-existent device returns 404."""
        _, resp = test_client.post("/change_device_state", json={
            "device_id": 99999,
            "state": "maintenance"
        }, headers=auth_headers_admin)
        assert resp.status == 404

    # ── Auth checks ──────────────────────────────────────────────────
    def test_engineer_cannot_change_state(self, test_client, sample_devices, auth_headers_engineer):
        """State changes require admin role."""
        device = sample_devices[0]
        _, resp = test_client.post("/change_device_state", json={
            "device_id": device.id,
            "state": "maintenance"
        }, headers=auth_headers_engineer)
        assert resp.status == 403

    def test_no_auth_cannot_change_state(self, test_client, sample_devices):
        """State changes require authentication."""
        device = sample_devices[0]
        _, resp = test_client.post("/change_device_state", json={
            "device_id": device.id,
            "state": "maintenance"
        })
        assert resp.status == 401

    # ── Valid transitions list endpoint ──────────────────────────────
    def test_valid_states_for_free_device(self, test_client, sample_devices):
        device = sample_devices[0]  # state=free
        _, resp = test_client.get(f"/device/{device.id}/valid_states")
        assert resp.status == 200
        assert "allocated" in resp.json["valid_transitions"]
        assert "maintenance" in resp.json["valid_transitions"]
        assert "testing" not in resp.json["valid_transitions"]

    def test_valid_states_for_maintenance_device(self, test_client, sample_devices):
        device = sample_devices[3]  # state=maintenance
        _, resp = test_client.get(f"/device/{device.id}/valid_states")
        assert resp.status == 200
        assert set(resp.json["valid_transitions"]) == {"free", "offline"}
