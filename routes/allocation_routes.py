from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Device, AllocationHistory, Rack
from state_machine import DeviceState, can_transition, transition_device, get_valid_transitions, is_valid_state
from datetime import datetime, timedelta

allocation_routes = Blueprint("allocation_routes")


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


@allocation_routes.post("/allocate_slot")
async def allocate_slot(request):
    """Allocate a free slot to a user with optional duration."""
    session = SessionLocal()
    try:
        data = request.json
        user = data["user"]
        slot_params = data["slot"]
        duration_str = data.get("duration")  # e.g., "2h", "30m", "90m"

        if not slot_params.get("id") and not slot_params.get("platform"):
            return json({"message": "Either 'id' or 'platform' must be provided"}, status=400)
        
        # Parse duration if provided
        duration_minutes = None
        allocation_expiry = None
        if duration_str:
            duration_minutes = parse_duration(duration_str)
            if duration_minutes is None:
                return json({"error": "Invalid duration format. Use '30m', '2h', or '90m'"}, status=400)
            if duration_minutes <= 0 or duration_minutes > 10080:  # Max 1 week
                return json({"error": "Duration must be between 1 minute and 1 week (10080m)"}, status=400)
            allocation_expiry = datetime.utcnow() + timedelta(minutes=duration_minutes)

        # Allocate by slot_id if provided
        if "id" in slot_params:
            slot_id = slot_params["id"]
            slot = session.query(Device).filter(Device.id == slot_id).first()
            if not slot:
                return json({"message": f"Slot with id {slot_id} not found"}, status=404)
            if slot.state != DeviceState.FREE.value:
                return json({"message": f"Slot {slot_id} is not free (current state: {slot.state})"}, status=409)
            
            # Set owner and expiry before allocation
            slot.owner_email = user.get("email")
            if allocation_expiry:
                slot.allocation_expiry = allocation_expiry
            
            # Allocate the slot using state machine
            success, message = transition_device(slot, DeviceState.ALLOCATED.value, session)
            if not success:
                return json({"message": message}, status=400)
            
            response = {
                "message": "Slot allocated successfully",
                "slot_id": slot.id,
                "rackName": slot.rack.name,
                "rackId": slot.rack_id,
                "slotName": slot.slot_name,
                "state": slot.state,
                "owner_email": slot.owner_email
            }
            if allocation_expiry:
                response["allocation_expiry"] = allocation_expiry.isoformat()
                response["duration_minutes"] = duration_minutes
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
            
            # Set owner and expiry before allocation
            slot.owner_email = user.get("email")
            if allocation_expiry:
                slot.allocation_expiry = allocation_expiry
            
            # Allocate the slot using state machine
            success, message = transition_device(slot, DeviceState.ALLOCATED.value, session)
            if not success:
                return json({"message": message}, status=400)
            
            response = {
                "message": "Slot allocated successfully",
                "slot_id": slot.id,
                "rackName": slot.rack.name,
                "rackId": slot.rack_id,
                "slotName": slot.slot_name,
                "state": slot.state,
                "owner_email": slot.owner_email
            }
            if allocation_expiry:
                response["allocation_expiry"] = allocation_expiry.isoformat()
                response["duration_minutes"] = duration_minutes
            return json(response, status=200)

    except Exception as e:
        session.rollback()
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.post("/deallocate_slot")
async def deallocate_slot(request):
    """Deallocate a previously allocated slot, making it available to other users."""
    session = SessionLocal()
    try:
        data = request.json
        user = data["user"]
        slot_id = data["slot"]["id"]

        slot = session.query(Device).filter(Device.id == slot_id).first()

        if not slot:
            return json({"message": "Slot not found"}, status=404)

        if slot.owner_email != user["email"]:
            return json({"message": "Unauthorized: Email mismatch"}, status=403)

        # Deallocate using state machine (transition to free)
        success, message = transition_device(slot, DeviceState.FREE.value, session)
        if not success:
            return json({"message": message}, status=400)
        
        return json({"message": f"Slot {slot_id} is now free"}, status=200)
    
    except Exception as e:
        session.rollback()
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()


@allocation_routes.post("/change_device_state")
async def change_device_state(request):
    """Change device state with validation (for maintenance, offline, etc.)."""
    session = SessionLocal()
    try:
        data = request.json
        device_id = data.get("device_id")
        new_state = data.get("state")
        
        if not device_id or not new_state:
            return json({"error": "device_id and state are required"}, status=400)
        
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
        session.close()
