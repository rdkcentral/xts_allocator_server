from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Device, AllocationHistory
from datetime import datetime, timedelta
from logging_config import get_logger
from sqlalchemy import func

usage_routes = Blueprint("usage_routes")
logger = get_logger()


@usage_routes.get("/device/<device_id:int>/usage_stats")
async def get_device_usage_stats(request, device_id):
    """
    Get usage statistics for a device.
    Includes: test execution count, total test time, idle time, allocation history summary.
    """
    session = SessionLocal()
    try:
        device = session.query(Device).filter(Device.id == device_id).first()
        if not device:
            return json({"error": f"Device {device_id} not found"}, status=404)
        
        # Get allocation history for this device
        allocations = session.query(AllocationHistory).filter(
            AllocationHistory.device_id == device_id
        ).all()
        
        # Calculate aggregated statistics
        total_allocations = len(allocations)
        total_test_executions = sum(h.test_execution_count for h in allocations if h.test_execution_count)
        total_test_time_minutes = sum(h.total_test_time for h in allocations if h.total_test_time)
        total_idle_time_minutes = sum(h.idle_time for h in allocations if h.idle_time)
        
        # Calculate total allocation time
        total_allocation_time = 0
        for h in allocations:
            if h.end_time:
                delta = h.end_time - h.start_time
                total_allocation_time += delta.total_seconds() / 60
        
        # Get recent allocations (last 10)
        recent_allocations = []
        for h in sorted(allocations, key=lambda x: x.start_time, reverse=True)[:10]:
            allocation_duration = None
            if h.end_time:
                delta = h.end_time - h.start_time
                allocation_duration = int(delta.total_seconds() / 60)
            
            recent_allocations.append({
                "id": h.id,
                "email": h.email,
                "start_time": h.start_time.isoformat() + "Z",
                "end_time": h.end_time.isoformat() + "Z" if h.end_time else None,
                "duration_minutes": allocation_duration,
                "allocation_type": h.allocation_type,
                "test_execution_count": h.test_execution_count,
                "total_test_time": h.total_test_time,
                "idle_time": h.idle_time
            })
        
        # Get allocation type breakdown
        permanent_count = sum(1 for h in allocations if h.allocation_type == "permanent")
        temporary_count = sum(1 for h in allocations if h.allocation_type == "temporary")
        
        stats = {
            "device_id": device_id,
            "rack": device.rack.name,
            "slot": device.slot_name,
            "platform": device.platform,
            "current_state": device.state,
            "current_owner": device.owner_email,
            "allocation_type": device.allocation_type,
            "last_seen": device.last_seen.isoformat() + "Z" if device.last_seen else None,
            "connectivity_status": device.connectivity_status,
            "statistics": {
                "total_allocations": total_allocations,
                "permanent_allocations": permanent_count,
                "temporary_allocations": temporary_count,
                "total_test_executions": total_test_executions,
                "total_test_time_minutes": total_test_time_minutes,
                "total_idle_time_minutes": total_idle_time_minutes,
                "total_allocation_time_minutes": int(total_allocation_time),
                "utilization_percentage": round((total_test_time_minutes / total_allocation_time * 100), 2) if total_allocation_time > 0 else 0
            },
            "recent_allocations": recent_allocations
        }
        
        return json(stats, status=200)
    
    except Exception as e:
        logger.error(f"Error fetching usage stats for device {device_id}: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@usage_routes.get("/usage_summary")
async def get_usage_summary(request):
    """
    Get system-wide usage summary across all devices.
    """
    session = SessionLocal()
    try:
        # Get query parameters
        days = int(request.args.get("days", 30))  # Default last 30 days
        
        since = datetime.utcnow() - timedelta(days=days)
        
        # Query allocations in timeframe
        allocations = session.query(AllocationHistory).filter(
            AllocationHistory.start_time >= since
        ).all()
        
        # Calculate aggregates
        total_allocations = len(allocations)
        total_test_executions = sum(h.test_execution_count for h in allocations if h.test_execution_count)
        total_test_time = sum(h.total_test_time for h in allocations if h.total_test_time)
        total_idle_time = sum(h.idle_time for h in allocations if h.idle_time)
        
        # Get unique users
        unique_users = len(set(h.email for h in allocations if h.email))
        
        # Get allocation type breakdown
        permanent_count = sum(1 for h in allocations if h.allocation_type == "permanent")
        temporary_count = sum(1 for h in allocations if h.allocation_type == "temporary")
        
        # Get device usage counts
        device_usage = {}
        for h in allocations:
            device_id = h.device_id
            if device_id not in device_usage:
                device_usage[device_id] = 0
            device_usage[device_id] += 1
        
        # Get top 10 most used devices
        top_devices = sorted(device_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        top_devices_list = []
        for device_id, count in top_devices:
            device = session.query(Device).filter(Device.id == device_id).first()
            if device:
                top_devices_list.append({
                    "device_id": device_id,
                    "rack": device.rack.name,
                    "slot": device.slot_name,
                    "platform": device.platform,
                    "allocation_count": count
                })
        
        summary = {
            "period_days": days,
            "since": since.isoformat() + "Z",
            "until": datetime.utcnow().isoformat() + "Z",
            "statistics": {
                "total_allocations": total_allocations,
                "permanent_allocations": permanent_count,
                "temporary_allocations": temporary_count,
                "unique_users": unique_users,
                "total_test_executions": total_test_executions,
                "total_test_time_minutes": total_test_time,
                "total_idle_time_minutes": total_idle_time,
                "avg_allocation_per_day": round(total_allocations / days, 2) if days > 0 else 0
            },
            "top_devices": top_devices_list
        }
        
        return json(summary, status=200)
    
    except Exception as e:
        logger.error(f"Error fetching usage summary: {str(e)}", exc_info=True)
        return json({"error": str(e)}, status=500)
    finally:
        session.close()
