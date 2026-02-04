from sanic import Blueprint
from sanic.response import json
from sqlalchemy import func, case
from models import SessionLocal, Rack, Device

rack_routes = Blueprint("rack_routes")

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
                "description": device.description,
                "state": device.state,
                "owner_email": device.owner_email,
                "tags": device.tags.split(",") if device.tags else [],
                "make": device.make,
                "model": device.model,
                "serial_number": device.serial_number,
                "external_equipment": device.external_equipment or []
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
                "description": device.description,
                "state": device.state,
                "owner_email": device.owner_email,
                "tags": device.tags.split(",") if device.tags else [],
                "make": device.make,
                "model": device.model,
                "serial_number": device.serial_number,
                "host_ipv4": device.host_ipv4,
                "control_uris": device.control_uris or {},
                "external_equipment": device.external_equipment or []
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
async def search_devices(request):
    """Advanced search for devices with multiple filters."""
    session = SessionLocal()
    try:
        filters = request.json or {}
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
        if "tags" in filters:
            tags = ",".join(filters["tags"]) if isinstance(filters["tags"], list) else filters["tags"]
            query = query.filter(Device.tags.contains(tags))
        
        # Filter by owner
        if "owner_email" in filters:
            query = query.filter(Device.owner_email == filters["owner_email"])
        
        # Filter by external equipment type
        if "has_equipment_type" in filters:
            # This requires JSON querying - simplified version
            equipment_type = filters["has_equipment_type"]
            devices = []
            for device in query.all():
                if device.external_equipment:
                    for eq in device.external_equipment:
                        if eq.get("type") == equipment_type:
                            devices.append(device)
                            break
        else:
            devices = query.all()
        
        devices_list = [
            {
                "id": device.id,
                "rack_id": device.rack_id,
                "rack_name": device.rack.name,
                "slot_name": device.slot_name,
                "platform": device.platform,
                "description": device.description,
                "state": device.state,
                "owner_email": device.owner_email,
                "tags": device.tags.split(",") if device.tags else [],
                "make": device.make,
                "model": device.model,
                "serial_number": device.serial_number,
                "host_ipv4": device.host_ipv4,
                "control_uris": device.control_uris or {},
                "external_equipment": device.external_equipment or []
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
