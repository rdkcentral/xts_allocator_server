from sanic import Blueprint
from sanic.response import json
from models import SessionLocal, Device, AllocationHistory
from sqlalchemy import func
from datetime import datetime, timedelta

health_routes = Blueprint("health_routes")


@health_routes.get("/health")
async def health_check(request):
    """Health check endpoint for monitoring service status."""
    try:
        # Test database connectivity
        session = SessionLocal()
        try:
            # Simple query to verify database is accessible
            session.query(Device).limit(1).all()
            db_status = "healthy"
            db_error = None
        except Exception as e:
            db_status = "unhealthy"
            db_error = str(e)
        finally:
            session.close()
        
        health_status = {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "xts_allocator_server",
            "version": "1.0.0",
            "database": {
                "status": db_status,
                "error": db_error
            }
        }
        
        status_code = 200 if db_status == "healthy" else 503
        return json(health_status, status=status_code)
        
    except Exception as e:
        return json({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }, status=503)


@health_routes.get("/metrics")
async def get_metrics(request):
    """Get system metrics for monitoring and analytics."""
    session = SessionLocal()
    try:
        # Device counts by state
        devices_by_state = {}
        state_counts = session.query(
            Device.state,
            func.count(Device.id)
        ).group_by(Device.state).all()
        
        for state, count in state_counts:
            devices_by_state[state] = count
        
        # Total devices
        total_devices = session.query(func.count(Device.id)).scalar()
        
        # Devices by rack
        devices_by_rack = {}
        rack_counts = session.query(
            Device.rack_id,
            func.count(Device.id)
        ).group_by(Device.rack_id).all()
        
        for rack_id, count in rack_counts:
            devices_by_rack[f"rack_{rack_id}"] = count
        
        # Allocation metrics for today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        allocations_today = session.query(func.count(AllocationHistory.id)).filter(
            AllocationHistory.start_time >= today_start
        ).scalar()
        
        # Average allocation duration (for completed allocations today)
        avg_duration_query = session.query(
            func.avg(
                func.julianday(AllocationHistory.end_time) - func.julianday(AllocationHistory.start_time)
            ) * 24 * 60  # Convert days to minutes
        ).filter(
            AllocationHistory.start_time >= today_start,
            AllocationHistory.end_time.isnot(None)
        ).scalar()
        
        avg_allocation_duration = round(avg_duration_query, 2) if avg_duration_query else 0
        
        # Active allocations (no end_time)
        active_allocations = session.query(func.count(AllocationHistory.id)).filter(
            AllocationHistory.end_time.is_(None)
        ).scalar()
        
        # Utilization rate (allocated + busy + testing vs total)
        utilized_count = session.query(func.count(Device.id)).filter(
            Device.state.in_(['allocated', 'busy', 'testing'])
        ).scalar()
        
        utilization_rate = round((utilized_count / total_devices * 100), 2) if total_devices > 0 else 0
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "devices": {
                "total": total_devices,
                "by_state": devices_by_state,
                "by_rack": devices_by_rack,
                "utilization_rate_percent": utilization_rate
            },
            "allocations": {
                "today": allocations_today,
                "active": active_allocations,
                "avg_duration_minutes": avg_allocation_duration
            }
        }
        
        return json(metrics, status=200)
        
    except Exception as e:
        return json({"error": str(e)}, status=500)
    finally:
        session.close()
