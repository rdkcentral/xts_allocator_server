"""Tests for audit logging system."""

import pytest
from datetime import datetime, timedelta
from models import SessionLocal, AuditLog
from audit_log import (
    log_auth_attempt, log_unauthorized_access, log_device_allocation,
    log_device_deallocation, log_state_change, log_device_operation,
    log_test_execution, EVENT_AUTH_LOGIN, EVENT_AUTH_FAILURE,
    CATEGORY_AUTHENTICATION, SEVERITY_INFO, SEVERITY_WARNING
)


class TestAuditLogBasics:
    """Test basic audit logging functionality."""
    
    def test_log_successful_login(self):
        """Test logging successful authentication."""
        session = SessionLocal()
        try:
            audit = log_auth_attempt(
                email="test@example.com",
                success=True,
                source_ip="192.168.1.100",
                session=session
            )
            
            assert audit is not None
            assert audit.event_type == EVENT_AUTH_LOGIN
            assert audit.user_email == "test@example.com"
            assert audit.success == "true"
            assert audit.source_ip == "192.168.1.100"
            assert audit.severity == SEVERITY_INFO
        finally:
            session.close()
    
    def test_log_failed_login(self):
        """Test logging failed authentication."""
        session = SessionLocal()
        try:
            audit = log_auth_attempt(
                email="baduser@example.com",
                success=False,
                source_ip="10.0.0.50",
                error_message="Invalid credentials",
                session=session
            )
            
            assert audit is not None
            assert audit.event_type == EVENT_AUTH_FAILURE
            assert audit.user_email == "baduser@example.com"
            assert audit.success == "false"
            assert audit.error_message == "Invalid credentials"
            assert audit.severity == SEVERITY_WARNING
        finally:
            session.close()
    
    def test_log_unauthorized_access(self):
        """Test logging unauthorized access attempt."""
        session = SessionLocal()
        try:
            audit = log_unauthorized_access(
                endpoint="/change_device_state",
                user_email="engineer@example.com",
                required_role="admin",
                user_role="engineer",
                source_ip="172.16.0.5",
                session=session
            )
            
            assert audit is not None
            assert audit.event_type == "unauthorized_access"
            assert audit.success == "false"
            assert audit.details["required_role"] == "admin"
            assert audit.details["user_role"] == "engineer"
        finally:
            session.close()
    
    def test_log_device_allocation(self, sample_devices):
        """Test logging device allocation."""
        device = sample_devices[0]
        session = SessionLocal()
        try:
            audit = log_device_allocation(
                device_id=device.id,
                user_email="user@example.com",
                user_role="engineer",
                allocation_type="temporary",
                duration=120,
                source_ip="192.168.1.50",
                session=session
            )
            
            assert audit is not None
            assert audit.resource_type == "device"
            assert audit.resource_id == device.id
            assert audit.details["allocation_type"] == "temporary"
            assert audit.details["duration_minutes"] == 120
        finally:
            session.close()
    
    def test_log_device_deallocation(self, sample_devices):
        """Test logging device deallocation."""
        device = sample_devices[0]
        session = SessionLocal()
        try:
            audit = log_device_deallocation(
                device_id=device.id,
                user_email="user@example.com",
                user_role="engineer",
                session=session
            )
            
            assert audit is not None
            assert audit.event_type == "deallocation"
            assert audit.resource_id == device.id
        finally:
            session.close()
    
    def test_log_state_change(self, sample_devices):
        """Test logging device state change."""
        device = sample_devices[0]
        session = SessionLocal()
        try:
            audit = log_state_change(
                device_id=device.id,
                old_state="free",
                new_state="maintenance",
                user_email="admin@example.com",
                user_role="admin",
                session=session
            )
            
            assert audit is not None
            assert audit.event_type == "state_change"
            assert audit.event_category == "admin_operation"
            assert audit.details["old_state"] == "free"
            assert audit.details["new_state"] == "maintenance"
        finally:
            session.close()
    
    def test_log_device_operations(self, sample_devices):
        """Test logging device CRUD operations."""
        device = sample_devices[0]
        session = SessionLocal()
        try:
            # Test add
            audit_add = log_device_operation(
                operation="add",
                device_id=device.id,
                user_email="admin@example.com",
                user_role="admin",
                details={"platform": "TestBox"},
                session=session
            )
            assert audit_add.event_type == "device_add"
            
            # Test update
            audit_update = log_device_operation(
                operation="update",
                device_id=device.id,
                user_email="admin@example.com",
                user_role="admin",
                session=session
            )
            assert audit_update.event_type == "device_update"
            
            # Test delete
            audit_delete = log_device_operation(
                operation="delete",
                device_id=device.id,
                user_email="admin@example.com",
                user_role="admin",
                session=session
            )
            assert audit_delete.event_type == "device_delete"
        finally:
            session.close()
    
    def test_log_test_execution(self, sample_devices):
        """Test logging test execution events."""
        device = sample_devices[0]
        session = SessionLocal()
        try:
            # Test start
            audit_start = log_test_execution(
                operation="start",
                test_id=1,
                device_id=device.id,
                user_email="tester@example.com",
                user_role="engineer",
                test_name="smoke_test",
                session=session
            )
            assert audit_start.event_type == "test_start"
            assert audit_start.details["test_name"] == "smoke_test"
            
            # Test end
            audit_end = log_test_execution(
                operation="end",
                test_id=1,
                device_id=device.id,
                user_email="tester@example.com",
                user_role="engineer",
                status="passed",
                session=session
            )
            assert audit_end.event_type == "test_end"
            assert audit_end.details["status"] == "passed"
        finally:
            session.close()


