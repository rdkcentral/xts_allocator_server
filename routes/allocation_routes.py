from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Device

allocation_routes = Blueprint("allocation_routes")

@allocation_routes.post("/allocate_slot")
async def allocate_slot(request):
    """Allocate a free slot to a user."""
    session = SessionLocal()
    try:
        data = request.json
        user = data["user"]
        slot_params = data["slot"]

        if not slot_params.get("id") and not slot_params.get("platform"):
            return json({"message": "Either 'id' or 'platform' must be provided"}, status=400)

        query = session.query(Device).filter(Device.state == "free")

        if "id" in slot_params:
            query = query.filter(Device.id == slot_params["id"])
        
        elif "platform" in slot_params:
            query = query.filter(Device.platform == slot_params["platform"])
            if "tags" in slot_params:
                tags = ",".join(slot_params["tags"])
                query = query.filter(Device.tags.contains(tags))

        # gets the first matching device
        slot = query.first()

        if slot:
            # allocate the device
            slot.state = "allocated"
            slot.owner_email = user["email"]
            session.commit()
            return json({
                "message": "Slot allocated",
                "slot_info": f"Slot ID: {slot.id}",
                "id": slot.id
            }, status=200)
        
        return json({"message": "Slot unavailable"}, status=404)

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

        slot.state = "free"
        slot.owner_email = None
        session.commit()
        return json({"message": f"Slot {slot_id} is now free"}, status=200)
    finally:
        session.close()
