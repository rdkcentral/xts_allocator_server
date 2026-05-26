"""Tests for health check and metrics endpoints."""



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
    
    def test_metrics_endpoint(self, test_client, sample_devices, auth_headers_engineer):
        """Test metrics endpoint provides correct data."""
        # Allocate some devices
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
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
    
    def test_metrics_prometheus_format(self, test_client, sample_devices, auth_headers_engineer):
        """Test Prometheus metrics format endpoint."""
        # Allocate a device
        test_client.post(
            "/allocate_slot",
            json={
                "user": {"email": "user@example.com"},
                "slot": {"id": sample_devices[0].id}
            },
            headers=auth_headers_engineer
        )
        
        # Request Prometheus format
        request, response = test_client.get("/metrics?format=prometheus")
        
        assert response.status == 200
        assert response.content_type == "text/plain; version=0.0.4"
        
        # Check it's text, not JSON
        text_content = response.body.decode('utf-8')
        assert isinstance(text_content, str)
        
        # Verify Prometheus format
        assert "# HELP device_state_total" in text_content
        assert "# TYPE device_state_total gauge" in text_content
        assert 'device_state_total{state=' in text_content
        assert "device_total" in text_content
        assert "device_utilization_percent" in text_content
        assert "allocations_today_total" in text_content
    
    def test_metrics_prometheus_dedicated_endpoint(self, test_client, sample_devices):
        """Test dedicated /metrics/prometheus endpoint."""
        request, response = test_client.get("/metrics/prometheus")
        
        assert response.status == 200
        assert response.content_type == "text/plain; version=0.0.4"
        
        text_content = response.body.decode('utf-8')
        assert "# HELP" in text_content
        assert "# TYPE" in text_content
        assert "gauge" in text_content or "counter" in text_content
    
    def test_metrics_json_format_default(self, test_client, sample_devices):
        """Test that JSON format is default without format parameter."""
        request, response = test_client.get("/metrics")
        
        assert response.status == 200
        # Should be JSON
        data = response.json
        assert isinstance(data, dict)
        assert "devices" in data
        assert "allocations" in data


def test_openapi_spec(test_client):
    """Test OpenAPI specification endpoint."""
    request, response = test_client.get("/openapi.json")
    assert response.status == 200
    
    data = response.json
    assert data["openapi"] == "3.0.0"
    assert "info" in data
    assert data["info"]["title"] == "XTS Allocator Server API"
    assert "paths" in data
    assert "/allocate_slot" in data["paths"]
    assert "/deallocate_slot" in data["paths"]
    assert "/start_test" in data["paths"]
    assert "/metrics" in data["paths"]
    assert "components" in data
    assert "schemas" in data["components"]
    assert "AllocationRequest" in data["components"]["schemas"]
    assert "Device" in data["components"]["schemas"]
