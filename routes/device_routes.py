from sanic import Blueprint
from sanic.response import json
from sqlalchemy import func
from models import SessionLocal, Device, Rack
from rate_limiter import rate_limit, user_email_identifier
from auth import require_auth, ROLE_ENGINEER, ROLE_READONLY

device_routes = Blueprint("device_routes")

@device_routes.get("/list_slots")
async def list_slots(request):
    """Retrieve all available slots from the database."""
    session = SessionLocal()
    try:
        slots = session.query(Device).all()
        slots_list = [
            {
                "slot_id": slot.id,
                "id": slot.id,  # Add id for compatibility
                "rackName": slot.rack.name,
                "rackId": slot.rack_id,
                "rackLocation": slot.rack.location,
                "rackBuilding": slot.rack.building,
                "slotName": slot.slot_name,
                "platform": slot.platform,
                "description": slot.description,
                "tags": slot.tags.split(",") if slot.tags else [],
                "state": slot.state,
                "owner_email": slot.owner_email,
                "allocation_type": slot.allocation_type,
                "allocation_expiry": slot.allocation_expiry.isoformat() if slot.allocation_expiry else None,
                "make": slot.make,
                "model": slot.model,
                "external_equipment": slot.external_equipment or [],
            }
            for slot in slots
        ]
        return json({"slots": slots_list}, status=200)
    finally:
        session.close()


@device_routes.post("/list_slots")
@rate_limit(max_requests=60, window_seconds=60, identifier_fn=user_email_identifier)
async def list_slots_filters(request):
    """Retrieve slots from the database based on specific filter criteria."""
    session = SessionLocal()
    try:
        criteria = request.json
        query = session.query(Device)

        if "platform" in criteria:
            query = query.filter(Device.platform == criteria["platform"])
        if "description" in criteria:
            query = query.filter(Device.description.like(f"%{criteria['description']}%"))
        if "tags" in criteria:
            tags = ",".join(criteria["tags"])
            query = query.filter(Device.tags.contains(tags))

        matching_slots = [
            {
                "slot_id": slot.id,
                "rackName": slot.rack.name,
                "rackId": slot.rack_id,
                "slotName": slot.slot_name,
                "platform": slot.platform,
                "description": slot.description,
                "tags": slot.tags.split(",") if slot.tags else [],
                "state": slot.state,
                "owner_email": slot.owner_email,
                "allocation_expiry": slot.allocation_expiry.isoformat() if slot.allocation_expiry else None
            }
            for slot in query.all()
        ]
        return json({"slots": matching_slots}, status=200)
    finally:
        session.close()

def update_slot_fields(slot, data, session):
    """Helper function to update a slot's attributes."""
    if "rackName" in data:
        # Find or create rack by name
        rack = session.query(Rack).filter(Rack.name == data["rackName"]).first()
        if not rack:
            rack = Rack(name=data["rackName"])
            session.add(rack)
            session.flush()  # Get the rack.id
        slot.rack_id = rack.id
    if "slotName" in data:
        slot.slot_name = data["slotName"]
    if "platform" in data:
        slot.platform = data["platform"]
    if "description" in data:
        slot.description = data["description"]
    if "tags" in data:
        slot.tags = ",".join(data["tags"]) if isinstance(data["tags"], list) else data["tags"]

@device_routes.post("/add_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=20, window_seconds=60, identifier_fn=user_email_identifier)
async def add_slot(request):
    """Add a new slot to the database."""
    session = SessionLocal()
    try:
        data = request.json

        if "rackName" not in data or "slotName" not in data:
            return json({"error": "Missing required fields: rackName and slotName"}, status=400)

        # Find or create rack
        rack = session.query(Rack).filter(Rack.name == data["rackName"]).first()
        if not rack:
            rack = Rack(name=data["rackName"])
            session.add(rack)
            session.flush()  # Get the rack.id

        new_slot = Device(
            rack_id=rack.id,
            slot_name=data["slotName"],
            platform=data.get("platform", ""), 
            description=data.get("description", ""), 
            tags=",".join(data["tags"]) if "tags" in data and isinstance(data["tags"], list) else data.get("tags", ""), 
            state=data.get("state", "free"),
            owner_email=data.get("owner_email")
        )
            
        session.add(new_slot)
        session.commit()

        # to get the new generated id from the db
        session.refresh(new_slot)

        return json({"message": "Slot added successfully", "slot_id": new_slot.id}, status=201)

    except Exception as e:
        session.rollback()
        return json({"error": str(e)}, status=500)
    finally:
        session.close()

@device_routes.post("/update_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def update_slot_info(request):
    """Update an existing slot in the database."""
    session = SessionLocal()
    try:
        data = request.json
        slot_id = data.get("slot_id")

        if not slot_id:
            return json({"error": "Slot ID is required"}, status=400)

        slot = session.query(Device).filter(Device.id == slot_id).first()
        if not slot:
            return json({"error": "Slot not found"}, status=404)

        update_slot_fields(slot, data, session)
        session.commit()
        
        return json({"message": "Slot updated successfully"}, status=200)

    except Exception as e:
        session.rollback()
        return json({"error": str(e)}, status=500)
    finally:
        session.close()

@device_routes.post("/delete_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=20, window_seconds=60, identifier_fn=user_email_identifier)
async def delete_slot(request):
    """Delete a slot from the database."""
    session = SessionLocal()
    try:
        data = request.json
        slot_id = data.get("slot_id")

        if not slot_id:
            return json({"error": "Slot ID is required"}, status=400)

        slot = session.query(Device).filter(Device.id == slot_id).first()
        if not slot:
            return json({"error": "Slot not found"}, status=404)

        session.delete(slot)
        session.commit()
        return json({"message": f"Slot {slot_id} deleted successfully"}, status=200)
    except Exception as e:
        session.rollback()
        return json({"error": str(e)}, status=500)
    finally:
        session.close()