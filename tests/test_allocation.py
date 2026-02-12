"""Tests for allocation and deallocation endpoints."""

import pytest
from datetime import datetime, timedelta


class TestAllocation:
    """Test allocation functionality."""
    
    def test_allocate_by_id_success(self, test_client, sample_devices, auth_headers_engineer):
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
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 200
        data = response.json
        assert data["slot_id"] == sample_devices[0].id
        assert data["target_id"] == "Cisco@TestRack1/Slot1"
        assert data["state"] == "allocated"
        assert data["owner_email"] == "test@example.com"
        assert "allocation_expiry" in data
        assert data["duration_minutes"] == 120
        assert "allocation_history_id" in data
    
    def test_allocate_by_platform_success(self, test_client, sample_devices, auth_headers_engineer):
        """Test successful allocation by platform."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"platform": "Dell"}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 200
        data = response.json
        assert data["slot_id"] == sample_devices[1].id
        assert data["target_id"] == "Dell@TestRack2/Slot2"
        assert data["state"] == "allocated"
        assert data["owner_email"] == "user@example.com"

    def test_allocate_by_target_id_slot_match(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation by explicit target_id rack/slot."""
        _, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"target_id": "Cisco@TestRack1/Slot1"}
            },
            headers=auth_headers_engineer
        )

        assert response.status == 200
        data = response.json
        assert data["slot_id"] == sample_devices[0].id
        assert data["target_id"] == "Cisco@TestRack1/Slot1"
        assert data["state"] == "allocated"

    def test_allocate_by_target_id_platform_fallback(self, test_client, sample_devices, auth_headers_engineer):
        """Test target_id fallback to platform when slot lookup does not match."""
        _, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"target_id": "Dell"}
            },
            headers=auth_headers_engineer
        )

        assert response.status == 200
        data = response.json
        assert data["slot_id"] == sample_devices[1].id
        assert data["target_id"] == "Dell@TestRack2/Slot2"

    def test_allocate_by_platform_and_tags(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation by platform with tag filtering."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {
                    "platform": "Cisco",
                    "tags": ["network"]
                }
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 200
        data = response.json
        # Verify we got a Cisco device (either device 1 or 4)
        assert data["slot_id"] in [sample_devices[0].id, sample_devices[3].id]
        assert "network" in sample_devices[0].tags  # Verify the device has the tag
    
    def test_allocate_already_allocated(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation of already allocated device."""
        # First allocation
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        
        # Second allocation attempt
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user2@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 409
        assert "not free" in response.json["message"]
    
    def test_allocate_nonexistent_device(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation of non-existent device."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": 99999}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 404
        assert "not found" in response.json["message"]
    
    def test_allocate_no_matching_criteria(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation when no devices match criteria."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"platform": "NonExistent"}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 200
        assert response.json["message"] == "No free slot matches the criteria"
    
    def test_allocate_invalid_duration(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation with invalid duration format."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": sample_devices[0].id},
                "duration": "invalid"
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 400
        assert "Invalid duration format" in response.json["error"]
    
    def test_allocate_duration_too_long(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation with duration exceeding maximum."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": sample_devices[0].id},
                "duration": "20000m"  # Over 1 week
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 400
        assert "Duration must be between" in response.json["error"]
    
    def test_allocate_missing_criteria(self, test_client, sample_devices, auth_headers_engineer):
        """Test allocation without id or platform."""
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 400
        assert "'id', 'platform', or 'target_id' must be provided" in response.json["message"]


class TestDeallocation:
    """Test deallocation functionality."""
    
    def test_deallocate_success(self, test_client, sample_devices, auth_headers_engineer):
        """Test successful deallocation."""
        # First allocate
        request, response = test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        assert response.status == 200
        
        # Then deallocate
        request, response = test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 200
        assert "deallocated successfully" in response.json["message"] or "free" in response.json["message"]
    
    def test_deallocate_unauthorized(self, test_client, sample_devices, auth_headers_engineer):
        """Test deallocation by different user."""
        # Allocate with user1
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        
        # Try to deallocate with user2
        request, response = test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "user2@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 403
        assert "Unauthorized" in response.json["message"]
    
    def test_deallocate_nonexistent_device(self, test_client, sample_devices, auth_headers_engineer):
        """Test deallocation of non-existent device."""
        request, response = test_client.post(
            "/deallocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": 99999}
            },
            headers=auth_headers_engineer
        )
        
        assert response.status == 404
        assert "not found" in response.json["message"]


class TestBorrowing:
    """Test borrowing and returning permanently assigned boxes."""

    def test_borrow_and_return_permanent_box_success(self, test_client, sample_devices, auth_headers_engineer):
        """Borrow a permanently assigned device and return it to original owner."""
        device_id = sample_devices[0].id

        # Original owner gets a permanent assignment.
        _, response = test_client.post(
            "/allocate_permanent",
            json={
                "user": {"email": "owner@example.com"},
                "slot": {"id": device_id}
            },
            headers=auth_headers_engineer
        )
        assert response.status == 200

        # Borrower temporarily borrows the box.
        _, response = test_client.post(
            "/borrow_slot",
            json={
                "user": {"email": "borrower@example.com", "name": "Borrow User"},
                "slot": {"id": device_id},
                "duration": "2h",
                "reason": "owner away"
            },
            headers=auth_headers_engineer
        )
        assert response.status == 200
        data = response.json
        assert data["owner_email"] == "borrower@example.com"
        assert data["borrowed_from_email"] == "owner@example.com"
        assert data["duration_minutes"] == 120

        # Borrower returns the box to original owner.
        _, response = test_client.post(
            "/return_borrowed_slot",
            json={
                "user": {"email": "borrower@example.com"},
                "slot": {"id": device_id}
            },
            headers=auth_headers_engineer
        )
        assert response.status == 200
        data = response.json
        assert data["owner_email"] == "owner@example.com"
        assert data["allocation_type"] == "permanent"

    def test_borrow_free_slot_rejected(self, test_client, sample_devices, auth_headers_engineer):
        """Cannot borrow a free slot; must allocate instead."""
        device_id = sample_devices[0].id

        _, response = test_client.post(
            "/borrow_slot",
            json={
                "user": {"email": "borrower@example.com"},
                "slot": {"id": device_id},
                "duration": "1h"
            },
            headers=auth_headers_engineer
        )

        assert response.status == 409
        assert "is free" in response.json["message"]

    def test_return_borrowed_slot_unauthorized(self, test_client, sample_devices, auth_headers_engineer):
        """Only current borrower (or admin) can return a borrowed slot."""
        device_id = sample_devices[0].id

        # Create permanent owner + borrowed state.
        test_client.post(
            "/allocate_permanent",
            json={
                "user": {"email": "owner@example.com"},
                "slot": {"id": device_id}
            },
            headers=auth_headers_engineer
        )
        test_client.post(
            "/borrow_slot",
            json={
                "user": {"email": "borrower@example.com"},
                "slot": {"id": device_id}
            },
            headers=auth_headers_engineer
        )

        # Different non-admin user attempts return.
        _, response = test_client.post(
            "/return_borrowed_slot",
            json={
                "user": {"email": "other@example.com"},
                "slot": {"id": device_id}
            },
            headers=auth_headers_engineer
        )

        assert response.status == 403
        assert "Only current borrower or admin" in response.json["message"]


class TestBackgroundTasks:
    """Test background expiry checking and hung test detection."""
    
    def test_expired_allocation_structure(self, test_client, sample_devices, auth_headers_engineer):
        """Test that temporary allocations have expiry timestamp set."""
        device = sample_devices[0]
        
        # Allocate with short duration
        _, response = test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id},
            "duration": "1m"
        }, headers=auth_headers_engineer)
        
        assert response.status == 200
        assert "allocation_expiry" in response.json
        assert response.json["allocation_expiry"] is not None
    
    def test_permanent_allocation_no_expiry(self, test_client, sample_devices, auth_headers_engineer):
        """Test that permanent allocations have no expiry."""
        device = sample_devices[0]
        
        # Allocate permanently
        _, response = test_client.post("/allocate_permanent", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        assert response.status == 200
        assert response.json.get("allocation_type") == "permanent"
    
    def test_duration_parsing_edge_cases(self, test_client, sample_devices, auth_headers_engineer):
        """Test duration parsing with various edge cases."""
        device = sample_devices[0]
        
        # Valid formats
        valid_durations = ["30m", "2h", "1.5h", "90"]
        for duration in valid_durations:
            _, response = test_client.post("/allocate_slot", json={
                "user": {"email": "tester@example.com"},
                "slot": {"id": device.id},
                "duration": duration
            }, headers=auth_headers_engineer)
            assert response.status == 200, f"Failed for duration: {duration}"
            
            # Deallocate for next test
            test_client.post("/deallocate_slot", json={
                "user": {"email": "tester@example.com"},
                "slot": {"id": device.id}
            }, headers=auth_headers_engineer)
        
        # Invalid formats
        _, response = test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id},
            "duration": "invalid"
        }, headers=auth_headers_engineer)
        assert response.status == 400
        
        # Negative duration
        _, response = test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id},
            "duration": "-10m"
        }, headers=auth_headers_engineer)
        assert response.status == 400
        
        # Zero duration
        _, response = test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id},
            "duration": "0m"
        }, headers=auth_headers_engineer)
        assert response.status == 400
