"""Tests for allocation and deallocation endpoints."""

import pytest
from datetime import datetime, timedelta


class TestAllocation:
    """Test allocation functionality."""
    
    def test_allocate_by_id_success(self, test_client, sample_devices):
        """Test successful allocation by device ID."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {
                    "email": "test@example.com",
                    "username": "testuser",
                    "name": "Test User"
                },
                "slot": {"id": sample_devices[0].id},
                "duration": "2h"
            }
        )
        
        assert response.status == 200
        data = response.json
        assert data["slot_id"] == sample_devices[0].id
        assert data["state"] == "allocated"
        assert data["owner_email"] == "test@example.com"
        assert "allocation_expiry" in data
        assert data["duration_minutes"] == 120
        assert "allocation_history_id" in data
    
    def test_allocate_by_platform_success(self, test_client, sample_devices):
        """Test successful allocation by platform."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"platform": "Dell"}
            }
        )
        
        assert response.status == 200
        data = response.json
        assert data["slot_id"] == sample_devices[1].id
        assert data["state"] == "allocated"
        assert data["owner_email"] == "user@example.com"
    
    def test_allocate_by_platform_and_tags(self, test_client, sample_devices):
        """Test allocation by platform with tag filtering."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {
                    "platform": "Cisco",
                    "tags": ["network"]
                }
            }
        )
        
        assert response.status == 200
        data = response.json
        # Verify we got a Cisco device (either device 1 or 4)
        assert data["slot_id"] in [sample_devices[0].id, sample_devices[3].id]
        assert "network" in sample_devices[0].tags  # Verify the device has the tag
    
    def test_allocate_already_allocated(self, test_client, sample_devices):
        """Test allocation of already allocated device."""
        # First allocation
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        # Second allocation attempt
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user2@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        assert response.status == 409
        assert "not free" in response.json["message"]
    
    def test_allocate_nonexistent_device(self, test_client, sample_devices):
        """Test allocation of non-existent device."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": 99999}
            }
        )
        
        assert response.status == 404
        assert "not found" in response.json["message"]
    
    def test_allocate_no_matching_criteria(self, test_client, sample_devices):
        """Test allocation when no devices match criteria."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"platform": "NonExistent"}
            }
        )
        
        assert response.status == 200
        assert response.json["message"] == "No free slot matches the criteria"
    
    def test_allocate_invalid_duration(self, test_client, sample_devices):
        """Test allocation with invalid duration format."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": sample_devices[0].id},
                "duration": "invalid"
            }
        )
        
        assert response.status == 400
        assert "Invalid duration format" in response.json["error"]
    
    def test_allocate_duration_too_long(self, test_client, sample_devices):
        """Test allocation with duration exceeding maximum."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": sample_devices[0].id},
                "duration": "20000m"  # Over 1 week
            }
        )
        
        assert response.status == 400
        assert "Duration must be between" in response.json["error"]
    
    def test_allocate_missing_criteria(self, test_client, sample_devices):
        """Test allocation without id or platform."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {}
            }
        )
        
        assert response.status == 400
        assert "'id' or 'platform' must be provided" in response.json["message"]


class TestDeallocation:
    """Test deallocation functionality."""
    
    def test_deallocate_success(self, test_client, sample_devices):
        """Test successful deallocation."""
        # First allocate
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        assert response.status == 200
        
        # Then deallocate
        request, response = test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        assert response.status == 200
        assert "free" in response.json["message"]
    
    def test_deallocate_unauthorized(self, test_client, sample_devices):
        """Test deallocation by different user."""
        # Allocate with user1
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        # Try to deallocate with user2
        request, response = test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "user2@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        assert response.status == 403
        assert "Unauthorized" in response.json["message"]
    
    def test_deallocate_nonexistent_device(self, test_client, sample_devices):
        """Test deallocation of non-existent device."""
        request, response = test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": 99999}
            }
        )
        
        assert response.status == 404
        assert "not found" in response.json["message"]
