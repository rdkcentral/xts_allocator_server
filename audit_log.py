"""Audit logging utilities for security and compliance tracking.

This module provides functions for recording security-relevant events including:
- Authentication attempts (success/failure)
- Authorization decisions
- Privileged operations (device state changes, deletions)
- User actions (allocations, test execution)

All audit logs are persisted to the database for forensic analysis and compliance.
"""

from models import AuditLog, SessionLocal
from logging_config import get_logger
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

logger = get_logger()


# Event types
EVENT_AUTH_LOGIN = "auth_login"
EVENT_AUTH_FAILURE = "auth_failure"
EVENT_AUTH_LOGOUT = "auth_logout"
EVENT_AUTH_TOKEN_REFRESH = "auth_token_refresh"
EVENT_ALLOCATION = "allocation"
EVENT_DEALLOCATION = "deallocation"
EVENT_STATE_CHANGE = "state_change"
EVENT_DEVICE_ADD = "device_add"
EVENT_DEVICE_UPDATE = "device_update"
EVENT_DEVICE_DELETE = "device_delete"
EVENT_TEST_START = "test_start"
EVENT_TEST_END = "test_end"
EVENT_UNAUTHORIZED_ACCESS = "unauthorized_access"
EVENT_RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

# Event categories
CATEGORY_AUTHENTICATION = "authentication"
CATEGORY_AUTHORIZATION = "authorization"
CATEGORY_DEVICE_OPERATION = "device_operation"
CATEGORY_TEST_OPERATION = "test_operation"
CATEGORY_ADMIN_OPERATION = "admin_operation"

# Severity levels
SEVERITY_DEBUG = "debug"
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITY_CRITICAL = "critical"


def log_audit_event(
    event_type: str,
    event_category: str,
    action: str,
    user_email: Optional[str] = None,
    user_role: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    endpoint: Optional[str] = None,
    http_method: Optional[str] = None,
    source_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    status_code: Optional[int] = None,
    error_message: Optional[str] = None,
    severity: str = SEVERITY_INFO,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    session: Optional[Any] = None
) -> Optional[AuditLog]:
    """Log an audit event to the database.
    
    Args:
        event_type: Type of event (auth_login, allocation, etc.)
        event_category: Category of event (authentication, device_operation, etc.)
        action: Human-readable description of the action
        user_email: Email of user performing action
        user_role: Role of user at time of action
        resource_type: Type of resource affected (device, rack, etc.)
        resource_id: ID of affected resource
        endpoint: API endpoint called
        http_method: HTTP method (GET, POST, etc.)
        source_ip: IP address of request
        user_agent: User agent string
        success: Whether action succeeded
        status_code: HTTP status code
        error_message: Error message if failed
        severity: Severity level (debug, info, warning, error, critical)
        details: Additional structured data
        request_id: Unique request identifier
        session: Optional SQLAlchemy session to use (creates new if None)
    
    Returns:
        AuditLog object if successful, None if error
    """
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    
    try:
        # Generate request_id if not provided
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        audit_entry = AuditLog(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            event_category=event_category,
            severity=severity,
            user_email=user_email,
            user_role=user_role,
            source_ip=source_ip,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            endpoint=endpoint,
            http_method=http_method,
            request_id=request_id,
            success="true" if success else "false",
            status_code=status_code,
            error_message=error_message,
            details=details
        )
        
        session.add(audit_entry)
        session.commit()
        
        # Also log to application logger for immediate visibility
        log_level = {
            SEVERITY_DEBUG: logger.debug,
            SEVERITY_INFO: logger.info,
            SEVERITY_WARNING: logger.warning,
            SEVERITY_ERROR: logger.error,
            SEVERITY_CRITICAL: logger.critical
        }.get(severity, logger.info)
        
        log_level(f"AUDIT: {action} | user={user_email} role={user_role} event={event_type} "
                 f"resource={resource_type}:{resource_id} success={success} request_id={request_id}")
        
        return audit_entry
        
    except Exception as e:
        logger.error(f"Failed to create audit log entry: {e}")
        if close_session:
            session.rollback()
        return None
    finally:
        if close_session:
            session.close()


def log_auth_attempt(email: str, success: bool, source_ip: Optional[str] = None, 
                     error_message: Optional[str] = None, request_id: Optional[str] = None,
                     session: Optional[Any] = None) -> Optional[AuditLog]:
    """Log authentication attempt."""
    return log_audit_event(
        event_type=EVENT_AUTH_LOGIN if success else EVENT_AUTH_FAILURE,
        event_category=CATEGORY_AUTHENTICATION,
        action=f"User login {'succeeded' if success else 'failed'}: {email}",
        user_email=email,
        endpoint="/auth/login",
        http_method="POST",
        source_ip=source_ip,
        success=success,
        status_code=200 if success else 401,
        error_message=error_message,
        severity=SEVERITY_INFO if success else SEVERITY_WARNING,
        request_id=request_id,
        session=session
    )


def log_unauthorized_access(endpoint: str, user_email: Optional[str], required_role: str,
                           user_role: Optional[str], source_ip: Optional[str] = None,
                           request_id: Optional[str] = None, session: Optional[Any] = None) -> Optional[AuditLog]:
    """Log unauthorized access attempt."""
    return log_audit_event(
        event_type=EVENT_UNAUTHORIZED_ACCESS,
        event_category=CATEGORY_AUTHORIZATION,
        action=f"Unauthorized access attempt to {endpoint} by {user_email or 'unknown'} "
              f"(required: {required_role}, actual: {user_role or 'none'})",
        user_email=user_email,
        user_role=user_role,
        endpoint=endpoint,
        source_ip=source_ip,
        success=False,
        status_code=403,
        severity=SEVERITY_WARNING,
        details={"required_role": required_role, "user_role": user_role},
        request_id=request_id,
        session=session
    )


