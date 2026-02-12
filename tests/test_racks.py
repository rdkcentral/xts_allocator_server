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
        assert "target_id" in data["devices"][0]
    
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

    def test_search_devices_by_query(self, test_client, sample_devices):
        """Test free-text box search."""
        _, response = test_client.post(
            "/devices/search",
            json={"query": "poweredge"}
        )

        assert response.status == 200
        devices = response.json["results"]
        assert len(devices) >= 1
        assert any(d["platform"] == "Dell" for d in devices)

    def test_search_devices_by_labels_alias(self, test_client, sample_devices):
        """Test labels alias in search endpoint."""
        _, response = test_client.post(
            "/devices/search",
            json={"labels": ["network"]}
        )

        assert response.status == 200
        devices = response.json["results"]
        assert len(devices) >= 2
        assert all("network" in d["labels"] for d in devices)

    def test_search_devices_by_equipment_type(self, test_client, sample_devices, auth_headers_engineer):
        """Test searching boxes by attached slot contents/equipment."""
        # Add equipment metadata to one device.
        _, update_response = test_client.post(
            "/update_slot",
            json={
                "slot_id": sample_devices[0].id,
                "external_equipment": [
                    {"type": "camera", "name": "Axis Cam"},
                    {"type": "ir_blaster", "name": "Ollemxi"}
                ]
            },
            headers=auth_headers_engineer
        )
        assert update_response.status == 200

        _, response = test_client.post(
            "/devices/search",
            json={"has_equipment_type": "camera"}
        )
        assert response.status == 200
        devices = response.json["results"]
        assert len(devices) >= 1
        assert any(d["id"] == sample_devices[0].id for d in devices)
