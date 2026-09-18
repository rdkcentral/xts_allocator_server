from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Device, AllocationHistory, TestExecution
from state_machine import DeviceState, transition_device
from logging_config import get_logger
from datetime import datetime, timedelta, timezone
from rate_limiter import rate_limit, user_email_identifier
from input_validation import validate_integer, validate_string, validate_email, ValidationError
from auth import require_auth, ROLE_ENGINEER
from routes.utils import ensure_utc, build_target_id

test_routes = Blueprint("test_routes")
logger = get_logger()


@test_routes.post("/start_test")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def start_test(request):
    """
    Start test execution on an allocated device.
    Transitions device to 'testing' state and creates test execution record.
    """
    session = SessionLocal()
    try:
        data = request.json
        
        # Validate inputs
        try:
            device_id = validate_integer(data.get("device_id"), "device_id", min_value=1)
            test_name = validate_string(data.get("test_name"), "test_name", max_length=255)
            test_suite = validate_string(data.get("test_suite"), "test_suite", max_length=255, required=False)
            expected_duration = validate_integer(data.get("expected_duration"), "expected_duration", 
                                                min_value=1, max_value=1440, required=False)  # Max 24 hours
            user_email = validate_email(data.get("user_email"), required=False)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        
        # Get device
        device = session.query(Device).filter(Device.id == device_id).first()
        if not device:
            return json({"error": f"Device {device_id} not found"}, status=404)
        
        # Verify device is allocated
        if device.state != DeviceState.ALLOCATED.value:
            return json({
                "error": f"Device must be in 'allocated' state to start test (current: {device.state})"
            }, status=400)
        
        # Verify ownership if user_email provided
        if user_email and device.owner_email != user_email:
            return json({
                "error": f"Device is allocated to {device.owner_email}, not {user_email}"
            }, status=403)
        
        # Find active allocation history
        active_history = session.query(AllocationHistory).filter(
            AllocationHistory.device_id == device_id,
            AllocationHistory.end_time.is_(None)
        ).order_by(AllocationHistory.start_time.desc()).first()
        
        # Check if allocation is still valid (not expired for temporary allocations)
        if device.allocation_type == "temporary" and device.allocation_expiry:
            if ensure_utc(device.allocation_expiry) < datetime.now(timezone.utc):
                return json({
                    "error": "Allocation has expired, cannot start test"
                }, status=400)
        
        # Extend allocation if test expected_duration exceeds remaining time
        if expected_duration and device.allocation_type == "temporary" and device.allocation_expiry:
            remaining_time = (ensure_utc(device.allocation_expiry) - datetime.now(timezone.utc)).total_seconds() / 60
            if expected_duration > remaining_time:
                # Extend allocation by test duration
                device.allocation_expiry = datetime.now(timezone.utc) + timedelta(minutes=expected_duration + 15)  # +15min buffer
                logger.info(f"Extended allocation for device {device_id} by {expected_duration}min for test")
        
        # Transition device to testing state
        success, message = transition_device(device, DeviceState.TESTING.value, session)
        if not success:
            return json({"error": f"Failed to transition to testing state: {message}"}, status=400)
        
        # Create test execution record
        test_execution = TestExecution(
            device_id=device_id,
            allocation_history_id=active_history.id if active_history else None,
            test_name=test_name,
            test_suite=test_suite,
            expected_duration=expected_duration,
            max_duration=data.get("max_duration", 240),  # Default 4 hours
            start_time=datetime.now(timezone.utc),
            last_heartbeat=datetime.now(timezone.utc),
            heartbeat_timeout=data.get("heartbeat_timeout", 10),  # Default 10 minutes
            test_metadata=data.get("metadata")
        )
        session.add(test_execution)
        
        # Update allocation history test count
        if active_history:
            active_history.test_execution_count = (active_history.test_execution_count or 0) + 1
        
        session.commit()
        
        logger.info(f"Test started: device_id={device_id}, test={test_name}, suite={test_suite}, execution_id={test_execution.id}")
        
        return json({
            "message": "Test started successfully",
            "test_execution_id": test_execution.id,
            "device_id": device_id,
            "device_state": device.state,
            "test_name": test_name,
            "expected_duration": expected_duration,
            "max_duration": test_execution.max_duration,
            "allocation_extended": bool(expected_duration and device.allocation_type == "temporary")
        }, status=200)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Start test error: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@test_routes.post("/test_heartbeat")