def log_device_allocation(device_id: int, user_email: str, user_role: str, 
                         allocation_type: str, duration: Optional[int] = None,
                         source_ip: Optional[str] = None, request_id: Optional[str] = None,
                         session: Optional[Any] = None) -> Optional[AuditLog]:
    """Log device allocation."""
    details = {"allocation_type": allocation_type}
    if duration:
        details["duration_minutes"] = duration
    
    return log_audit_event(
        event_type=EVENT_ALLOCATION,
        event_category=CATEGORY_DEVICE_OPERATION,
        action=f"Device {device_id} allocated to {user_email} ({allocation_type})",
        user_email=user_email,
        user_role=user_role,
        resource_type="device",
        resource_id=device_id,
        endpoint="/allocate_slot",
        http_method="POST",
        source_ip=source_ip,
        success=True,
        status_code=200,
        severity=SEVERITY_INFO,
        details=details,
        request_id=request_id,
        session=session
    )


def log_device_deallocation(device_id: int, user_email: str, user_role: str,
                           source_ip: Optional[str] = None, request_id: Optional[str] = None,
                           session: Optional[Any] = None) -> Optional[AuditLog]:
    """Log device deallocation."""
    return log_audit_event(
        event_type=EVENT_DEALLOCATION,
        event_category=CATEGORY_DEVICE_OPERATION,
        action=f"Device {device_id} deallocated by {user_email}",
        user_email=user_email,
        user_role=user_role,
        resource_type="device",
        resource_id=device_id,
        endpoint="/deallocate_slot",
        http_method="POST",
        source_ip=source_ip,
        success=True,
        status_code=200,
        severity=SEVERITY_INFO,
        request_id=request_id,
        session=session
    )


def log_state_change(device_id: int, old_state: str, new_state: str, 
                    user_email: str, user_role: str, source_ip: Optional[str] = None,
                    request_id: Optional[str] = None, session: Optional[Any] = None) -> Optional[AuditLog]:
    """Log device state change (privileged operation)."""
    return log_audit_event(
        event_type=EVENT_STATE_CHANGE,
        event_category=CATEGORY_ADMIN_OPERATION,
        action=f"Device {device_id} state changed from {old_state} to {new_state} by {user_email}",
        user_email=user_email,
        user_role=user_role,
        resource_type="device",
        resource_id=device_id,
        endpoint="/change_device_state",
        http_method="POST",
        source_ip=source_ip,
        success=True,
        status_code=200,
        severity=SEVERITY_INFO,
        details={"old_state": old_state, "new_state": new_state},
        request_id=request_id,
        session=session
    )


def log_device_operation(operation: str, device_id: Optional[int], user_email: str,
                        user_role: str, details: Optional[Dict] = None,
                        source_ip: Optional[str] = None, request_id: Optional[str] = None,
                        session: Optional[Any] = None) -> Optional[AuditLog]:
    """Log device add/update/delete operations."""
    event_type_map = {
        "add": EVENT_DEVICE_ADD,
        "update": EVENT_DEVICE_UPDATE,
        "delete": EVENT_DEVICE_DELETE
    }
    
    endpoint_map = {
        "add": "/add_slot",
        "update": "/update_slot",
        "delete": "/delete_slot"
    }
    
    return log_audit_event(
        event_type=event_type_map.get(operation, EVENT_DEVICE_UPDATE),
        event_category=CATEGORY_DEVICE_OPERATION,
        action=f"Device {operation} by {user_email}: device_id={device_id}",
        user_email=user_email,
        user_role=user_role,
        resource_type="device",
        resource_id=device_id,
        endpoint=endpoint_map.get(operation, f"/{operation}_slot"),
        http_method="POST",
        source_ip=source_ip,
        success=True,
        status_code=200 if operation != "add" else 201,
        severity=SEVERITY_INFO,
        details=details,
        request_id=request_id,
        session=session
    )


def log_test_execution(operation: str, test_id: Optional[int], device_id: int,
                      user_email: str, user_role: str, test_name: Optional[str] = None,
                      status: Optional[str] = None, source_ip: Optional[str] = None,
                      request_id: Optional[str] = None, session: Optional[Any] = None) -> Optional[AuditLog]:
    """Log test execution start/end."""
    event_type = EVENT_TEST_START if operation == "start" else EVENT_TEST_END
    endpoint = "/start_test" if operation == "start" else "/end_test"
    
    action = f"Test {operation} by {user_email}: device_id={device_id}"
    if test_name:
        action += f" test={test_name}"
    if status:
        action += f" status={status}"
    
    details = {}
    if test_name:
        details["test_name"] = test_name
    if status:
        details["status"] = status
    if test_id:
        details["test_execution_id"] = test_id
    
    return log_audit_event(
        event_type=event_type,
        event_category=CATEGORY_TEST_OPERATION,
        action=action,
        user_email=user_email,
        user_role=user_role,
        resource_type="test_execution",
        resource_id=test_id,
        endpoint=endpoint,
        http_method="POST",
        source_ip=source_ip,
        success=True,
        status_code=200,
        severity=SEVERITY_INFO,
        details=details if details else None,
        request_id=request_id,
        session=session
    )
