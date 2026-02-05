from sanic import Blueprint
from sanic.response import text, json as json_response
from models import SessionLocal, Device, Rack
import yaml
from datetime import datetime

export_routes = Blueprint("export_routes")


@export_routes.get("/export/raft_config")
async def export_raft_config(request):
    """Export allocator-optimized YAML config for allocated devices.
    
    New format optimized for XTS allocator integration with:
    - Unified structure (device + rack + allocation metadata)
    - Server communication details
    - Allocation context for reference
    
    Query parameters:
    - allocation_id: Device ID to export config for
    - owner_email: Filter by owner email
    """
    session = SessionLocal()
    try:
        allocation_id = request.args.get("allocation_id")
        owner_email = request.args.get("owner_email")
        
        if not allocation_id and not owner_email:
            return json_response({
                "error": "Either allocation_id or owner_email must be provided"
            }, status=400)
        
        # Build query
        query = session.query(Device).join(Rack)
        if allocation_id:
            query = query.filter(Device.id == int(allocation_id))
        if owner_email:
            query = query.filter(Device.owner_email == owner_email)
        
        devices = query.all()
        
        if not devices:
            return json_response({
                "error": "No allocated devices found matching criteria"
            }, status=404)
        
        # Build allocator-optimized config
        config = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "allocator": {
                "server_url": f"http://{request.host}",
                "api_version": "v1"
            },
            "allocations": []
        }
        
        for device in devices:
            allocation = {
                "allocation_id": device.id,
                "allocation_expiry": device.allocation_expiry.isoformat() if device.allocation_expiry else None,
                "owner_email": device.owner_email,
                "state": device.state,
                "device": {
                    "id": device.id,
                    "platform": device.platform,
                    "make": device.make,
                    "model": device.model,
                    "serial_number": device.serial_number,
                    "firmware": device.firmware,
                    "network": {
                        "host_mac": device.host_mac,
                        "host_ipv4": device.host_ipv4,
                        "host_ipv6": device.host_ipv6
                    },
                    "control_uris": device.control_uris or {},
                    "external_equipment": device.external_equipment or []
                },
                "rack": {
                    "id": device.rack_id,
                    "name": device.rack.name,
                    "location": device.rack.location,
                    "building": device.rack.building,
                    "slot_name": device.slot_name
                },
                "metadata": {
                    "tags": device.tags.split(",") if device.tags else [],
                    "description": device.description,
                    "software_version": device.software_version,
                    "last_verified": device.last_verified.isoformat() if device.last_verified else None
                }
            }
            config["allocations"].append(allocation)
        
        yaml_output = yaml.dump(config, default_flow_style=False, sort_keys=False)
        return text(yaml_output, content_type="application/x-yaml")
        
    except ValueError as e:
        return json_response({"error": f"Invalid parameter: {str(e)}"}, status=400)
    except Exception as e:
        return json_response({"error": str(e)}, status=500)
    finally:
        session.close()


@export_routes.get("/export/python_raft_config")
async def export_python_raft_config(request):
    """Export python_raft-compatible manual format config for allocated devices.
    
    Generates rack_config.yml + device_config.yml compatible structure.
    This format maintains compatibility with existing python_raft workflows
    that expect manually-defined configuration files.
    
    Query parameters:
    - allocation_id: Device ID to export config for
    - owner_email: Filter by owner email
    """
    session = SessionLocal()
    try:
        allocation_id = request.args.get("allocation_id")
        owner_email = request.args.get("owner_email")
        
        if not allocation_id and not owner_email:
            return json_response({
                "error": "Either allocation_id or owner_email must be provided"
            }, status=400)
        
        # Build query
        query = session.query(Device).join(Rack)
        if allocation_id:
            query = query.filter(Device.id == int(allocation_id))
        if owner_email:
            query = query.filter(Device.owner_email == owner_email)
        
        devices = query.all()
        
        if not devices:
            return json_response({
                "error": "No allocated devices found matching criteria"
            }, status=404)
        
        # Build python_raft-compatible config structure
        # Organize devices by rack for rack_config
        racks_dict = {}
        devices_list = []
        
        for device in devices:
            # Build rack_config structure
            rack_key = device.rack.name
            if rack_key not in racks_dict:
                racks_dict[rack_key] = {
                    "name": device.rack.name,
                    "location": device.rack.location or "Unknown",
                    "building": device.rack.building or "Unknown",
                    "slots": []
                }
            
            racks_dict[rack_key]["slots"].append({
                "slot_name": device.slot_name,
                "device_id": device.id,
                "state": device.state
            })
            
            # Build device_config structure
            device_config = {
                "id": device.id,
                "name": f"{device.rack.name}_{device.slot_name}",
                "platform": device.platform or "Unknown",
                "hardware": {
                    "make": device.make,
                    "model": device.model,
                    "serial_number": device.serial_number,
                    "manufacturer": device.manufacturer
                },
                "network": {
                    "host_mac": device.host_mac,
                    "host_ipv4": device.host_ipv4,
                    "host_ipv6": device.host_ipv6
                },
                "control": device.control_uris or {},
                "external_equipment": device.external_equipment or [],
                "firmware": device.firmware,
                "tags": device.tags.split(",") if device.tags else [],
                "allocation": {
                    "owner": device.owner_email,
                    "expiry": device.allocation_expiry.isoformat() if device.allocation_expiry else None,
                    "state": device.state
                }
            }
            devices_list.append(device_config)
        
        # Combine into python_raft manual format
        config = {
            "rack_config": {
                "version": "1.0",
                "racks": list(racks_dict.values())
            },
            "device_config": {
                "version": "1.0",
                "devices": devices_list
            },
            "metadata": {
                "generated_by": "xts_allocator_server",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "allocator_url": f"http://{request.host}"
            }
        }
        
        yaml_output = yaml.dump(config, default_flow_style=False, sort_keys=False)
        return text(yaml_output, content_type="application/x-yaml")
        
    except ValueError as e:
        return json_response({"error": f"Invalid parameter: {str(e)}"}, status=400)
    except Exception as e:
        return json_response({"error": str(e)}, status=500)
    finally:
        session.close()
