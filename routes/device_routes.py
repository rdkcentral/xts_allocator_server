from sanic import Blueprint
from sanic.response import json
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


@device_routes.post("/search_slots")
async def search_slots(request):
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
