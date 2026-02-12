from sanic import Blueprint
from sanic.response import text, json as json_response
from models import SessionLocal, Device, Rack
import yaml
from datetime import datetime

export_routes = Blueprint("export_routes")


def build_target_id(device):
    """Build a stable allocation target identifier for a device."""
    rack_name = device.rack.name if device.rack else f"rack-{device.rack_id}"
    platform = device.platform or "unknown"
    return f"{platform}@{rack_name}/{device.slot_name}"


def _get_allocated_devices(session, request):
    """Fetch allocated devices with optional filters."""
    allocation_id = request.args.get("allocation_id")
    owner_email = request.args.get("owner_email")
    platform = request.args.get("platform")

    if not allocation_id and not owner_email:
        raise ValueError("Either allocation_id or owner_email must be provided")

    query = session.query(Device).join(Rack)
    if allocation_id:
        query = query.filter(Device.id == int(allocation_id))
    if owner_email:
        query = query.filter(Device.owner_email == owner_email)
    if platform:
        query = query.filter(Device.platform == platform)

    return query.all()


def _build_platform_profiles(devices, request):
    """Build platform-centric deviceConfig profiles for python_raft."""
    default_target_directory = request.args.get("target_directory", "/opt/VTS/")
    default_prompt = request.args.get("prompt", "")
    default_soc_vendor = request.args.get("soc_vendor", "unknown")
    default_test_profile = request.args.get("test_profile", "")
    default_streams_url = request.args.get("streams_download_url", "")

    platform_profiles = {}
    device_refs = {}
    legacy_device_config = {}

    for idx, device in enumerate(devices, 1):
        platform_name = device.platform or "Unknown"
        profile_key = platform_name

        if profile_key not in platform_profiles:
            platform_profiles[profile_key] = {
                "platform": platform_name,
                "model": device.model or request.args.get("model", "Unknown"),
                "soc_vendor": request.args.get(f"soc_vendor_{platform_name}", default_soc_vendor),
                "target_directory": request.args.get("target_directory", default_target_directory),
                "prompt": request.args.get("prompt", default_prompt),
                "test": {
                    "profile": request.args.get(f"test_profile_{platform_name}", default_test_profile),
                    "streams_download_url": request.args.get("streams_download_url", default_streams_url)
                }
            }

        cpe_key = f"cpe{idx}"
        device_refs[cpe_key] = {
            "platform_profile": profile_key,
            "device_id": device.id,
            "target_id": build_target_id(device),
            "rack": device.rack.name if device.rack else None,
            "slot": device.slot_name
        }

        # Backward compatible per-device section for consumers expecting older shape.
        legacy_device_config[cpe_key] = {
            "platform": platform_name,
            "model": device.model or request.args.get("model", "Unknown"),
            "soc_vendor": request.args.get(f"soc_vendor_{platform_name}", default_soc_vendor),
            "target_directory": request.args.get("target_directory", default_target_directory),
            "prompt": request.args.get("prompt", default_prompt),
            "test": {
                "profile": request.args.get(f"test_profile_{platform_name}", default_test_profile),
                "streams_download_url": request.args.get("streams_download_url", default_streams_url)
            }
        }

    return {
        "schema_version": "2.0",
        "profile_type": "python_raft_device_profile",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "allocator": {
            "url": f"http://{request.host}"
        },
        "deviceConfig": {
            "platformProfiles": platform_profiles,
            "devices": device_refs
        },
        "legacyDeviceConfig": legacy_device_config
    }


