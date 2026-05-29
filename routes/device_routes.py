from sanic import Blueprint
from sanic.response import json
from sqlalchemy import func, or_
from models import SessionLocal, Device, Rack
from rate_limiter import rate_limit, user_email_identifier
from auth import require_auth, ROLE_ENGINEER
from input_validation import validate_string, ValidationError

from routes.utils import build_target_id, normalize_tags


_MAX_STR = 255
_MAX_FREE_TEXT = 1024


def _coerce_str(value, field_name, max_length=_MAX_STR):
    """Reject non-str / oversized values at the API boundary so they cannot
    flow into SQLAlchemy bind params and trigger a 500."""
    if value is None:
        return None
    if not isinstance(value, (str, int, float)):
        raise ValidationError(f"{field_name} must be a string (got {type(value).__name__})")
    return validate_string(str(value), field_name, max_length=max_length, required=False)

device_routes = Blueprint("device_routes")


def normalize_external_equipment(raw_equipment):
    """Normalize slot contents to list[dict] for external_equipment storage."""
    if raw_equipment is None:
        return []
    if isinstance(raw_equipment, str):
        raw_equipment = [item.strip() for item in raw_equipment.split(",") if item.strip()]
    if not isinstance(raw_equipment, list):
        return []

    normalized = []
    for item in raw_equipment:
        if isinstance(item, dict):
            normalized.append(item)
        elif isinstance(item, str) and item.strip():
            normalized.append({"type": item.strip().lower(), "name": item.strip()})
    return normalized


@device_routes.get("/list_slots")
@rate_limit(max_requests=60, window_seconds=60)
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
                "target_id": build_target_id(slot),
                "description": slot.description,
                "tags": slot.tags.split(",") if slot.tags else [],
                "labels": slot.tags.split(",") if slot.tags else [],
                "state": slot.state,
                "owner_email": slot.owner_email,
                "allocation_type": slot.allocation_type,
                "allocation_expiry": slot.allocation_expiry.isoformat() if slot.allocation_expiry else None,
                "make": slot.make,
                "model": slot.model,
                "external_equipment": slot.external_equipment or [],
                "slot_contents": slot.external_equipment or [],
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
        criteria = request.json or {}
        # Guard string filters against unbounded input / wrong types before
        # they reach SQLAlchemy bind params.
        try:
            for field in ("platform", "description", "rackName", "state",
                          "owner_email", "query", "target_id",
                          "has_equipment_type", "has_equipment"):
                if field in criteria:
                    criteria[field] = _coerce_str(criteria[field], field, _MAX_FREE_TEXT)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        query = session.query(Device).join(Rack)

        if "platform" in criteria:
            query = query.filter(Device.platform == criteria["platform"])
        if "description" in criteria:
            query = query.filter(Device.description.like(f"%{criteria['description']}%"))
        if "tags" in criteria or "labels" in criteria:
            tags = normalize_tags(criteria.get("tags", criteria.get("labels")))
            query = query.filter(Device.tags.contains(tags))
        if "rackName" in criteria:
            query = query.filter(Rack.name == criteria["rackName"])
        if "state" in criteria:
            query = query.filter(Device.state == criteria["state"])
        if "owner_email" in criteria:
            query = query.filter(Device.owner_email == criteria["owner_email"])
        if "query" in criteria and str(criteria["query"]).strip():
            q = str(criteria["query"]).strip().lower()
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    func.lower(Device.platform).like(pattern),
                    func.lower(Device.slot_name).like(pattern),
                    func.lower(Device.description).like(pattern),
                    func.lower(Device.make).like(pattern),
                    func.lower(Device.model).like(pattern),
                    func.lower(Device.tags).like(pattern),
                    func.lower(Rack.name).like(pattern)
                )
            )

        devices = query.all()

        target_filter = str(criteria.get("target_id", "")).strip().lower()
        if target_filter:
            devices = [d for d in devices if target_filter in build_target_id(d).lower()]

        equipment_filter = str(criteria.get("has_equipment_type", criteria.get("has_equipment", ""))).strip().lower()
        if equipment_filter:
            devices = [
                d for d in devices
                if any(
                    equipment_filter in str(eq.get("type", "")).lower()
                    or equipment_filter in str(eq.get("name", "")).lower()
                    for eq in (d.external_equipment or [])
                )
            ]

        matching_slots = [
            {
                "slot_id": slot.id,
                "rackName": slot.rack.name,
                "rackId": slot.rack_id,
                "slotName": slot.slot_name,
                "platform": slot.platform,
                "target_id": build_target_id(slot),
                "description": slot.description,
                "tags": slot.tags.split(",") if slot.tags else [],
                "labels": slot.tags.split(",") if slot.tags else [],
                "state": slot.state,
                "owner_email": slot.owner_email,
                "allocation_expiry": slot.allocation_expiry.isoformat() if slot.allocation_expiry else None,
                "external_equipment": slot.external_equipment or [],
                "slot_contents": slot.external_equipment or []
            }
            for slot in devices
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
        slot.tags = normalize_tags(data["tags"])
    if "labels" in data and "tags" not in data:
        slot.tags = normalize_tags(data["labels"])
    if "make" in data:
        slot.make = data["make"]
    if "model" in data:
        slot.model = data["model"]
    if "host_ipv4" in data:
        slot.host_ipv4 = data["host_ipv4"]
    if "control_uris" in data:
        slot.control_uris = data["control_uris"]
    if "external_equipment" in data:
        slot.external_equipment = normalize_external_equipment(data["external_equipment"])
    if "slot_contents" in data and "external_equipment" not in data:
        slot.external_equipment = normalize_external_equipment(data["slot_contents"])

@device_routes.post("/add_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=20, window_seconds=60, identifier_fn=user_email_identifier)
async def add_slot(request):
    """Add a new slot to the database."""
    session = SessionLocal()
    try:
        data = request.json or {}

        if "rackName" not in data or "slotName" not in data:
            return json({"error": "Missing required fields: rackName and slotName"}, status=400)

        # Reject non-string rackName / slotName before they reach SQLAlchemy.
        try:
            data["rackName"] = _coerce_str(data["rackName"], "rackName")
            data["slotName"] = _coerce_str(data["slotName"], "slotName")
        except ValidationError as e:
            return json({"error": str(e)}, status=400)

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
            tags=normalize_tags(data.get("tags", data.get("labels", ""))),
            state=data.get("state", "free"),
            owner_email=data.get("owner_email"),
            make=data.get("make"),
            model=data.get("model"),
            host_ipv4=data.get("host_ipv4"),
            control_uris=data.get("control_uris"),
            external_equipment=normalize_external_equipment(
                data.get("external_equipment", data.get("slot_contents"))
            )
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
