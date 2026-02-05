"""Tests for device CRUD operations."""

import pytest


class TestDeviceListings:
    """Test device listing endpoints."""
    
    def test_list_all_slots(self, test_client, sample_devices):
        """Test listing all devices."""
        request, response = test_client.get("/list_slots")
        
        assert response.status == 200
        data = response.json
        assert "slots" in data
        assert len(data["slots"]) == 4
        
        # Verify structure
        slot = data["slots"][0]
        assert "slot_id" in slot
        assert "rackName" in slot
        assert "slotName" in slot
        assert "platform" in slot
        assert "state" in slot
    
    def test_list_slots_filter_platform(self, test_client, sample_devices):
        """Test filtering slots by platform."""
        request, response = test_client.post(
            "/list_slots",
            json={"platform": "Cisco"}
        )
        
        assert response.status == 200
        slots = response.json["slots"]
        assert len(slots) == 2  # Two Cisco devices
        assert all(slot["platform"] == "Cisco" for slot in slots)
    
    def test_list_slots_filter_tags(self, test_client, sample_devices):
        """Test filtering slots by tags."""
        request, response = test_client.post(
            "/list_slots",
            json={"tags": ["network"]}
        )
        
        assert response.status == 200
        slots = response.json["slots"]
        assert len(slots) >= 2
        assert all("network" in slot["tags"] for slot in slots)


class TestDeviceCRUD:
    """Test device CRUD operations."""
    
    def test_add_device(self, test_client, sample_racks):
        """Test adding a new device."""
        request, response = test_client.post(
            "/add_slot",
            json={
                "rackName": sample_racks[0].name,
                "slotName": "NewSlot",
                "platform": "TestPlatform",
                "tags": ["test", "new"],
                "description": "Test device"
            }
        )
        
        assert response.status == 201
        assert "slot_id" in response.json
        assert response.json["message"] == "Slot added successfully"
    
    def test_add_device_missing_required(self, test_client, sample_racks):
        """Test adding device without required fields."""
        request, response = test_client.post(
            "/add_slot",
            json={"platform": "TestPlatform"}
        )
        
        assert response.status == 400
        assert "Missing required fields" in response.json["error"]
    
    def test_update_device(self, test_client, sample_devices):
        """Test updating device information."""
        request, response = test_client.post(
            "/update_slot",
            json={
                "slot_id": sample_devices[0].id,
                "platform": "UpdatedPlatform",
                "description": "Updated description"
            }
        )
        
        assert response.status == 200
        assert "updated successfully" in response.json["message"]
    
    def test_update_nonexistent_device(self, test_client, sample_devices):
        """Test updating non-existent device."""
        request, response = test_client.post(
            "/update_slot",
            json={
                "slot_id": 99999,
                "platform": "Test"
            }
        )
        
        assert response.status == 404
        assert "not found" in response.json["error"]
    
    def test_delete_device(self, test_client, sample_devices):
        """Test deleting a device."""
        request, response = test_client.post(
            "/delete_slot",
            json={"slot_id": sample_devices[0].id}
        )
        
        assert response.status == 200
        assert "deleted successfully" in response.json["message"]
    
    def test_delete_nonexistent_device(self, test_client, sample_devices):
        """Test deleting non-existent device."""
        request, response = test_client.post(
            "/delete_slot",
            json={"slot_id": 99999}
        )
        
        assert response.status == 404
        assert "not found" in response.json["error"]
