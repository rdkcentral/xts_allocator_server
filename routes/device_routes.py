from sanic import Blueprint
from sanic.response import json
from sqlalchemy import func
from models import SessionLocal, Device

device_routes = Blueprint("device_routes")

@device_routes.get("/list_slots")
async def list_slots(request):
    """Retrieve all available slots from the database."""
    session = SessionLocal()
    try:
        slots = session.query(Device).all()
        slots_list = [
            {
                "rackName": slot.rack_name,
                "slotName": slot.slot_name,
                "description": slot.description,
                "tags": slot.tags.split(",") if slot.tags else []
            }
            for slot in slots
        ]
        return json({"slots": slots_list}, status=200)
    finally:
        session.close()


@device_routes.post("/list_slots")
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
                "rackName": slot.rack_name,
                "slotName": slot.slot_name,
                "description": slot.description,
                "tags": slot.tags.split(",") if slot.tags else []
            }
            for slot in query.all()
        ]
        return json({"slots": matching_slots}, status=200)
    finally:
        session.close()

def update_slot_fields(slot, data):
    """Helper function to update a slot's attributes."""
    if "rackName" in data:
        slot.rack_name = data["rackName"]
    if "slotName" in data:
        slot.slot_name = data["slotName"]
    if "description" in data:
        slot.description = data["description"]
    if "tags" in data:
        slot.tags = ",".join(data["tags"]) if isinstance(data["tags"], list) else data["tags"]

@device_routes.post("/add_slot")
async def add_slot(request):
    """Add a new slot to the database."""
    session = SessionLocal()
    try:
        data = request.json

        if "rackName" not in data or "slotName" not in data:
            return json({"error": "Missing required fields: rackName and slotName"}, status=400)

        new_slot = Device(rack_name="", slot_name="", description="", tags="")
        update_slot_fields(new_slot, data)
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

        update_slot_fields(slot, data)
        session.commit()
        
        return json({"message": "Slot updated successfully"}, status=200)

    except Exception as e:
        session.rollback()
        return json({"error": str(e)}, status=500)
    finally:
        session.close()

@device_routes.post("/delete_slot")
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