class TestAuditLogQueries:
    """Test audit log query endpoints."""
    
    def test_get_audit_logs_requires_admin(self, test_client, auth_headers_engineer):
        """Test that audit log queries require admin role."""
        _, response = test_client.get("/audit/logs", headers=auth_headers_engineer)
        assert response.status == 403
    
    def test_get_audit_logs_success(self, test_client, auth_headers_admin):
        """Test querying audit logs as admin."""
        # Create some audit entries
        log_auth_attempt("user1@example.com", True)
        log_auth_attempt("user2@example.com", False, error_message="Bad password")
        
        _, response = test_client.get("/audit/logs", headers=auth_headers_admin)
        
        assert response.status == 200
        data = response.json
        assert "logs" in data
        assert "total" in data
        assert len(data["logs"]) >= 2
    
    def test_get_audit_logs_filter_by_user(self, test_client, auth_headers_admin):
        """Test filtering audit logs by user email."""
        log_auth_attempt("specific@example.com", True)
        log_auth_attempt("other@example.com", True)
        
        _, response = test_client.get(
            "/audit/logs?user_email=specific@example.com",
            headers=auth_headers_admin
        )
        
        assert response.status == 200
        logs = response.json["logs"]
        for log in logs:
            if log["user_email"]:  # Some logs might not have user_email
                assert log["user_email"] == "specific@example.com"
    
    def test_get_audit_logs_filter_by_event_type(self, test_client, auth_headers_admin):
        """Test filtering by event type."""
        log_auth_attempt("user@example.com", False, error_message="Invalid")
        
        _, response = test_client.get(
            "/audit/logs?event_type=auth_failure",
            headers=auth_headers_admin
        )
        
        assert response.status == 200
        logs = response.json["logs"]
        assert len(logs) >= 1
        assert all(log["event_type"] == "auth_failure" for log in logs)
    
    def test_get_audit_logs_time_range(self, test_client, auth_headers_admin):
        """Test filtering by time range."""
        log_auth_attempt("recent@example.com", True)
        
        # Query last 5 minutes
        _, response = test_client.get(
            "/audit/logs?since=5",
            headers=auth_headers_admin
        )
        
        assert response.status == 200
        assert response.json["total"] >= 1
    
    def test_get_audit_logs_pagination(self, test_client, auth_headers_admin):
        """Test pagination of audit logs."""
        # Create multiple entries
        for i in range(15):
            log_auth_attempt(f"user{i}@example.com", True)
        
        # Get first page
        _, response1 = test_client.get(
            "/audit/logs?limit=10&offset=0",
            headers=auth_headers_admin
        )
        assert response1.status == 200
        assert len(response1.json["logs"]) == 10
        
        # Get second page
        _, response2 = test_client.get(
            "/audit/logs?limit=10&offset=10",
            headers=auth_headers_admin
        )
        assert response2.status == 200
        assert len(response2.json["logs"]) >= 5
    
    def test_get_audit_summary(self, test_client, auth_headers_admin):
        """Test audit summary statistics."""
        # Create varied audit events
        log_auth_attempt("user1@example.com", True)
        log_auth_attempt("user2@example.com", False, error_message="Bad creds")
        log_unauthorized_access(
            "/admin/endpoint",
            "user3@example.com",
            "admin",
            "engineer"
        )
        
        _, response = test_client.get("/audit/summary", headers=auth_headers_admin)
        
        assert response.status == 200
        data = response.json
        assert "total_events" in data
        assert "by_event_type" in data
        assert "by_severity" in data
        assert "security" in data
        assert "top_users" in data
        
        security = data["security"]
        assert "failed_operations" in security
        assert "unauthorized_attempts" in security
        assert "authentication_failures" in security
    
    def test_get_event_types(self, test_client, auth_headers_admin):
        """Test getting available event types."""
        _, response = test_client.get("/audit/events/types", headers=auth_headers_admin)
        
        assert response.status == 200
        data = response.json
        assert "event_types" in data
        assert "event_categories" in data
        assert "severity_levels" in data
        assert "auth_login" in data["event_types"]
        assert "authentication" in data["event_categories"]


