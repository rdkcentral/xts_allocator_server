"""Tests for config export endpoints."""

import pytest
import yaml


class TestConfigExport:
    """Test configuration export functionality."""
    
    def test_export_raft_config(self, test_client, sample_devices, auth_headers_engineer):
        """Test exporting allocator-optimized raft config."""
        # Allocate a device first
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
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
    
    def test_export_python_raft_config(self, test_client, sample_devices, auth_headers_engineer):
        """Test exporting python_raft-compatible config."""
        # Allocate a device
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
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
    
    def test_export_filter_by_email(self, test_client, sample_devices, auth_headers_engineer):
        """Test exporting config filtered by owner email."""
        # Allocate devices to different users
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user1@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user2@example.com"},
                "slot": {"id": sample_devices[1].id}
            },
            headers=auth_headers_engineer
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

    def test_export_python_raft_device_profile(self, test_client, sample_devices, auth_headers_engineer):
        """Test exporting platform-centric python_raft device profile."""
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )

        request, response = test_client.get(
            f"/export/python_raft_device_profile?allocation_id={sample_devices[0].id}"
        )

        assert response.status == 200
        config = yaml.safe_load(response.body)
        assert config["profile_type"] == "python_raft_device_profile"
        assert "deviceConfig" in config
        assert "platformProfiles" in config["deviceConfig"]
        assert "devices" in config["deviceConfig"]

        cpe_key = next(iter(config["deviceConfig"]["devices"]))
        platform_key = config["deviceConfig"]["devices"][cpe_key]["platform_profile"]
        assert platform_key in config["deviceConfig"]["platformProfiles"]

    def test_export_python_raft_rack_config(self, test_client, sample_devices, auth_headers_engineer):
        """Test exporting rack/slot config with includes and global settings."""
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "test@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )

        request, response = test_client.get(
            f"/export/python_raft_rack_config?allocation_id={sample_devices[0].id}"
        )

        assert response.status == 200
        config = yaml.safe_load(response.body)
        assert config["profile_type"] == "python_raft_rack_config"
        assert "globalConfig" in config
        assert "rackConfig" in config
        assert "includes" in config["globalConfig"]
        assert "deviceConfig" in config["globalConfig"]["includes"]

        rack_key = next(iter(config["rackConfig"]))
        rack_data = config["rackConfig"][rack_key]
        slot_keys = [k for k in rack_data.keys() if k not in ("name", "description")]
        assert slot_keys, "Expected at least one slot in rack config"
        slot_data = rack_data[slot_keys[0]]
        assert "devices" in slot_data
        assert "dut" in slot_data["devices"][0]