@rate_limit(max_requests=120, window_seconds=60, identifier_fn=user_email_identifier)
async def test_heartbeat(request):
    """
    Update heartbeat for active test execution.
    Keeps test execution alive and prevents hung test detection.
    """
    session = SessionLocal()
    try:
        data = request.json
        
        test_execution_id = data.get("test_execution_id")
        device_id = data.get("device_id")
        
        if not test_execution_id and not device_id:
            return json({"error": "test_execution_id or device_id is required"}, status=400)
        
        # Find test execution
        query = session.query(TestExecution).filter(TestExecution.end_time.is_(None))
        if test_execution_id:
            query = query.filter(TestExecution.id == test_execution_id)
        elif device_id:
            query = query.filter(TestExecution.device_id == device_id)
        
        test_execution = query.order_by(TestExecution.start_time.desc()).first()
        
        if not test_execution:
            return json({"error": "No active test execution found"}, status=404)
        
        # Update heartbeat
        test_execution.last_heartbeat = datetime.now(timezone.utc)
        session.commit()
        
        # Calculate time remaining
        elapsed_minutes = (datetime.now(timezone.utc) - ensure_utc(test_execution.start_time)).total_seconds() / 60
        max_remaining = test_execution.max_duration - elapsed_minutes
        
        return json({
            "message": "Heartbeat received",
            "test_execution_id": test_execution.id,
            "device_id": test_execution.device_id,
            "elapsed_minutes": round(elapsed_minutes, 2),
            "max_remaining_minutes": round(max_remaining, 2) if max_remaining > 0 else 0,
            "last_heartbeat": test_execution.last_heartbeat.isoformat() + "Z"
        }, status=200)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Test heartbeat error: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@test_routes.post("/end_test")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=60, window_seconds=60, identifier_fn=user_email_identifier)