def _build_rack_config(devices, request):
    """Build python_raft-style rackConfig with globalConfig and slot mappings."""
    include_device_config = request.args.get("device_config_include", "example_device_config.yml")
    ocr_engine_path = request.args.get("ocr_engine_path", "/usr/bin/tesseract")
    capture_resolution = request.args.get("capture_resolution", "1080p")
    capture_input = int(request.args.get("capture_input", "0"))
    log_directory = request.args.get("log_directory", "./logs")
    log_delimiter = request.args.get("log_delimiter", "/")
    default_console_type = request.args.get("default_console_type", "ssh")
    default_console_port = int(request.args.get("default_console_port", "22"))
    default_console_user = request.args.get("default_console_user", "root")
    default_console_password = request.args.get("default_console_password", "")
    default_download_url = request.args.get("download_url", "")
    default_upload_url = request.args.get("upload_url", "")
    default_upload_base = request.args.get("upload_url_base_dir", "")
    default_http_proxy = request.args.get("http_proxy", "")
    default_workspace = request.args.get("workspace_directory", "./logs/workspace")

    rack_config = {}

    for device in devices:
        rack_name = device.rack.name if device.rack else f"rack_{device.rack_id}"
        slot_key = (device.slot_name or "slot").lower().replace(" ", "_")

        if rack_name not in rack_config:
            rack_config[rack_name] = {
                "name": rack_name,
                "description": (device.rack.description if device.rack else None) or f"Generated rack profile for {rack_name}"
            }

        # Build default console based on known host IP.
        default_console = {
            "type": default_console_type,
            "port": default_console_port,
            "username": default_console_user,
            "ip": device.host_ipv4 or "",
            "password": default_console_password
        }

        rack_config[rack_name][slot_key] = {
            "name": device.slot_name,
            "devices": [
                {
                    "dut": {
                        "ip": device.host_ipv4 or "",
                        "description": device.description or "Device under test",
                        "platform": device.platform or "Unknown",
                        "consoles": [
                            {"default": default_console}
                        ],
                        "outbound": {
                            "download_url": default_download_url,
                            "upload_url": default_upload_url,
                            "upload_url_base_dir": default_upload_base,
                            "httpProxy": default_http_proxy,
                            "workspaceDirectory": default_workspace
                        }
                    }
                }
            ]
        }

    return {
        "schema_version": "2.0",
        "profile_type": "python_raft_rack_config",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "allocator": {
            "url": f"http://{request.host}"
        },
        "globalConfig": {
            "includes": {
                "deviceConfig": include_device_config
            },
            "capture": {
                "ocrEnginePath": ocr_engine_path,
                "resolution": capture_resolution,
                "input": capture_input
            },
            "local": {
                "log": {
                    "directory": log_directory,
                    "delimiter": log_delimiter
                }
            }
        },
        "rackConfig": rack_config
    }


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
                "target_id": build_target_id(device),
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
                "target_id": build_target_id(device),
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


@export_routes.get("/export/python_raft_device_profile")
async def export_python_raft_device_profile(request):
    """Export platform-centric python_raft deviceConfig profile."""
    session = SessionLocal()
    try:
        devices = _get_allocated_devices(session, request)
        if not devices:
            return json_response({
                "error": "No allocated devices found matching criteria"
            }, status=404)

        profile = _build_platform_profiles(devices, request)
        yaml_output = yaml.dump(profile, default_flow_style=False, sort_keys=False)
        return text(yaml_output, content_type="application/x-yaml")

    except ValueError as e:
        return json_response({"error": f"Invalid parameter: {str(e)}"}, status=400)
    except Exception as e:
        return json_response({"error": str(e)}, status=500)
    finally:
        session.close()


@export_routes.get("/export/python_raft_rack_config")
async def export_python_raft_rack_config(request):
    """Export python_raft rack/slot configuration with global includes."""
    session = SessionLocal()
    try:
        devices = _get_allocated_devices(session, request)
        if not devices:
            return json_response({
                "error": "No allocated devices found matching criteria"
            }, status=404)

        profile = _build_rack_config(devices, request)
        yaml_output = yaml.dump(profile, default_flow_style=False, sort_keys=False)
        return text(yaml_output, content_type="application/x-yaml")

    except ValueError as e:
        return json_response({"error": f"Invalid parameter: {str(e)}"}, status=400)
    except Exception as e:
        return json_response({"error": str(e)}, status=500)
    finally:
        session.close()
