"""Tests for device state transitions."""

import pytest


class TestStateTransitions:
    """Test device state machine transitions."""
    
    def test_change_state_to_maintenance(self, test_client, sample_devices, auth_headers_admin):
        """Test changing device state to maintenance."""
        request, response = test_client.post(
            "/change_device_state",
            json={
                "device_id": sample_devices[0].id,
                "state": "maintenance"
            },
            headers=auth_headers_admin
        )
        
        assert response.status == 200
        data = response.json
        assert data["new_state"] == "maintenance"
        assert "state_changed_at" in data
    
    def test_change_state_invalid(self, test_client, sample_devices, auth_headers_admin):
        """Test changing to invalid state."""
        request, response = test_client.post(
            "/change_device_state",
            json={
                "device_id": sample_devices[0].id,
                "state": "invalid_state"
            },
            headers=auth_headers_admin
        )
        
        assert response.status == 400
        assert "Invalid state" in response.json["error"]
    
    def test_get_valid_transitions(self, test_client, sample_devices):
        """Test getting valid state transitions for a device."""
        request, response = test_client.get(
            f"/device/{sample_devices[0].id}/valid_states"
        )
        
        assert response.status == 200
        data = response.json
        assert "current_state" in data
        assert "valid_transitions" in data
        assert isinstance(data["valid_transitions"], list)
    
    def test_get_valid_transitions_nonexistent(self, test_client, sample_devices):
        """Test getting transitions for non-existent device."""
        request, response = test_client.get("/device/99999/valid_states")
        
        assert response.status == 404
        assert "not found" in response.json["error"]
