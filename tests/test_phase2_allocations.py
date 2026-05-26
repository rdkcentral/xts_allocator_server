from datetime import timezone


class TestPermanentAllocations:
    """Test permanent allocation features."""
    
    def test_allocate_permanent_success(self, test_client, sample_devices, auth_headers_engineer):
        """Test permanent allocation of a device."""
        device = sample_devices[0]
        
        request_data = {
            "user": {"email": "engineer@example.com", "username": "engineer1"},
            "slot": {"id": device.id}
        }
        
        _, response = test_client.post("/allocate_permanent", json=request_data, headers=auth_headers_engineer)
        
        assert response.status == 200
        data = response.json
        assert data["message"] == "Slot allocated permanently"
        assert data["slot_id"] == device.id
        assert data["allocation_type"] == "permanent"
        assert "allocation_expiry" not in data  # No expiry for permanent
        assert data["owner_email"] == "engineer@example.com"
    
    def test_allocate_permanent_not_free(self, test_client, sample_devices, auth_headers_engineer):
        """Test permanent allocation fails for non-free device."""
        device = sample_devices[0]
        
        # First allocate the device temporarily
        temp_request = {
            "user": {"email": "user1@example.com"},
            "slot": {"id": device.id},
            "duration": "1h"
        }
        test_client.post("/allocate_slot", json=temp_request, headers=auth_headers_engineer)
        
        # Try permanent allocation on allocated device
        perm_request = {
            "user": {"email": "engineer@example.com"},
            "slot": {"id": device.id}
        }
        
        _, response = test_client.post("/allocate_permanent", json=perm_request, headers=auth_headers_engineer)
        
        assert response.status == 409
        assert "not free" in response.json["message"]
    
    def test_allocate_permanent_missing_id(self, test_client, auth_headers_engineer):
        """Test permanent allocation requires device ID."""
        request_data = {
            "user": {"email": "engineer@example.com"},
            "slot": {}
        }
        
        _, response = test_client.post("/allocate_permanent", json=request_data, headers=auth_headers_engineer)
        
        assert response.status == 400
        assert "'id' must be provided" in response.json["message"]
    
    def test_allocate_permanent_device_not_found(self, test_client, auth_headers_engineer):
        """Test permanent allocation with nonexistent device."""
        request_data = {
            "user": {"email": "engineer@example.com"},
            "slot": {"id": 99999}
        }
        
        _, response = test_client.post("/allocate_permanent", json=request_data, headers=auth_headers_engineer)
        
        assert response.status == 404
        assert "not found" in response.json["message"]
    
    def test_permanent_allocation_not_expired(self, test_client, sample_devices, auth_headers_engineer):
        """Test that permanent allocations are not expired by background task."""
        device = sample_devices[0]
        
        # Allocate permanently
        request_data = {
            "user": {"email": "engineer@example.com"},
            "slot": {"id": device.id}
        }
        
        _, response = test_client.post("/allocate_permanent", json=request_data, headers=auth_headers_engineer)
        assert response.status == 200
        
        # Check device state
        _, list_response = test_client.get("/list_slots")
        devices = list_response.json["slots"]
        allocated_device = next(d for d in devices if d["id"] == device.id)
        
        assert allocated_device["state"] == "allocated"
        assert allocated_device["allocation_type"] == "permanent"
        assert allocated_device["allocation_expiry"] is None
    
    def test_deallocate_permanent_allocation(self, test_client, sample_devices, auth_headers_engineer):
        """Test deallocation of permanently allocated device."""
        device = sample_devices[0]
        
        # Allocate permanently
        alloc_request = {
            "user": {"email": "engineer@example.com"},
            "slot": {"id": device.id}
        }
        test_client.post("/allocate_permanent", json=alloc_request, headers=auth_headers_engineer)
        
        # Deallocate
        dealloc_request = {
            "user": {"email": "engineer@example.com"},
            "slot": {"id": device.id}
        }
        
        _, response = test_client.post("/deallocate_slot", json=dealloc_request, headers=auth_headers_engineer)
        
        assert response.status == 200
        assert response.json["message"] == "Slot deallocated successfully"


class TestDeviceStatusTracking:
    """Test device status reporting and tracking."""
    
    def test_report_status_success(self, test_client, sample_devices):
        """Test successful status report."""
        device = sample_devices[0]
        
        status_data = {
            "device_id": device.id,
            "connectivity_status": "online",
            "software_version": "v2.0.1",
            "system_metrics": {
                "cpu_usage": 45.2,
                "memory_usage": 62.8,
                "uptime_hours": 48
            }
        }
        
        _, response = test_client.post("/report_status", json=status_data)
        
        assert response.status == 200
        data = response.json
        assert data["message"] == "Status updated successfully"
        assert data["device_id"] == device.id
        assert data["connectivity_status"] == "online"
        assert "last_seen" in data
    
    def test_report_status_missing_device_id(self, test_client):
        """Test status report without device_id."""
        status_data = {
            "connectivity_status": "online"
        }
        
        _, response = test_client.post("/report_status", json=status_data)
        
        assert response.status == 400
        assert "device_id is required" in response.json["error"]
    
    def test_report_status_device_not_found(self, test_client):
        """Test status report for nonexistent device."""
        status_data = {
            "device_id": 99999,
            "connectivity_status": "online"
        }
        
        _, response = test_client.post("/report_status", json=status_data)
        
        assert response.status == 404
        assert "not found" in response.json["error"]
    
    def test_report_status_partial_update(self, test_client, sample_devices):
        """Test status report with only some fields."""
        device = sample_devices[0]
        
        # Update only connectivity status
        status_data = {
            "device_id": device.id,
            "connectivity_status": "online"
        }
        
        _, response = test_client.post("/report_status", json=status_data)
        
        assert response.status == 200
        assert response.json["connectivity_status"] == "online"
    
    def test_report_status_updates_last_seen(self, test_client, sample_devices):
        """Test that status report updates last_seen timestamp."""
        device = sample_devices[0]
        
        status_data = {
            "device_id": device.id,
            "connectivity_status": "online"
        }
        
        _, response = test_client.post("/report_status", json=status_data)
        
        assert response.status == 200
        last_seen = response.json["last_seen"]
        assert last_seen is not None
        
        # Parse and verify timestamp is recent
        from datetime import datetime
        last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc).replace(tzinfo=last_seen_dt.tzinfo)
        delta = (now - last_seen_dt).total_seconds()
        assert delta < 5  # Should be within 5 seconds
