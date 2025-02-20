from sanic import Blueprint
from sanic.response import json
from sqlalchemy import func
from models import SessionLocal, Device

device_routes = Blueprint("device_routes")

@device_routes.get("/list_slots")
async def list_slots(request):
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

@device_routes.post("/add_slot")
async def add_slot(request):
    session = SessionLocal()
    try:
        data = request.json

        # get the next available slot ID
        max_id = session.query(func.max(Device.id)).scalar()
        next_id = (max_id + 1) if max_id else 1  #if no records then start from 1

        if "rackName" not in data or "slotName" not in data:
            return json({"error": "Missing required fields: rackName and slotName"}, status=400)

        new_slot = Device(
            id=next_id,
            rack_name=data["rackName"],
            slot_name=data["slotName"],
            description=data.get("description", ""),
            tags=",".join(data.get("tags", []))
        )
        session.add(new_slot)
        session.commit()

        return json({"message": "Slot added successfully", "slot_id": next_id}, status=201)

    except Exception as e:
        session.rollback()
        return json({"error": str(e)}, status=500)
    finally:
        session.close()

@device_routes.post("/update_slot")
async def update_slot_info(request):
    session = SessionLocal()
    try:
        data = request.json
        slot_id = data.get("slot_id")

        if not slot_id:
            return json({"error": "Slot ID is required"}, status=400)

        slot = session.query(Device).filter(Device.id == slot_id).first()
        if not slot:
            return json({"error": "Slot not found"}, status=404)

        #only update the provided fields
        if "rackName" in data:
            slot.rack_name = data["rackName"]
        if "slotName" in data:
            slot.slot_name = data["slotName"]
        if "description" in data:
            slot.description = data["description"]
        if "tags" in data:
            slot.tags = ",".join(data["tags"])

        session.commit()
        return json({"message": "Slot updated successfully"}, status=200)

    except Exception as e:
        session.rollback()
        return json({"error": str(e)}, status=500)
    finally:
        session.close()

@device_routes.post("/clear_slot_field")
async def clear_slot_info(request):
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