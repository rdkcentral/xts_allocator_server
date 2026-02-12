from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Device, AllocationHistory, Rack
from state_machine import DeviceState, can_transition, transition_device, get_valid_transitions, is_valid_state
from logging_config import get_logger
from datetime import datetime, timedelta, timezone
from rate_limiter import rate_limit, user_email_identifier
from input_validation import validate_user_data, validate_integer, validate_string, ValidationError
from auth import require_auth, ROLE_ENGINEER, ROLE_ADMIN, get_user_from_request
from sqlalchemy import func

allocation_routes = Blueprint("allocation_routes")
logger = get_logger()


def parse_duration(duration_str):
    """
    Parse duration string to minutes.
    Supports: '30m', '2h', '1.5h', '90m'
    Returns: minutes as integer, or None if invalid
    """
    if not duration_str:
        return None
    
    duration_str = duration_str.strip().lower()
    try:
        if duration_str.endswith('m'):
            return int(duration_str[:-1])
        elif duration_str.endswith('h'):
            hours = float(duration_str[:-1])
            return int(hours * 60)
        else:
            # Assume minutes if no unit
            return int(duration_str)
    except (ValueError, AttributeError):
        return None


from routes.utils import build_target_id, ensure_utc


def parse_target_id(target_id):
    """
    Parse target id formats:
      - platform@rack/slot
      - rack/slot
      - platform
    Returns a dict with optional platform, rack_name, slot_name.
    """
    token = (target_id or "").strip()
    if not token:
        return {"platform": None, "rack_name": None, "slot_name": None}

    platform = None
    location = token
    if "@" in token:
        left, right = token.split("@", 1)
        platform = left.strip() or None
        location = right.strip()

    rack_name = None
    slot_name = None
    if "/" in location:
        rack_name, slot_name = location.split("/", 1)
        rack_name = rack_name.strip() or None
        slot_name = slot_name.strip() or None
    elif not platform:
        platform = location.strip() or None

    return {
        "platform": platform,
        "rack_name": rack_name,
        "slot_name": slot_name,
    }


def allocate_device(session, slot, user, duration_minutes, allocation_expiry):
    """Apply allocation state transition, create history, and return response payload."""
    # Set owner and expiry before allocation
    slot.owner_email = user.get("email")
    slot.allocation_type = "temporary"
    if allocation_expiry:
        slot.allocation_expiry = allocation_expiry

    # Record state before allocation
    state_before = slot.state

    # Allocate the slot using state machine
    success, message = transition_device(slot, DeviceState.ALLOCATED.value, session)
    if not success:
        return None, json({"message": message}, status=400)

    # Create allocation history record
    history = AllocationHistory(
        device_id=slot.id,
        user=user.get("username"),
        email=user.get("email"),
        name=user.get("name"),
        start_time=datetime.now(timezone.utc),
        duration_requested=duration_minutes,
        allocation_type="temporary",
        state_before=state_before,
        software_version=slot.software_version
    )
    session.add(history)
    session.commit()

    response = {
        "message": "Slot allocated successfully",
        "slot_id": slot.id,
        "target_id": build_target_id(slot),
        "rackName": slot.rack.name,
        "rackId": slot.rack_id,
        "slotName": slot.slot_name,
        "state": slot.state,
        "owner_email": slot.owner_email,
        "allocation_history_id": history.id
    }
    if allocation_expiry:
        response["allocation_expiry"] = allocation_expiry.isoformat()
        response["duration_minutes"] = duration_minutes

    return response, None


def _normalize_metrics(metrics):
    """Return mutable dict for device.system_metrics."""
    if isinstance(metrics, dict):
        return dict(metrics)
    return {}


