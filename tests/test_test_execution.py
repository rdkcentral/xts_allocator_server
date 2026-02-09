"""Tests for test execution lifecycle routes."""

import pytest
from datetime import datetime, timedelta


class TestTestExecutionLifecycle:
    """Test the test execution tracking system."""
    
    def test_start_test_success(self, test_client, sample_devices, auth_headers_engineer):
        """Test starting a test on an allocated device."""
        device = sample_devices[0]
        
        # First allocate the device
        test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        # Start test
        _, response = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "smoke_test",
            "test_suite": "regression",
            "expected_duration": 30,
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        
        assert response.status == 200
        data = response.json
        assert "test_execution_id" in data
        assert data["device_id"] == device.id
        assert data["test_name"] == "smoke_test"
        assert data["device_state"] == "testing"
    
    def test_start_test_on_free_device(self, test_client, sample_devices, auth_headers_engineer):
        """Test starting a test on non-allocated device fails."""
        device = sample_devices[0]
        
        _, response = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "smoke_test",
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        
        assert response.status == 400
        error_msg = response.json["error"].lower()
        assert "allocated" in error_msg or "free" in error_msg
    
    def test_start_test_missing_fields(self, test_client, sample_devices, auth_headers_engineer):
        """Test starting test with missing required fields."""
        _, response = test_client.post("/start_test", json={
            "device_id": sample_devices[0].id
        }, headers=auth_headers_engineer)
        
        assert response.status == 400
        assert "required" in response.json["error"].lower()
    
    def test_start_test_on_nonexistent_device(self, test_client, auth_headers_engineer):
        """Test starting test on device that doesn't exist."""
        _, response = test_client.post("/start_test", json={
            "device_id": 99999,
            "test_name": "smoke_test",
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        
        assert response.status == 404
    
    def test_test_heartbeat_success(self, test_client, sample_devices, auth_headers_engineer):
        """Test sending heartbeat for running test."""
        device = sample_devices[0]
        
        # Allocate and start test
        test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        _, start_response = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "smoke_test",
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        test_execution_id = start_response.json["test_execution_id"]
        
        # Send heartbeat
        _, response = test_client.post("/test_heartbeat", json={
            "test_execution_id": test_execution_id
        })
        
        assert response.status == 200
        assert "heartbeat received" in response.json["message"].lower()
    
    def test_test_heartbeat_nonexistent_test(self, test_client):
        """Test heartbeat for non-existent test."""
        _, response = test_client.post("/test_heartbeat", json={
            "test_execution_id": 99999
        })
        
        assert response.status == 404
        assert "no active test execution found" in response.json["error"].lower()
    
    def test_test_heartbeat_missing_test_id(self, test_client):
        """Test heartbeat without test_id."""
        _, response = test_client.post("/test_heartbeat", json={})
        
        assert response.status == 400
    
    def test_end_test_success(self, test_client, sample_devices, auth_headers_engineer):
        """Test ending a running test."""
        device = sample_devices[0]
        
        # Allocate and start test
        test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        _, start_response = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "smoke_test",
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        test_execution_id = start_response.json["test_execution_id"]
        
        # End test
        _, response = test_client.post("/end_test", json={
            "test_execution_id": test_execution_id,
            "status": "passed",
            "result_summary": {"tests_run": 10, "passed": 10}
        }, headers=auth_headers_engineer)
        
        assert response.status == 200
        data = response.json
        assert data["test_execution_id"] == test_execution_id
        assert data["status"] == "passed"
        assert "allocated" in data["device_state"]
    
    def test_end_test_with_failure(self, test_client, sample_devices, auth_headers_engineer):
        """Test ending a test that failed."""
        device = sample_devices[0]
        
        test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        
        _, start_response = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "regression",
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        test_execution_id = start_response.json["test_execution_id"]
        
        _, response = test_client.post("/end_test", json={
            "test_execution_id": test_execution_id,
            "status": "failed",
            "error_message": "Assertion failed"
        }, headers=auth_headers_engineer)
        
        assert response.status == 200
        assert response.json["status"] == "failed"
    
    def test_end_nonexistent_test(self, test_client, auth_headers_engineer):
        """Test ending a test that doesn't exist."""
        _, response = test_client.post("/end_test", json={
            "test_execution_id": 99999,
            "status": "passed"
        }, headers=auth_headers_engineer)
        
        assert response.status == 404
    
    def test_list_test_executions(self, test_client, sample_devices, auth_headers_engineer):
        """Test listing active test executions."""
        device = sample_devices[0]
        
        # Start a test
        test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id}
        }, headers=auth_headers_engineer)
        test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "smoke_test",
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        
        # List executions
        _, response = test_client.get("/test_executions")
        
        assert response.status == 200
        data = response.json
        assert "test_executions" in data
        assert len(data["test_executions"]) > 0
        assert data["test_executions"][0]["test_name"] == "smoke_test"
    
    def test_allocation_extends_during_test(self, test_client, sample_devices, auth_headers_engineer):
        """Test that allocation auto-extends if test duration exceeds remaining time."""
        device = sample_devices[0]
        
        # Allocate with short duration
        test_client.post("/allocate_slot", json={
            "user": {"email": "tester@example.com"},
            "slot": {"id": device.id},
            "duration": "5m"
        }, headers=auth_headers_engineer)
        
        # Start test with longer expected duration
        _, response = test_client.post("/start_test", json={
            "device_id": device.id,
            "test_name": "long_test",
            "expected_duration": 60,
            "user_email": "tester@example.com"
        }, headers=auth_headers_engineer)
        
        assert response.status == 200
        # Should succeed and extend allocation
