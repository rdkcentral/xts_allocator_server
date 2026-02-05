"""Tests for config export endpoints."""

import pytest
import yaml


class TestConfigExport:
    """Test configuration export functionality."""
    
    def test_export_raft_config(self, test_client, sample_devices):
        """Test exporting allocator-optimized raft config."""
        # Allocate a device first
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        # Export config
        request, response = test_client.get(
            f"/export/raft_config?allocation_id={sample_devices[0].id}"
        )
        
        assert response.status == 200
        assert response.headers["Content-Type"] == "application/x-yaml"
        
        # Parse YAML
        config = yaml.safe_load(response.body)
        assert config["version"] == "1.0"
        assert "allocator" in config
        assert "allocations" in config
        assert len(config["allocations"]) == 1
        assert config["allocations"][0]["allocation_id"] == sample_devices[0].id
    
    def test_export_python_raft_config(self, test_client, sample_devices):
        """Test exporting python_raft-compatible config."""
        # Allocate a device
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        # Export config
        request, response = test_client.get(
            f"/export/python_raft_config?allocation_id={sample_devices[0].id}"
        )
        
        assert response.status == 200
        
        # Parse YAML
        config = yaml.safe_load(response.body)
        assert "rack_config" in config
        assert "device_config" in config
        assert config["rack_config"]["version"] == "1.0"
        assert len(config["device_config"]["devices"]) == 1
    
    def test_export_filter_by_email(self, test_client, sample_devices):
        """Test exporting config filtered by owner email."""
        # Allocate devices to different users
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user2@example.com"},
                "slot": {"id": sample_devices[1].id}
            }
        )
        
        # Export for user1 only
        request, response = test_client.get(
            "/export/raft_config?owner_email=user1@example.com"
        )
        
        assert response.status == 200
        config = yaml.safe_load(response.body)
        assert len(config["allocations"]) == 1
        assert config["allocations"][0]["owner_email"] == "user1@example.com"
    
    def test_export_missing_parameters(self, test_client, sample_devices):
        """Test export without required parameters."""
        request, response = test_client.get("/export/raft_config")
        
        assert response.status == 400
        assert "must be provided" in response.json["error"]
    
    def test_export_no_devices_found(self, test_client, sample_devices):
        """Test export when no devices match criteria."""
        request, response = test_client.get(
            "/export/raft_config?allocation_id=99999"
        )
        
        assert response.status == 404
        assert "No allocated devices found" in response.json["error"]
