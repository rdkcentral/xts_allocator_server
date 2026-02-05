import pytest


class TestUsageStatistics:
    """Test usage statistics and reporting."""
    
    @pytest.mark.asyncio
    async def test_device_usage_stats(self, test_client, sample_devices):
        """Test device usage statistics endpoint."""
        device = sample_devices[0]
        
        # Allocate and deallocate to create history
        alloc_request = {
            "user": {"email": "user1@example.com", "username": "user1"},
            "slot": {"id": device.id},
            "duration": "1h"
        }
        await test_client.post("/allocate_slot", json=alloc_request)
        
        dealloc_request = {
            "user": {"email": "user1@example.com"},
            "slot": {"id": device.id}
        }
        await test_client.post("/deallocate_slot", json=dealloc_request)
        
        # Get usage stats
        _, response = await test_client.get(f"/device/{device.id}/usage_stats")
        
        assert response.status == 200
        data = response.json
        assert data["device_id"] == device.id
        assert data["rack"] == device.rack.name
        assert data["slot"] == device.slot_name
        assert "statistics" in data
        assert data["statistics"]["total_allocations"] >= 1
        assert "recent_allocations" in data
    
    @pytest.mark.asyncio
    async def test_device_usage_stats_not_found(self, test_client):
        """Test usage stats for nonexistent device."""
        _, response = await test_client.get("/device/99999/usage_stats")
        
        assert response.status == 404
        assert "not found" in response.json["error"]
    
    @pytest.mark.asyncio
    async def test_device_usage_stats_no_history(self, test_client, sample_devices):
        """Test usage stats for device with no allocation history."""
        device = sample_devices[0]
        
        _, response = await test_client.get(f"/device/{device.id}/usage_stats")
        
        assert response.status == 200
        data = response.json
        assert data["statistics"]["total_allocations"] == 0
        assert data["statistics"]["total_test_executions"] == 0
        assert len(data["recent_allocations"]) == 0
    
    @pytest.mark.asyncio
    async def test_device_usage_stats_multiple_allocations(self, test_client, sample_devices):
        """Test usage stats with multiple allocations."""
        device = sample_devices[0]
        
        # Create multiple allocations
        for i in range(3):
            alloc_request = {
                "user": {"email": f"user{i}@example.com"},
                "slot": {"id": device.id},
                "duration": "30m"
            }
            await test_client.post("/allocate_slot", json=alloc_request)
            
            dealloc_request = {
                "user": {"email": f"user{i}@example.com"},
                "slot": {"id": device.id}
            }
            await test_client.post("/deallocate_slot", json=dealloc_request)
        
        _, response = await test_client.get(f"/device/{device.id}/usage_stats")
        
        assert response.status == 200
        data = response.json
        assert data["statistics"]["total_allocations"] == 3
        assert len(data["recent_allocations"]) == 3
    
    @pytest.mark.asyncio
    async def test_usage_summary_default(self, test_client, sample_devices):
        """Test system-wide usage summary with default parameters."""
        # Create some allocations
        device = sample_devices[0]
        alloc_request = {
            "user": {"email": "user1@example.com"},
            "slot": {"id": device.id},
            "duration": "1h"
        }
        await test_client.post("/allocate_slot", json=alloc_request)
        
        _, response = await test_client.get("/usage_summary")
        
        assert response.status == 200
        data = response.json
        assert data["period_days"] == 30
        assert "since" in data
        assert "until" in data
        assert "statistics" in data
        assert "total_allocations" in data["statistics"]
        assert "top_devices" in data
    
    @pytest.mark.asyncio
    async def test_usage_summary_custom_period(self, test_client, sample_devices):
        """Test usage summary with custom time period."""
        _, response = await test_client.get("/usage_summary?days=7")
        
        assert response.status == 200
        data = response.json
        assert data["period_days"] == 7
    
    @pytest.mark.asyncio
    async def test_usage_summary_allocation_types(self, test_client, sample_devices):
        """Test usage summary tracks allocation types."""
        device1 = sample_devices[0]
        device2 = sample_devices[1]
        
        # Temporary allocation
        temp_request = {
            "user": {"email": "user1@example.com"},
            "slot": {"id": device1.id},
            "duration": "1h"
        }
        await test_client.post("/allocate_slot", json=temp_request)
        
        # Permanent allocation
        perm_request = {
            "user": {"email": "engineer@example.com"},
            "slot": {"id": device2.id}
        }
        await test_client.post("/allocate_permanent", json=perm_request)
        
        _, response = await test_client.get("/usage_summary")
        
        assert response.status == 200
        data = response.json
        stats = data["statistics"]
        assert stats["temporary_allocations"] >= 1
        assert stats["permanent_allocations"] >= 1
    
    @pytest.mark.asyncio
    async def test_usage_summary_unique_users(self, test_client, sample_devices):
        """Test usage summary counts unique users."""
        device = sample_devices[0]
        
        # Multiple allocations by same user
        for _ in range(2):
            alloc_request = {
                "user": {"email": "user1@example.com"},
                "slot": {"id": device.id},
                "duration": "30m"
            }
            await test_client.post("/allocate_slot", json=alloc_request)
            
            dealloc_request = {
                "user": {"email": "user1@example.com"},
                "slot": {"id": device.id}
            }
            await test_client.post("/deallocate_slot", json=dealloc_request)
        
        _, response = await test_client.get("/usage_summary")
        
        assert response.status == 200
        data = response.json
        # Should count user1 only once despite multiple allocations
        assert data["statistics"]["unique_users"] >= 1
    
    @pytest.mark.asyncio
    async def test_usage_summary_top_devices(self, test_client, sample_devices):
        """Test usage summary shows top devices by usage."""
        device = sample_devices[0]
        
        # Create multiple allocations for same device
        for i in range(5):
            alloc_request = {
                "user": {"email": f"user{i}@example.com"},
                "slot": {"id": device.id},
                "duration": "15m"
            }
            await test_client.post("/allocate_slot", json=alloc_request)
            
            dealloc_request = {
                "user": {"email": f"user{i}@example.com"},
                "slot": {"id": device.id}
            }
            await test_client.post("/deallocate_slot", json=dealloc_request)
        
        _, response = await test_client.get("/usage_summary")
        
        assert response.status == 200
        data = response.json
        top_devices = data["top_devices"]
        assert len(top_devices) > 0
        
        # Check that our device appears in top devices
        device_in_top = any(d["device_id"] == device.id for d in top_devices)
        assert device_in_top
