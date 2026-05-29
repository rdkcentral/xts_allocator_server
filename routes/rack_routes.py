from sanic import Blueprint
from sanic.response import json
from sqlalchemy import func, case, or_
from models import SessionLocal, Rack, Device
from rate_limiter import rate_limit, user_email_identifier
from input_validation import validate_string, ValidationError

from routes.utils import build_target_id, normalize_tags

rack_routes = Blueprint("rack_routes")


_MAX_SEARCH_TEXT = 1024


@rack_routes.get("/list_racks")
async def list_racks(request):
    """List all racks with device counts and status summary."""
    session = SessionLocal()
    try:
        # Query racks with device counts
        racks = session.query(
            Rack,
            func.count(Device.id).label('total_devices'),
            func.sum(case((Device.state == 'free', 1), else_=0)).label('free_devices'),
            func.sum(case((Device.state == 'allocated', 1), else_=0)).label('allocated_devices')
        ).outerjoin(Device).group_by(Rack.id).all()
        
        racks_list = [
            {
                "id": rack.id,
                "name": rack.name,
                "location": rack.location,
                "building": rack.building,
                "description": rack.description,
                "device_counts": {
                    "total": total or 0,
                    "free": free or 0,
                    "allocated": allocated or 0
                }
            }
            for rack, total, free, allocated in racks
        ]
        
        return json({"racks": racks_list}, status=200)
    finally:
        session.close()


@rack_routes.get("/rack/<rack_id:int>")
async def get_rack(request, rack_id):
    """Get rack details with all devices."""
    session = SessionLocal()
    try:
        rack = session.query(Rack).filter(Rack.id == rack_id).first()
        if not rack:
            return json({"error": "Rack not found"}, status=404)
        
        devices = session.query(Device).filter(Device.rack_id == rack_id).all()
        
        devices_list = [
            {
                "id": device.id,
                "slot_name": device.slot_name,
                "platform": device.platform,
                "target_id": build_target_id(device),
                "description": device.description,
                "state": device.state,
                "owner_email": device.owner_email,
                "tags": device.tags.split(",") if device.tags else [],
                "labels": device.tags.split(",") if device.tags else [],
                "make": device.make,
                "model": device.model,
                "serial_number": device.serial_number,
                "external_equipment": device.external_equipment or [],
                "slot_contents": device.external_equipment or []
            }
            for device in devices
        ]
        
        return json({
            "rack": {
                "id": rack.id,
                "name": rack.name,
                "location": rack.location,
                "building": rack.building,
                "description": rack.description,
                "device_count": len(devices_list)
            },
            "devices": devices_list
        }, status=200)
    finally:
        session.close()


@rack_routes.get("/rack/<rack_id:int>/devices")
async def get_rack_devices(request, rack_id):
    """Get all devices in a specific rack."""
    session = SessionLocal()
    try:
        # Check rack exists
        rack = session.query(Rack).filter(Rack.id == rack_id).first()
        if not rack:
            return json({"error": "Rack not found"}, status=404)
        
        devices = session.query(Device).filter(Device.rack_id == rack_id).all()
        
        devices_list = [
            {
                "id": device.id,
                "slot_name": device.slot_name,
                "platform": device.platform,
                "target_id": build_target_id(device),
                "description": device.description,
                "state": device.state,
                "owner_email": device.owner_email,
                "tags": device.tags.split(",") if device.tags else [],
                "labels": device.tags.split(",") if device.tags else [],
                "make": device.make,
                "model": device.model,
                "serial_number": device.serial_number,
                "host_ipv4": device.host_ipv4,
                "control_uris": device.control_uris or {},
                "external_equipment": device.external_equipment or [],
                "slot_contents": device.external_equipment or []
            }
            for device in devices
        ]
        
        return json({
            "rack_id": rack_id,
            "rack_name": rack.name,
            "devices": devices_list,
            "total": len(devices_list)
        }, status=200)
    finally:
        session.close()


@rack_routes.post("/devices/search")
@rate_limit(max_requests=60, window_seconds=60, identifier_fn=user_email_identifier)
async def search_devices(request):
    """Advanced search for devices with multiple filters."""
    session = SessionLocal()
    try:
        filters = request.json or {}
        # Cap free-text filter strings so unbounded input cannot reach
        # SQLAlchemy bind params and trigger a 500.
        try:
            for field in ("rack_name", "platform", "state", "query"):
                if field in filters and not isinstance(filters[field], (list, dict)):
                    filters[field] = validate_string(
                        str(filters[field]), field,
                        max_length=_MAX_SEARCH_TEXT, required=False
                    )
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        query = session.query(Device)
        
        # Filter by rack
        if "rack_id" in filters:
            query = query.filter(Device.rack_id == filters["rack_id"])
        if "rack_name" in filters:
            rack = session.query(Rack).filter(Rack.name == filters["rack_name"]).first()
            if rack:
                query = query.filter(Device.rack_id == rack.id)
        
        # Filter by platform
        if "platform" in filters:
            query = query.filter(Device.platform == filters["platform"])
        
        # Filter by state
        if "state" in filters:
            query = query.filter(Device.state == filters["state"])
        
        # Filter by tags
        if "tags" in filters or "labels" in filters:
            tags = normalize_tags(filters.get("tags", filters.get("labels")))
            query = query.filter(Device.tags.contains(tags))

        # Filter by free-text query across common box identity fields
        if "query" in filters and str(filters["query"]).strip():
            q = str(filters["query"]).strip().lower()
            pattern = f"%{q}%"
            query = query.join(Rack).filter(
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
        
        # Filter by owner
        if "owner_email" in filters:
            query = query.filter(Device.owner_email == filters["owner_email"])
        
        devices = query.all()

        # Filter by computed target id (exact or partial)
        target_filter = str(filters.get("target_id", "")).strip().lower()
        if target_filter:
            devices = [d for d in devices if target_filter in build_target_id(d).lower()]

        # Filter by external equipment type/name
        equipment_type = str(filters.get("has_equipment_type", filters.get("has_equipment", ""))).strip().lower()
        if equipment_type:
            devices = [
                d for d in devices
                if any(
                    equipment_type in str(eq.get("type", "")).lower()
                    or equipment_type in str(eq.get("name", "")).lower()
                    for eq in (d.external_equipment or [])
                )
            ]
        
        devices_list = [
            {
                "id": device.id,
                "rack_id": device.rack_id,
                "rack_name": device.rack.name,
                "slot_name": device.slot_name,
                "platform": device.platform,
                "target_id": build_target_id(device),
                "description": device.description,
                "state": device.state,
                "owner_email": device.owner_email,
                "tags": device.tags.split(",") if device.tags else [],
                "labels": device.tags.split(",") if device.tags else [],
                "make": device.make,
                "model": device.model,
                "serial_number": device.serial_number,
                "host_ipv4": device.host_ipv4,
                "control_uris": device.control_uris or {},
                "external_equipment": device.external_equipment or [],
                "slot_contents": device.external_equipment or []
            }
            for device in devices
        ]
        
        return json({
            "filters": filters,
            "results": devices_list,
            "total": len(devices_list)
        }, status=200)
    finally:
        session.close()
