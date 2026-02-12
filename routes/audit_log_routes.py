"""Audit log query routes for viewing security events."""

from sanic import Blueprint, json as sanic_json
from models import SessionLocal, AuditLog
from sqlalchemy import desc, and_
from datetime import datetime, timedelta, timezone
from logging_config import get_logger
from auth import require_auth, ROLE_ADMIN

logger = get_logger()

audit_log_bp = Blueprint("audit_log", url_prefix="/audit")


@audit_log_bp.route("/logs", methods=["GET"])
@require_auth(ROLE_ADMIN)
async def get_audit_logs(request):
    """Query audit logs with filters (admin only).
    
    Query parameters:
        user_email: Filter by user email
        event_type: Filter by event type
        event_category: Filter by category
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        severity: Filter by severity level
        success: Filter by success (true/false)
        since: Start time (ISO format or minutes ago, e.g., "60")
        until: End time (ISO format)
        limit: Maximum results (default 100, max 1000)
        offset: Results offset for pagination
    
    Returns:
        JSON with audit log entries
    """
    session = SessionLocal()
    try:
        # Parse query parameters
        user_email = request.args.get("user_email")
        event_type = request.args.get("event_type")
        event_category = request.args.get("event_category")
        resource_type = request.args.get("resource_type")
        resource_id = request.args.get("resource_id")
        severity = request.args.get("severity")
        success = request.args.get("success")
        since = request.args.get("since")
        until = request.args.get("until")
        limit = min(int(request.args.get("limit", 100)), 1000)
        offset = int(request.args.get("offset", 0))
        
        # Build query
        query = session.query(AuditLog)
        
        # Apply filters
        if user_email:
            query = query.filter(AuditLog.user_email == user_email)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if event_category:
            query = query.filter(AuditLog.event_category == event_category)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == int(resource_id))
        if severity:
            query = query.filter(AuditLog.severity == severity)
        if success:
            query = query.filter(AuditLog.success == success.lower())
        
        # Time filters
        if since:
            try:
                # Try parsing as minutes ago
                minutes = int(since)
                since_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            except ValueError:
                # Parse as ISO timestamp
                since_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp >= since_time)
        
        if until:
            until_time = datetime.fromisoformat(until.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp <= until_time)
        
        # Get total count
        total_count = query.count()
        
        # Order by timestamp descending and apply pagination
        query = query.order_by(desc(AuditLog.timestamp))
        query = query.limit(limit).offset(offset)
        
        # Execute query
        logs = query.all()
        
        # Format results
        results = []
        for log in logs:
            results.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat() + "Z",
                "event_type": log.event_type,
                "event_category": log.event_category,
                "severity": log.severity,
                "user_email": log.user_email,
                "user_role": log.user_role,
                "source_ip": log.source_ip,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "endpoint": log.endpoint,
                "http_method": log.http_method,
                "request_id": log.request_id,
                "success": log.success == "true",
                "status_code": log.status_code,
                "error_message": log.error_message,
                "details": log.details
            })
        
        return sanic_json({
            "logs": results,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "returned": len(results)
        }, status=200)
        
    except ValueError as e:
        return sanic_json({"error": f"Invalid parameter: {e}"}, status=400)
    except Exception as e:
        logger.error(f"Failed to query audit logs: {e}")
        return sanic_json({"error": str(e)}, status=500)
    finally:
        session.close()


@audit_log_bp.route("/summary", methods=["GET"])
@require_auth(ROLE_ADMIN)
async def get_audit_summary(request):
    """Get audit log summary statistics (admin only).
    
    Query parameters:
        since: Start time (ISO format or minutes ago, default 1440 = 24 hours)
    
    Returns:
        JSON with summary statistics
    """
    session = SessionLocal()
    try:
        # Parse time range
        since = request.args.get("since", "1440")  # Default 24 hours
        try:
            minutes = int(since)
            since_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        except ValueError:
            since_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
        
        # Base query for time range
        base_query = session.query(AuditLog).filter(AuditLog.timestamp >= since_time)
        
        # Count by event type
        event_type_counts = {}
        for event_type, count in session.query(
            AuditLog.event_type, 
            AuditLog.id
        ).filter(AuditLog.timestamp >= since_time).all():
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for severity, count in session.query(
            AuditLog.severity,
            AuditLog.id
        ).filter(AuditLog.timestamp >= since_time).all():
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Failed operations (success = "false")
        failed_count = base_query.filter(AuditLog.success == "false").count()
        
        # Unauthorized access attempts
        unauthorized_count = base_query.filter(
            AuditLog.event_type == "unauthorized_access"
        ).count()
        
        # Authentication failures
        auth_failures = base_query.filter(
            AuditLog.event_type == "auth_failure"
        ).count()
        
        # Top users by activity
        user_activity = {}
        for user_email in session.query(AuditLog.user_email).filter(
            and_(AuditLog.timestamp >= since_time, AuditLog.user_email.isnot(None))
        ).all():
            email = user_email[0]
            user_activity[email] = user_activity.get(email, 0) + 1
        
        top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Most common operations
        operation_counts = {}
        for endpoint in session.query(AuditLog.endpoint).filter(
            and_(AuditLog.timestamp >= since_time, AuditLog.endpoint.isnot(None))
        ).all():
            ep = endpoint[0]
            operation_counts[ep] = operation_counts.get(ep, 0) + 1
        
        top_operations = sorted(operation_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return sanic_json({
            "time_range": {
                "since": since_time.isoformat() + "Z",
                "until": datetime.now(timezone.utc).isoformat() + "Z",
                "duration_minutes": int((datetime.now(timezone.utc) - since_time).total_seconds() / 60)
            },
            "total_events": base_query.count(),
            "by_event_type": event_type_counts,
            "by_severity": severity_counts,
            "security": {
                "failed_operations": failed_count,
                "unauthorized_attempts": unauthorized_count,
                "authentication_failures": auth_failures
            },
            "top_users": [{"email": email, "count": count} for email, count in top_users],
            "top_operations": [{"endpoint": endpoint, "count": count} for endpoint, count in top_operations]
        }, status=200)
        
    except Exception as e:
        logger.error(f"Failed to generate audit summary: {e}")
        return sanic_json({"error": str(e)}, status=500)
    finally:
        session.close()


@audit_log_bp.route("/events/types", methods=["GET"])
@require_auth(ROLE_ADMIN)
async def get_event_types(request):
    """Get list of all event types and categories (admin only)."""
    return sanic_json({
        "event_types": [
            "auth_login", "auth_failure", "auth_logout", "auth_token_refresh",
            "allocation", "deallocation", "state_change",
            "device_add", "device_update", "device_delete",
            "test_start", "test_end",
            "unauthorized_access", "rate_limit_exceeded"
        ],
        "event_categories": [
            "authentication", "authorization", "device_operation",
            "test_operation", "admin_operation"
        ],
        "severity_levels": [
            "debug", "info", "warning", "error", "critical"
        ]
    }, status=200)
