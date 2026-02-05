"""Tests for rack operations."""

import pytest


class TestRacks:
    """Test rack listing and search functionality."""
    
    def test_list_racks(self, test_client, sample_racks, sample_devices):
        """Test listing all racks."""
        request, response = test_client.get("/list_racks")
        
        assert response.status == 200
        data = response.json
        assert "racks" in data
        assert len(data["racks"]) == 3
        
        # Verify structure
        rack = data["racks"][0]
        assert "id" in rack
        assert "name" in rack
        assert "location" in rack
        assert "building" in rack
        assert "device_counts" in rack or "device_count" in rack
    
    def test_get_rack_devices(self, test_client, sample_racks, sample_devices):
        """Test getting devices for a specific rack."""
        rack_id = sample_racks[0].id
        request, response = test_client.get(f"/rack/{rack_id}/devices")
        
        assert response.status == 200
        data = response.json
        assert "devices" in data
        # Rack1 should have 2 devices
        assert len(data["devices"]) == 2
    
    def test_search_devices(self, test_client, sample_devices):
        """Test device search endpoint."""
        request, response = test_client.post(
            "/devices/search",
            json={
                "platform": "Cisco",
                "state": "free"
            }
        )
        
        assert response.status == 200
        devices = response.json["results"]  # Changed from "devices" to "results"
        assert all(d["platform"] == "Cisco" for d in devices)
        assert all(d["state"] == "free" for d in devices)