@allocation_routes.post("/allocate_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def allocate_slot(request):
    """Allocate a free slot to a user with optional duration."""
    session = SessionLocal()
    try:
        data = request.json
        
        # Validate user data
        try:
            validate_user_data(data.get("user", {}))
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        
        user = data["user"]
        slot_params = data["slot"]
        duration_str = data.get("duration")  # e.g., "2h", "30m", "90m"

        if not slot_params.get("id") and not slot_params.get("platform") and not slot_params.get("target_id"):
            return json({"message": "Either 'id', 'platform', or 'target_id' must be provided"}, status=400)
        
        # Validate duration string if provided
        if duration_str:
            try:
                duration_str = validate_string(duration_str, "duration", max_length=20, required=False)
            except ValidationError as e:
                return json({"error": str(e)}, status=400)
        
        # Parse duration if provided
        duration_minutes = None
        allocation_expiry = None
        if duration_str:
            duration_minutes = parse_duration(duration_str)
            if duration_minutes is None:
                return json({"error": "Invalid duration format. Use '30m', '2h', or '90m'"}, status=400)
            if duration_minutes <= 0 or duration_minutes > 10080:  # Max 1 week
                return json({"error": "Duration must be between 1 minute and 1 week (10080m)"}, status=400)
            allocation_expiry = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

        # Allocate by slot_id if provided
        if "id" in slot_params:
            # Validate slot_id
            try:
                slot_id = validate_integer(slot_params["id"], "slot_id", min_value=1)
            except ValidationError as e:
                return json({"error": str(e)}, status=400)
            
            slot = session.query(Device).filter(Device.id == slot_id).first()
            if not slot:
                return json({"message": f"Slot with id {slot_id} not found"}, status=404)
            if slot.state != DeviceState.FREE.value:
                return json({"message": f"Slot {slot_id} is not free (current state: {slot.state})"}, status=409)
            
            response, error_response = allocate_device(
                session=session,
                slot=slot,
                user=user,
                duration_minutes=duration_minutes,
                allocation_expiry=allocation_expiry
            )
            if error_response:
                return error_response
            
            logger.info(
                f"Slot allocated by ID: device_id={slot.id}, rack={slot.rack.name}, "
                f"slot={slot.slot_name}, target_id={build_target_id(slot)}, "
                f"email={user.get('email')}, duration={duration_minutes}m, "
                f"history_id={response['allocation_history_id']}"
            )
            return json(response, status=200)

        # Allocate by target_id (slot-first, platform fallback)
        elif "target_id" in slot_params:
            try:
                target_id = validate_string(slot_params.get("target_id"), "target_id", max_length=255)
            except ValidationError as e:
                return json({"error": str(e)}, status=400)

            parsed = parse_target_id(target_id)
            platform = parsed.get("platform")
            rack_name = parsed.get("rack_name")
            slot_name = parsed.get("slot_name")
            slot = None

            # 1) Prefer explicit rack/slot match when present.
            if rack_name and slot_name:
                query = session.query(Device).join(Rack).filter(
                    Device.state == DeviceState.FREE.value,
                    func.lower(Rack.name) == rack_name.lower(),
                    func.lower(Device.slot_name) == slot_name.lower()
                )
                if platform:
                    query = query.filter(func.lower(Device.platform) == platform.lower())
                slot = query.first()

            # 2) Fallback to platform allocation if slot lookup misses or target only encodes platform.
            if not slot and platform:
                slot = session.query(Device).filter(
                    Device.state == DeviceState.FREE.value,
                    func.lower(Device.platform) == platform.lower()
                ).first()

            if not slot:
                return json({
                    "message": "No free slot matches the criteria",
                    "target_id": target_id,
                    "slots": []
                }, status=200)

            response, error_response = allocate_device(
                session=session,
                slot=slot,
                user=user,
                duration_minutes=duration_minutes,
                allocation_expiry=allocation_expiry
            )
            if error_response:
                return error_response

            logger.info(
                f"Slot allocated by target_id: device_id={slot.id}, rack={slot.rack.name}, "
                f"slot={slot.slot_name}, target_id={build_target_id(slot)}, "
                f"email={user.get('email')}, duration={duration_minutes}m, "
                f"history_id={response['allocation_history_id']}"
            )
            return json(response, status=200)

        # Allocate by platform/tags
        else:
            query = session.query(Device).filter(Device.state == DeviceState.FREE.value, Device.platform == slot_params["platform"])
            if "tags" in slot_params:
                tags = ",".join(slot_params["tags"])
                query = query.filter(Device.tags.contains(tags))
            slot = query.first()
            if not slot:
                return json({"message": "No free slot matches the criteria", "slots":[]}, status=200)
            
            response, error_response = allocate_device(
                session=session,
                slot=slot,
                user=user,
                duration_minutes=duration_minutes,
                allocation_expiry=allocation_expiry
            )
            if error_response:
                return error_response
            
            logger.info(
                f"Slot allocated by platform: device_id={slot.id}, rack={slot.rack.name}, "
                f"slot={slot.slot_name}, target_id={build_target_id(slot)}, "
                f"platform={slot.platform}, email={user.get('email')}, "
                f"duration={duration_minutes}m, history_id={response['allocation_history_id']}"
            )
            return json(response, status=200)

    except Exception as e:
        session.rollback()
        logger.error(f"Allocation error: {str(e)}", exc_info=True)
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.post("/deallocate_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def deallocate_slot(request):
    """Deallocate a previously allocated slot, making it available to other users."""
    session = SessionLocal()
    try:
        data = request.json
        
        # Validate user data
        try:
            validate_user_data(data.get("user", {}))
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        
        user = data["user"]
        
        # Validate slot_id
        try:
            slot_id = validate_integer(data["slot"]["id"], "slot_id", min_value=1)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)

        slot = session.query(Device).filter(Device.id == slot_id).first()

        if not slot:
            return json({"message": "Slot not found"}, status=404)

        if slot.owner_email != user["email"]:
            return json({"message": "Unauthorized: Email mismatch"}, status=403)

        # Find active allocation history record
        active_history = session.query(AllocationHistory).filter(
            AllocationHistory.device_id == slot_id,
            AllocationHistory.email == user["email"],
            AllocationHistory.end_time.is_(None)
        ).order_by(AllocationHistory.start_time.desc()).first()
        
        # Record state before deallocation
        state_after = DeviceState.FREE.value
        
        # Deallocate using state machine (transition to free)
        success, message = transition_device(slot, DeviceState.FREE.value, session)
        if not success:
            return json({"message": message}, status=400)
        
        # Update allocation history record
        if active_history:
            active_history.end_time = datetime.now(timezone.utc)
            active_history.state_after = state_after
            session.commit()
            logger.info(f"Slot deallocated: device_id={slot_id}, email={user['email']}, history_id={active_history.id}, duration_actual={(ensure_utc(active_history.end_time) - ensure_utc(active_history.start_time)).total_seconds() / 60:.1f}m")
        else:
            logger.warning(f"Slot deallocated but no active history found: device_id={slot_id}, email={user['email']}")
        
        return json({"message": "Slot deallocated successfully"}, status=200)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Deallocation error: {str(e)}", exc_info=True)
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.post("/borrow_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def borrow_slot(request):
    """
    Borrow an allocated/permanent device when the current owner is unavailable.
    Temporarily transfers ownership to borrower and records original owner in metadata.
    """
    session = SessionLocal()
    try:
        data = request.json

        # Validate user data
        try:
            validate_user_data(data.get("user", {}))
        except ValidationError as e:
            return json({"error": str(e)}, status=400)

        user = data["user"]

        try:
            slot_id = validate_integer(data.get("slot", {}).get("id"), "slot_id", min_value=1)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)

        duration_str = data.get("duration", "4h")
        try:
            duration_str = validate_string(duration_str, "duration", max_length=20, required=False) or "4h"
        except ValidationError as e:
            return json({"error": str(e)}, status=400)

        duration_minutes = parse_duration(duration_str)
        if duration_minutes is None:
            return json({"error": "Invalid duration format. Use '30m', '2h', or '90m'"}, status=400)
        if duration_minutes <= 0 or duration_minutes > 10080:
            return json({"error": "Duration must be between 1 minute and 1 week (10080m)"}, status=400)

        reason = None
        if "reason" in data:
            try:
                reason = validate_string(data.get("reason"), "reason", min_length=1, max_length=200, required=False)
            except ValidationError as e:
                return json({"error": str(e)}, status=400)

        slot = session.query(Device).filter(Device.id == slot_id).first()
        if not slot:
            return json({"message": f"Slot with id {slot_id} not found"}, status=404)

        if slot.state == DeviceState.FREE.value:
            return json({"message": f"Slot {slot_id} is free; use allocate command instead"}, status=409)
        if slot.state == DeviceState.TESTING.value:
            return json({"message": f"Slot {slot_id} is actively testing and cannot be borrowed"}, status=409)
        if not slot.owner_email:
            return json({"message": f"Slot {slot_id} has no current owner and cannot be borrowed"}, status=409)
        if slot.owner_email == user["email"]:
            return json({"message": "Borrower already owns this slot"}, status=400)

        metrics = _normalize_metrics(slot.system_metrics)
        borrow_meta = metrics.get("borrow") if isinstance(metrics.get("borrow"), dict) else None
        if borrow_meta and borrow_meta.get("active"):
            return json({
                "message": f"Slot {slot_id} is already borrowed",
                "borrowed_by": borrow_meta.get("borrowed_by_email"),
                "original_owner": borrow_meta.get("original_owner_email")
            }, status=409)

        original_owner = slot.owner_email
        original_allocation_type = slot.allocation_type or "temporary"
        original_expiry = slot.allocation_expiry.isoformat() if slot.allocation_expiry else None

        now = datetime.now(timezone.utc)
        borrow_expiry = now + timedelta(minutes=duration_minutes)

        # Close current owner's active allocation history record, if present.
        owner_history = session.query(AllocationHistory).filter(
            AllocationHistory.device_id == slot_id,
            AllocationHistory.email == original_owner,
            AllocationHistory.end_time.is_(None)
        ).order_by(AllocationHistory.start_time.desc()).first()
        if owner_history:
            owner_history.end_time = now
            owner_history.state_after = "borrowed_out"

        # Apply borrow ownership.
        slot.owner_email = user["email"]
        slot.allocation_type = "temporary"
        slot.allocation_expiry = borrow_expiry

        metrics["borrow"] = {
            "active": True,
            "original_owner_email": original_owner,
            "original_allocation_type": original_allocation_type,
            "original_allocation_expiry": original_expiry,
            "borrowed_by_email": user["email"],
            "borrowed_at": now.isoformat(),
            "reason": reason
        }
        slot.system_metrics = metrics

        borrow_history = AllocationHistory(
            device_id=slot.id,
            user=user.get("username"),
            email=user.get("email"),
            name=user.get("name"),
            start_time=now,
            duration_requested=duration_minutes,
            allocation_type="borrowed",
            state_before=slot.state,
            software_version=slot.software_version
        )
        session.add(borrow_history)
        session.commit()

        logger.info(
            f"Slot borrowed: device_id={slot.id}, borrowed_by={user.get('email')}, "
            f"original_owner={original_owner}, expires={borrow_expiry.isoformat()}, "
            f"history_id={borrow_history.id}"
        )

        return json({
            "message": "Slot borrowed successfully",
            "slot_id": slot.id,
            "target_id": build_target_id(slot),
            "state": slot.state,
            "owner_email": slot.owner_email,
            "borrowed_from_email": original_owner,
            "borrow_expires": borrow_expiry.isoformat(),
            "duration_minutes": duration_minutes,
            "allocation_history_id": borrow_history.id
        }, status=200)

    except Exception as e:
        session.rollback()
        logger.error(f"Borrow slot error: {str(e)}", exc_info=True)
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.post("/return_borrowed_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def return_borrowed_slot(request):
    """Return a borrowed slot to its original owner."""
    session = SessionLocal()
    try:
        data = request.json

        # Validate user data
        try:
            validate_user_data(data.get("user", {}))
        except ValidationError as e:
            return json({"error": str(e)}, status=400)

        user = data["user"]
        requester = get_user_from_request(request) or {}
        requester_role = requester.get("role")

        try:
            slot_id = validate_integer(data.get("slot", {}).get("id"), "slot_id", min_value=1)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)

        slot = session.query(Device).filter(Device.id == slot_id).first()
        if not slot:
            return json({"message": f"Slot with id {slot_id} not found"}, status=404)

        metrics = _normalize_metrics(slot.system_metrics)
        borrow_meta = metrics.get("borrow") if isinstance(metrics.get("borrow"), dict) else None
        if not borrow_meta or not borrow_meta.get("active"):
            return json({"message": f"Slot {slot_id} is not currently borrowed"}, status=400)

        current_borrower = slot.owner_email
        if current_borrower != user["email"] and requester_role != ROLE_ADMIN:
            return json({"message": "Only current borrower or admin can return borrowed slot"}, status=403)

        original_owner = borrow_meta.get("original_owner_email")
        if not original_owner:
            return json({"message": "Borrow metadata is incomplete: missing original owner"}, status=500)

        previous_type = borrow_meta.get("original_allocation_type") or "temporary"
        if previous_type not in {"temporary", "permanent"}:
            previous_type = "temporary"

        previous_expiry = borrow_meta.get("original_allocation_expiry")

        now = datetime.now(timezone.utc)

        # Close borrower's active history
        borrower_history = session.query(AllocationHistory).filter(
            AllocationHistory.device_id == slot_id,
            AllocationHistory.email == current_borrower,
            AllocationHistory.end_time.is_(None)
        ).order_by(AllocationHistory.start_time.desc()).first()
        if borrower_history:
            borrower_history.end_time = now
            borrower_history.state_after = "returned"

        # Restore original ownership
        slot.owner_email = original_owner
        slot.allocation_type = previous_type
        if previous_type == "temporary" and previous_expiry:
            try:
                slot.allocation_expiry = datetime.fromisoformat(previous_expiry)
            except ValueError:
                slot.allocation_expiry = None
        else:
            slot.allocation_expiry = None

        metrics.pop("borrow", None)
        slot.system_metrics = metrics if metrics else None

        restored_history = AllocationHistory(
            device_id=slot.id,
            user=original_owner.split("@")[0] if "@" in original_owner else original_owner,
            email=original_owner,
            name=None,
            start_time=now,
            duration_requested=None,
            allocation_type=slot.allocation_type,
            state_before=slot.state,
            software_version=slot.software_version
        )
        session.add(restored_history)
        session.commit()

        logger.info(
            f"Borrow returned: device_id={slot.id}, returned_by={user.get('email')}, "
            f"restored_owner={original_owner}, history_id={restored_history.id}"
        )

        return json({
            "message": "Borrowed slot returned successfully",
            "slot_id": slot.id,
            "target_id": build_target_id(slot),
            "state": slot.state,
            "owner_email": slot.owner_email,
            "allocation_type": slot.allocation_type,
            "allocation_expiry": slot.allocation_expiry.isoformat() if slot.allocation_expiry else None,
            "allocation_history_id": restored_history.id
        }, status=200)

    except Exception as e:
        session.rollback()
        logger.error(f"Return borrowed slot error: {str(e)}", exc_info=True)
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.post("/change_device_state")
@require_auth(ROLE_ADMIN)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def change_device_state(request):
    """Change device state with validation (for maintenance, offline, etc.)."""
    session = SessionLocal()
    try:
        data = request.json
        
        # Validate device_id
        try:
            device_id = validate_integer(data.get("device_id"), "device_id", min_value=1)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        
        # Validate new_state
        try:
            new_state = validate_string(data.get("state"), "state", max_length=20)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        
        if not is_valid_state(new_state):
            return json({
                "error": f"Invalid state: {new_state}",
                "valid_states": [s.value for s in DeviceState]
            }, status=400)
        
        device = session.query(Device).filter(Device.id == device_id).first()
        if not device:
            return json({"error": "Device not found"}, status=404)
        
        # Perform state transition
        success, message = transition_device(device, new_state, session)
        
        if success:
            return json({
                "message": message,
                "device_id": device.id,
                "previous_state": message.split("from ")[1].split(" to")[0] if "from" in message else None,
                "new_state": device.state,
                "state_changed_at": device.state_changed_at.isoformat() if device.state_changed_at else None
            }, status=200)
        else:
            return json({"error": message}, status=400)
    
    except Exception as e:
        session.rollback()
        return json({"error": "Internal server error", "details": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.get("/device/<device_id:int>/valid_states")
async def get_valid_states(request, device_id):
    """Get valid state transitions for a device."""
    session = SessionLocal()
    try:
        device = session.query(Device).filter(Device.id == device_id).first()
        if not device:
            return json({"error": "Device not found"}, status=404)
        
        valid_transitions = get_valid_transitions(device.state)
        
        return json({
            "device_id": device.id,
            "current_state": device.state,
            "valid_transitions": valid_transitions,
            "state_changed_at": device.state_changed_at.isoformat() if device.state_changed_at else None
        }, status=200)
    finally:
        session.close()


@allocation_routes.get("/allocation_history")
async def get_allocation_history(request):
    """Get allocation history with optional filters."""
    session = SessionLocal()
    try:
        # Parse query parameters
        device_id = request.args.get("device_id")
        email = request.args.get("email")
        start_date = request.args.get("start_date")  # ISO format: 2026-02-01
        end_date = request.args.get("end_date")
        limit = request.args.get("limit", "100")
        
        # Build query
        query = session.query(AllocationHistory).join(Device)
        
        if device_id:
            query = query.filter(AllocationHistory.device_id == int(device_id))
        if email:
            query = query.filter(AllocationHistory.email == email)
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(AllocationHistory.start_time >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(AllocationHistory.start_time <= end_dt)
        
        # Order by most recent first and limit results
        query = query.order_by(AllocationHistory.start_time.desc())
        query = query.limit(int(limit))
        
        history_records = query.all()
        
        # Format response
        history_list = []
        for record in history_records:
            duration_actual = None
            if record.end_time and record.start_time:
                duration_actual = int((ensure_utc(record.end_time) - ensure_utc(record.start_time)).total_seconds() / 60)
            
            history_list.append({
                "id": record.id,
                "device_id": record.device_id,
                "target_id": build_target_id(record.device),
                "device_name": f"{record.device.rack.name}_{record.device.slot_name}",
                "platform": record.device.platform,
                "user": record.user,
                "email": record.email,
                "name": record.name,
                "start_time": record.start_time.isoformat() if record.start_time else None,
                "end_time": record.end_time.isoformat() if record.end_time else None,
                "duration_requested": record.duration_requested,
                "duration_actual": duration_actual,
                "state_before": record.state_before,
                "state_after": record.state_after,
                "software_version": record.software_version,
                "is_active": record.end_time is None
            })
        
        return json({
            "count": len(history_list),
            "history": history_list
        }, status=200)
        
    except ValueError as e:
        return json({"error": f"Invalid parameter: {str(e)}"}, status=400)
    except Exception as e:
        return json({"error": str(e)}, status=500)
    finally:
        session.close()

@allocation_routes.post("/allocate_permanent")
async def allocate_permanent(request):
    """
    Allocate a device permanently to a user (no expiry).
    Intended for desk boxes and long-term assignments.
    """
    session = SessionLocal()
    try:
        data = request.json
        user = data["user"]
        slot_params = data["slot"]

        if not slot_params.get("id"):
            return json({"message": "'id' must be provided for permanent allocation"}, status=400)
        
        slot_id = slot_params["id"]
        slot = session.query(Device).filter(Device.id == slot_id).first()
        
        if not slot:
            return json({"message": f"Slot with id {slot_id} not found"}, status=404)
        if slot.state != DeviceState.FREE.value:
            return json({"message": f"Slot {slot_id} is not free (current state: {slot.state})"}, status=409)
        
        # Set owner for permanent allocation (no expiry)
        slot.owner_email = user.get("email")
        slot.allocation_type = "permanent"
        slot.allocation_expiry = None
        
        # Record state before allocation
        state_before = slot.state
        
        # Allocate the slot using state machine
        success, message = transition_device(slot, DeviceState.ALLOCATED.value, session)
        if not success:
            return json({"message": message}, status=400)
        
        # Create allocation history record
        history = AllocationHistory(
            device_id=slot.id,
            user=user.get("username"),
            email=user.get("email"),
            name=user.get("name"),
            start_time=datetime.now(timezone.utc),
            duration_requested=None,  # No duration for permanent
            allocation_type="permanent",
            state_before=state_before,
            software_version=slot.software_version
        )
        session.add(history)
        session.commit()
        
        logger.info(f"Permanent allocation: device_id={slot.id}, rack={slot.rack.name}, slot={slot.slot_name}, email={user.get('email')}, history_id={history.id}")
        
        response = {
            "message": "Slot allocated permanently",
            "slot_id": slot.id,
            "target_id": build_target_id(slot),
            "rackName": slot.rack.name,
            "rackId": slot.rack_id,
            "slotName": slot.slot_name,
            "state": slot.state,
            "owner_email": slot.owner_email,
            "allocation_type": "permanent",
            "allocation_history_id": history.id
        }
        return json(response, status=200)

    except Exception as e:
        session.rollback()
        logger.error(f"Permanent allocation error: {str(e)}", exc_info=True)
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.post("/report_status")
async def report_status(request):
    """
    Allow XTS or external tools to report device status.
    Updates last_seen, connectivity_status, software_version, and system_metrics.
    """
    session = SessionLocal()
    try:
        data = request.json
        device_id = data.get("device_id")
        
        if not device_id:
            return json({"error": "device_id is required"}, status=400)
        
        device = session.query(Device).filter(Device.id == device_id).first()
        if not device:
            return json({"error": f"Device {device_id} not found"}, status=404)
        
        # Update status fields
        device.last_seen = datetime.now(timezone.utc)
        
        if "connectivity_status" in data:
            device.connectivity_status = data["connectivity_status"]
        
        if "software_version" in data:
            device.software_version = data["software_version"]
        
        if "system_metrics" in data:
            device.system_metrics = data["system_metrics"]
        
        session.commit()
        
        logger.info(f"Status report for device {device_id}: connectivity={device.connectivity_status}, software={device.software_version}")
        
        return json({
            "message": "Status updated successfully",
            "device_id": device_id,
            "last_seen": device.last_seen.isoformat() + "Z",
            "connectivity_status": device.connectivity_status
        }, status=200)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Status report error: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()
