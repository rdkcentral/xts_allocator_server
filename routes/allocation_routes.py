from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Device, AllocationHistory, Rack

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

        # Allocate by slot_id if provided
        if "id" in slot_params:
            slot_id = slot_params["id"]
            slot = session.query(Device).filter(Device.id == slot_id).first()
            if not slot:
                return json({"message": f"Slot with id {slot_id} not found"}, status=404)
            if slot.state != "free":
                return json({"message": f"Slot {slot_id} is already allocated"}, status=409)
            
            # Allocate the slot
            slot.state = "allocated"
            slot.owner_email = user.get("email")
            session.commit()
            return json({
                "message": "Slot allocated successfully",
                "slot_id": slot.id,
                "rackName": slot.rack_name,
                "slotName": slot.slot_name,
                "state": slot.state,
                "owner_email": slot.owner_email
            }, status=200)

        # Allocate by platform/tags
        else:
            query = session.query(Device).filter(Device.state == "free", Device.platform == slot_params["platform"])
            if "tags" in slot_params:
                tags = ",".join(slot_params["tags"])
                query = query.filter(Device.tags.contains(tags))
            slot = query.first()
            if not slot:
                return json({"message": "No free slot matches the criteria", "slots":[]}, status=200)
            
            # Allocate the slot
            slot.state = "allocated"
            slot.owner_email = user.get("email")
            session.commit()
            return json({
                "message": "Slot allocated successfully",
                "slot_id": slot.id,
                "rackName": slot.rack.name,
                "rackId": slot.rack_id,
                "slotName": slot.slot_name,
                "state": slot.state,
                "owner_email": slot.owner_email
            }, status=200)

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

        slot.state = "free"
        slot.owner_email = None
        session.commit()
        return json({"message": f"Slot {slot_id} is now free"}, status=200)
    
    except Exception as e:
        session.rollback()
        return json({"message": "Internal server error", "error": str(e)}, status=500)
    finally:
        session.close()
