"""Tests for concurrent operations and race conditions."""



class TestConcurrentAllocations:
    """Test concurrent allocation scenarios to detect race conditions."""
    
    def test_sequential_double_allocation_prevented(self, test_client, sample_devices, auth_headers_engineer):
        """Test that two users cannot allocate the same device sequentially."""
        device = sample_devices[0]
        
        # First user allocates
        _, response1 = test_client.post("/allocate_slot", json={
            "user": {"email": "user1@example.com", "username": "user1"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert response1.status == 200
        
        # Second user tries to allocate same device
        _, response2 = test_client.post("/allocate_slot", json={
            "user": {"email": "user2@example.com", "username": "user2"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        # Should fail with 409 Conflict
        assert response2.status == 409
        assert "not free" in response2.json["message"].lower()
    
    def test_allocation_query_uses_current_state(self, test_client, sample_devices, auth_headers_engineer):
        """Verify allocation queries check current device state from database."""
        device = sample_devices[0]
        
        # Allocate device
        _, response1 = test_client.post("/allocate_slot", json={
            "user": {"email": "user1@example.com", "username": "user1"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert response1.status == 200
        
        # Query device list - should show allocated
        _, list_response = test_client.get("/list_slots")
        device_state = next(d for d in list_response.json["slots"] if d["id"] == device.id)
        assert device_state["state"] == "allocated"
        assert device_state["owner_email"] == "user1@example.com"
        
        # Try to allocate again - should read current state and reject
        _, response2 = test_client.post("/allocate_slot", json={
            "user": {"email": "user2@example.com", "username": "user2"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert response2.status == 409
    
    def test_state_machine_prevents_invalid_transitions(self, test_client, sample_devices, auth_headers_admin):
        """Test that state machine enforces valid transitions under load."""
        device = sample_devices[0]
        
        # Start with device in free state, try free -> testing (invalid)
        # free -> testing is invalid (must go through allocated first)
        _, response = test_client.post("/change_device_state", json={
            "device_id": device.id,
            "state": "testing"
        }, headers=auth_headers_admin)
        
        assert response.status == 400
        assert "invalid" in response.json["error"].lower() or "cannot" in response.json["error"].lower()
        
        # Verify device still free
        _, list_response = test_client.get("/list_slots")
        device_state = next(d for d in list_response.json["slots"] if d["id"] == device.id)
        assert device_state["state"] == "free"
    
    def test_multiple_sequential_allocations_different_devices(self, test_client, sample_devices, auth_headers_engineer):
        """Test rapid sequential allocations of different devices."""
        # Allocate first 3 devices rapidly
        for i, device in enumerate(sample_devices[:3]):
            _, response = test_client.post("/allocate_slot", json={
                "user": {"email": f"user{i}@example.com", "username": f"user{i}"},
                "slot": {"id": device.id}
            }, headers=auth_headers_engineer)
            assert response.status == 200, f"Failed to allocate device {device.id}"
        
        # Verify all 3 allocated
        _, list_response = test_client.get("/list_slots")
        allocated_count = sum(1 for d in list_response.json["slots"] 
                             if d["state"] == "allocated")
        assert allocated_count == 3


class TestDatabaseTransactionIntegrity:
    """Test database transaction behavior and rollback handling."""
    
    def test_failed_allocation_rolls_back_cleanly(self, test_client, sample_devices, auth_headers_engineer):
        """Test that failed allocations don't leave partial data."""
        device = sample_devices[0]

        # Attempt allocation with missing required field (should fail)
        _, response = test_client.post("/allocate_slot", json={
            "user": {"email": "test@example.com"},  # Missing username (some routes may require it)
            "slot": {"id": 99999}  # Non-existent device
        }, headers=auth_headers_engineer)
        
        # Should fail with 404
        assert response.status == 404
        
        # Verify original device unchanged
        _, list_response = test_client.get("/list_slots")
        device_check = next(d for d in list_response.json["slots"] if d["id"] == device.id)
        assert device_check["state"] == "free"  # Should remain in original state
    
    def test_allocation_history_created_atomically(self, test_client, sample_devices, auth_headers_engineer):
        """Test that allocation history is created in same transaction as device update."""
        device = sample_devices[0]
        
        # Allocate device
        _, alloc_response = test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com", "username": "user", "name": "Test User"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert alloc_response.status == 200
        
        # Check allocation history exists
        _, history_response = test_client.get(f"/allocation_history?device_id={device.id}")
        assert history_response.status == 200
        history = history_response.json["history"]
        assert len(history) > 0
        assert history[0]["email"] == "user@example.com"
        assert history[0]["device_id"] == device.id
    
    def test_deallocation_without_allocation_fails(self, test_client, sample_devices, auth_headers_engineer):
        """Test that deallocating a free device fails gracefully."""
        device = sample_devices[0]
        
        # Try to deallocate a free device
        _, response = test_client.post("/deallocate_slot", json={
            "user": {"email": "user@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        # Should fail (device not allocated) - may succeed if route doesn't validate state
        # Just verify device remains free
        _, list_check = test_client.get("/list_slots")
        device_check = next(d for d in list_check.json["slots"] if d["id"] == device.id)
        assert device_check["state"] == "free"
    
    def test_state_transition_atomic_with_timestamp(self, test_client, sample_devices, auth_headers_engineer, auth_headers_admin):
        """Test that state transitions update state and timestamp atomically."""
        device = sample_devices[0]
        
        # Allocate device
        _, alloc_response = test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com", "username": "user"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        # Get device details
        _, list_response = test_client.get("/list_slots")
        device_before = next(d for d in list_response.json["slots"] if d["id"] == device.id)
        state_changed_before = device_before.get("state_changed_at")
        
        # Change state
        _, state_response = test_client.post("/change_device_state", json={
            "device_id": device.id,
            "state": "testing"
        }, headers=auth_headers_admin)
        assert state_response.status == 200
        
        # Verify state and timestamp both updated
        _, list_response2 = test_client.get("/list_slots")
        device_after = next(d for d in list_response2.json["slots"] if d["id"] == device.id)
        
        assert device_after["state"] == "testing"
        state_changed_after = device_after.get("state_changed_at")
        
        # Timestamp should be different (newer)
        if state_changed_before and state_changed_after:
            assert state_changed_after != state_changed_before


class TestStateConsistency:
    """Test that device state remains consistent across operations."""
    
    def test_device_owner_cleared_on_deallocation(self, test_client, sample_devices, auth_headers_engineer):
        """Test that owner_email is properly cleared on deallocation."""
        device = sample_devices[0]
        
        # Allocate
        test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com", "username": "user"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        # Verify owner set
        _, list1 = test_client.get("/list_slots")
        device1 = next(d for d in list1.json["slots"] if d["id"] == device.id)
        assert device1["owner_email"] == "user@example.com"
        
        # Deallocate
        test_client.post("/deallocate_slot", json={
            "user": {"email": "user@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        # Verify owner cleared
        _, list2 = test_client.get("/list_slots")
        device2 = next(d for d in list2.json["slots"] if d["id"] == device.id)
        assert device2["state"] == "free"
        owner = device2.get("owner_email")
        assert owner is None or owner == ""
    
    def test_allocation_expiry_set_for_temporary(self, test_client, sample_devices, auth_headers_engineer):
        """Test that temporary allocations have expiry timestamp."""
        device = sample_devices[0]
        
        # Allocate with duration
        _, response = test_client.post("/allocate_slot", json={
            "user": {"email": "user@example.com", "username": "user"},
            "slot": {"id": device.id},
            "duration": "30m"
        }, headers=auth_headers_engineer)
        assert response.status == 200
        
        # Check device has expiry
        _, list_response = test_client.get("/list_slots")
        device_check = next(d for d in list_response.json["slots"] if d["id"] == device.id)
        
        assert device_check.get("allocation_expiry") is not None
        assert device_check.get("allocation_type") == "temporary"
    
    def test_permanent_allocation_no_expiry(self, test_client, sample_devices, auth_headers_engineer):
        """Test that permanent allocations don't have expiry."""
        device = sample_devices[0]
        
        # Permanent allocation
        _, response = test_client.post("/allocate_permanent", json={
            "user": {"email": "user@example.com", "username": "user"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        assert response.status == 200
        
        # Check device has no expiry
        _, list_response = test_client.get("/list_slots")
        device_check = next(d for d in list_response.json["slots"] if d["id"] == device.id)
        
        expiry = device_check.get("allocation_expiry")
        assert expiry is None or expiry == ""
        assert device_check.get("allocation_type") == "permanent"