class TestAuditLogIntegration:
    """Test audit logging integrated with actual operations."""
    
    def test_login_creates_audit_log(self, test_client):
        """Test that login creates audit log entry."""
        session = SessionLocal()
        try:
            # Count existing logs
            before_count = session.query(AuditLog).filter(
                AuditLog.event_type == "auth_login"
            ).count()
            
            # Perform login
            _, response = test_client.post("/login", json={
                "email": "admin@example.com",
                "password": "admin123"
            })
            assert response.status == 200
            
            # Check audit log created
            after_count = session.query(AuditLog).filter(
                AuditLog.event_type == "auth_login"
            ).count()
            assert after_count == before_count + 1
            
        finally:
            session.close()
    
    def test_failed_login_creates_audit_log(self, test_client):
        """Test that failed login creates audit log entry."""
        session = SessionLocal()
        try:
            before_count = session.query(AuditLog).filter(
                AuditLog.event_type == "auth_failure"
            ).count()
            
            # Attempt bad login
            _, response = test_client.post("/login", json={
                "email": "admin@example.com",
                "password": "wrongpassword"
            })
            assert response.status == 401
            
            # Check audit log created
            after_count = session.query(AuditLog).filter(
                AuditLog.event_type == "auth_failure"
            ).count()
            assert after_count == before_count + 1
            
        finally:
            session.close()
    
    def test_unauthorized_access_creates_audit_log(self, test_client, 
                                                   auth_headers_engineer,
                                                   sample_devices):
        """Test that unauthorized access attempts are logged."""
        session = SessionLocal()
        try:
            before_count = session.query(AuditLog).filter(
                AuditLog.event_type == "unauthorized_access"
            ).count()
            
            # Try to access admin-only endpoint with engineer role
            _, response = test_client.post("/change_device_state", json={
                "device_id": sample_devices[0].id,
                "state": "maintenance"
            }, headers=auth_headers_engineer)
            assert response.status == 403
            
            # Check audit log created
            after_count = session.query(AuditLog).filter(
                AuditLog.event_type == "unauthorized_access"
            ).count()
            assert after_count == before_count + 1
            
            # Verify log details
            audit = session.query(AuditLog).filter(
                AuditLog.event_type == "unauthorized_access"
            ).order_by(AuditLog.timestamp.desc()).first()
            assert audit.user_email == "engineer@example.com"
            assert audit.endpoint == "/change_device_state"
            
        finally:
            session.close()
