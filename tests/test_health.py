"""Tests for health check and metrics endpoints."""

import pytest


class TestHealth:
    """Test health check functionality."""
    
    def test_health_check_healthy(self, test_client, sample_devices):
        """Test health check when system is healthy."""
        request, response = test_client.get("/health")
        
        assert response.status == 200
        data = response.json
        assert data["status"] == "healthy"
        assert data["service"] == "xts_allocator_server"
        assert data["database"]["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_metrics_endpoint(self, test_client, sample_devices):
        """Test metrics endpoint provides correct data."""
        # Allocate some devices
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": sample_devices[0].id}
            }
        )
        
        request, response = test_client.get("/metrics")
        
        assert response.status == 200
        data = response.json
        assert "timestamp" in data
        assert "devices" in data
        assert "allocations" in data
        
        # Check device metrics
        devices = data["devices"]
        assert devices["total"] == 4
        assert "by_state" in devices
        assert "by_rack" in devices
        assert "utilization_rate_percent" in devices
        
        # Check allocation metrics
        allocations = data["allocations"]
        assert "today" in allocations
        assert "active" in allocations
        assert "avg_duration_minutes" in allocations
        assert allocations["active"] >= 1  # At least one active