async def end_test(request):
    """
    End test execution and transition device back to allocated state.
    Records test results and updates allocation history metrics.
    """
    session = SessionLocal()
    try:
        data = request.json
        
        test_execution_id = data.get("test_execution_id")
        device_id = data.get("device_id")
        status = data.get("status", "success")  # success, failure, error
        exit_code = data.get("exit_code")
        logs_url = data.get("logs_url")
        error_message = data.get("error_message")
        
        if not test_execution_id and not device_id:
            return json({"error": "test_execution_id or device_id is required"}, status=400)
        
        # Find test execution
        query = session.query(TestExecution).filter(TestExecution.end_time.is_(None))
        if test_execution_id:
            query = query.filter(TestExecution.id == test_execution_id)
        elif device_id:
            query = query.filter(TestExecution.device_id == device_id)
        
        test_execution = query.order_by(TestExecution.start_time.desc()).first()
        
        if not test_execution:
            return json({"error": "No active test execution found"}, status=404)
        
        # Update test execution record
        test_execution.end_time = datetime.now(timezone.utc)
        test_execution.status = status
        test_execution.exit_code = exit_code
        test_execution.logs_url = logs_url
        test_execution.error_message = error_message
        
        # Calculate test duration
        test_duration_minutes = (ensure_utc(test_execution.end_time) - ensure_utc(test_execution.start_time)).total_seconds() / 60
        
        # Update allocation history with test time
        if test_execution.allocation_history_id:
            history = session.query(AllocationHistory).filter(
                AllocationHistory.id == test_execution.allocation_history_id
            ).first()
            if history:
                history.total_test_time = (history.total_test_time or 0) + int(test_duration_minutes)
        
        # Get device and transition back to allocated
        device = session.query(Device).filter(Device.id == test_execution.device_id).first()
        if device:
            if device.state == DeviceState.TESTING.value:
                success, message = transition_device(device, DeviceState.ALLOCATED.value, session)
                if not success:
                    logger.warning(f"Failed to transition device {device.id} back to allocated: {message}")
        
        session.commit()
        
        logger.info(f"Test ended: device_id={test_execution.device_id}, test={test_execution.test_name}, status={status}, duration={test_duration_minutes:.2f}min")
        
        return json({
            "message": "Test ended successfully",
            "test_execution_id": test_execution.id,
            "device_id": test_execution.device_id,
            "device_state": device.state if device else "unknown",
            "status": status,
            "duration_minutes": round(test_duration_minutes, 2),
            "exit_code": exit_code
        }, status=200)
    
    except Exception as e:
        session.rollback()
        logger.error(f"End test error: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@test_routes.get("/test_executions")
async def list_test_executions(request):
    """
    List test executions with optional filtering.
    Query parameters: device_id, status, active_only, limit
    """
    session = SessionLocal()
    try:
        query = session.query(TestExecution)
        
        # Filter by device
        device_id = request.args.get("device_id")
        if device_id:
            query = query.filter(TestExecution.device_id == int(device_id))
        
        # Filter by status
        status = request.args.get("status")
        if status:
            query = query.filter(TestExecution.status == status)
        
        # Filter active only
        active_only = request.args.get("active_only", "false").lower() == "true"
        if active_only:
            query = query.filter(TestExecution.end_time.is_(None))
        
        # Limit results
        limit = int(request.args.get("limit", 50))
        query = query.order_by(TestExecution.start_time.desc()).limit(limit)
        
        executions = query.all()
        
        results = []
        for ex in executions:
            duration = None
            if ex.end_time:
                duration = (ensure_utc(ex.end_time) - ensure_utc(ex.start_time)).total_seconds() / 60
            
            results.append({
                "id": ex.id,
                "device_id": ex.device_id,
                "test_name": ex.test_name,
                "test_suite": ex.test_suite,
                "status": ex.status,
                "start_time": ex.start_time.isoformat() + "Z",
                "end_time": ex.end_time.isoformat() + "Z" if ex.end_time else None,
                "duration_minutes": round(duration, 2) if duration else None,
                "exit_code": ex.exit_code,
                "logs_url": ex.logs_url
            })
        
        return json({
            "test_executions": results,
            "total": len(results)
        }, status=200)
    
    except Exception as e:
        logger.error(f"List test executions error: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@test_routes.get("/device/<device_id:int>/box_status")
@rate_limit(max_requests=120, window_seconds=60)
async def get_box_status(request, device_id):
    """Compact box-status payload for RAFT/XTS polling.

    Returns the minimum a polling client needs: device state, target_id,
    current owner, active test summary (if any) with elapsed minutes and
    heartbeat age in seconds, allocation expiry. No rack metadata, no
    historical lists — keep this lightweight so it can be polled often.
    """
    session = SessionLocal()
    try:
        device = session.query(Device).filter(Device.id == device_id).first()
        if not device:
            return json({"error": f"Device {device_id} not found"}, status=404)

        now = datetime.now(timezone.utc)

        active = (
            session.query(TestExecution)
            .filter(
                TestExecution.device_id == device_id,
                TestExecution.end_time.is_(None),
            )
            .order_by(TestExecution.start_time.desc())
            .first()
        )
        active_test = None
        if active is not None:
            elapsed = (now - ensure_utc(active.start_time)).total_seconds() / 60
            heartbeat_age = None
            if active.last_heartbeat is not None:
                heartbeat_age = (now - ensure_utc(active.last_heartbeat)).total_seconds()
            active_test = {
                "id": active.id,
                "name": active.test_name,
                "suite": active.test_suite,
                "status": active.status,
                "elapsed_minutes": round(elapsed, 2),
                "heartbeat_age_seconds": round(heartbeat_age, 1) if heartbeat_age is not None else None,
            }

        return json({
            "device_id": device.id,
            "target_id": build_target_id(device),
            "state": device.state,
            "owner_email": device.owner_email,
            "allocation_expiry": device.allocation_expiry.isoformat() if device.allocation_expiry else None,
            "active_test": active_test,
        }, status=200)
    except Exception as e:
        logger.error(f"box_status error for device {device_id}: {e}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()
