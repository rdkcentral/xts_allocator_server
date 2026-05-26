from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Server
from datetime import datetime, timedelta, timezone
from logging_config import get_logger
from routes.utils import ensure_utc
import httpx

federation_routes = Blueprint("federation_routes")
logger = get_logger()


@federation_routes.post("/register")
async def register_server(request):
    """
    Register a slave server with the master.
    Slaves send: name, url, location, metadata
    """
    session = SessionLocal()
    try:
        data = request.json
        
        name = data.get("name")
        url = data.get("url")
        location = data.get("location")
        server_metadata = data.get("metadata", {})
        
        if not name or not url:
            return json({"error": "name and url are required"}, status=400)
        
        # Check if server already exists
        server = session.query(Server).filter(Server.name == name).first()
        
        if server:
            # Update existing server
            server.url = url
            server.location = location
            server.server_metadata = server_metadata
            server.status = "online"
            server.last_heartbeat = datetime.now(timezone.utc)
            logger.info(f"Server updated: {name} at {url}")
        else:
            # Create new server
            server = Server(
                name=name,
                url=url,
                location=location,
                role="slave",
                status="online",
                last_heartbeat=datetime.now(timezone.utc),
                server_metadata=server_metadata
            )
            session.add(server)
            logger.info(f"New server registered: {name} at {url}")
        
        session.commit()
        
        return json({
            "message": "Server registered successfully",
            "server_id": server.id,
            "name": server.name,
            "status": server.status
        }, status=200)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Server registration error: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@federation_routes.post("/heartbeat")
async def heartbeat(request):
    """
    Receive heartbeat from slave server.
    Slaves send: name, device_count, status
    """
    session = SessionLocal()
    try:
        data = request.json

        name = data.get("name")
        raw_count = data.get("device_count", 0)
        status = data.get("status", "online")

        if not name:
            return json({"error": "name is required"}, status=400)
        try:
            device_count = int(raw_count) if raw_count is not None else 0
        except (TypeError, ValueError):
            return json({"error": "device_count must be an integer"}, status=400)
        
        server = session.query(Server).filter(Server.name == name).first()
        
        if not server:
            return json({"error": f"Server {name} not registered"}, status=404)
        
        # Update heartbeat
        server.last_heartbeat = datetime.now(timezone.utc)
        server.device_count = device_count
        server.status = status
        
        session.commit()
        
        return json({
            "message": "Heartbeat received",
            "server_id": server.id,
            "status": server.status
        }, status=200)
    
    except Exception as e:
        session.rollback()
        logger.error(f"Heartbeat error: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@federation_routes.get("/servers")
async def list_servers(request):
    """
    List all registered servers.
    Query parameters:
    - status: filter by status (online, offline, unreachable)
    """
    session = SessionLocal()
    try:
        query = session.query(Server)

        # Filter by status if provided — cap length so unbounded input
        # cannot flow into SQLAlchemy bind params and 500.
        status_filter = request.args.get("status")
        if status_filter:
            if len(status_filter) > 64:
                return json({"error": "status filter too long (max 64)"}, status=400)
            query = query.filter(Server.status == status_filter)
        
        servers = query.all()
        
        # Mark servers as offline if no heartbeat in last 5 minutes
        offline_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        server_list = []
        for server in servers:
            # Check if server should be marked offline
            if server.last_heartbeat and ensure_utc(server.last_heartbeat) < offline_threshold:
                if server.status != "offline":
                    server.status = "offline"
                    session.commit()
            
            server_list.append({
                "id": server.id,
                "name": server.name,
                "url": server.url,
                "location": server.location,
                "role": server.role,
                "status": server.status,
                "device_count": server.device_count,
                "last_heartbeat": server.last_heartbeat.isoformat() + "Z" if server.last_heartbeat else None,
                "metadata": server.server_metadata
            })
        
        return json({
            "servers": server_list,
            "total": len(server_list)
        }, status=200)
    
    except Exception as e:
        logger.error(f"Error listing servers: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@federation_routes.get("/servers/<server_id:int>")
async def get_server_details(request, server_id):
    """
    Get details for a specific server.
    """
    session = SessionLocal()
    try:
        server = session.query(Server).filter(Server.id == server_id).first()
        
        if not server:
            return json({"error": f"Server {server_id} not found"}, status=404)
        
        server_details = {
            "id": server.id,
            "name": server.name,
            "url": server.url,
            "location": server.location,
            "role": server.role,
            "status": server.status,
            "device_count": server.device_count,
            "last_heartbeat": server.last_heartbeat.isoformat() + "Z" if server.last_heartbeat else None,
            "metadata": server.server_metadata,
            "created_at": server.created_at.isoformat() + "Z",
            "updated_at": getattr(server, "updated_at").isoformat() + "Z" if hasattr(server, "updated_at") else server.created_at.isoformat() + "Z"
        }
        
        return json(server_details, status=200)
    
    except Exception as e:
        logger.error(f"Error getting server details: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@federation_routes.get("/servers/<server_id:int>/devices")
async def get_server_devices(request, server_id):
    """
    Proxy request to slave server to get its devices.
    Master aggregates device listings from all slaves.
    """
    session = SessionLocal()
    try:
        server = session.query(Server).filter(Server.id == server_id).first()
        
        if not server:
            return json({"error": f"Server {server_id} not found"}, status=404)
        
        if server.status != "online":
            return json({"error": f"Server {server.name} is {server.status}"}, status=503)
        
        # Proxy request to slave server
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{server.url}/list_slots")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Add server context to response
                    return json({
                        "server_id": server.id,
                        "server_name": server.name,
                        "server_url": server.url,
                        "devices": data.get("slots", [])
                    }, status=200)
                else:
                    return json({
                        "error": f"Slave server returned status {response.status_code}"
                    }, status=response.status_code)
        
        except httpx.RequestError as e:
            logger.error(f"Error connecting to server {server.name}: {str(e)}")
            # Mark server as unreachable
            server.status = "unreachable"
            session.commit()
            return json({"error": f"Unable to reach server {server.name}"}, status=503)
    
    except Exception as e:
        logger.error(f"Error proxying to server: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@federation_routes.get("/devices/federated")
async def list_all_federated_devices(request):
    """
    Aggregate device listings from all online slave servers.
    Returns combined view of all devices across the federation.
    """
    session = SessionLocal()
    try:
        # Get all online servers
        servers = session.query(Server).filter(Server.status == "online").all()
        
        all_devices = []
        server_errors = []
        
        # Query each server for devices
        async with httpx.AsyncClient(timeout=10.0) as client:
            for server in servers:
                try:
                    response = await client.get(f"{server.url}/list_slots")
                    
                    if response.status_code == 200:
                        data = response.json()
                        devices = data.get("slots", [])
                        
                        # Add server context to each device
                        for device in devices:
                            device["server_id"] = server.id
                            device["server_name"] = server.name
                            device["server_location"] = server.location
                        
                        all_devices.extend(devices)
                    else:
                        server_errors.append({
                            "server": server.name,
                            "error": f"HTTP {response.status_code}"
                        })
                
                except httpx.RequestError as e:
                    logger.error(f"Error connecting to server {server.name}: {str(e)}")
                    server_errors.append({
                        "server": server.name,
                        "error": "unreachable"
                    })
                    # Mark server as unreachable
                    server.status = "unreachable"
                    session.commit()
        
        return json({
            "devices": all_devices,
            "total_devices": len(all_devices),
            "servers_queried": len(servers),
            "errors": server_errors if server_errors else None
        }, status=200)
    
    except Exception as e:
        logger.error(f"Error fetching federated devices: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()
