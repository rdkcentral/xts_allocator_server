from sanic import Blueprint
from sanic.response import json, text
from models import SessionLocal, Device, AllocationHistory, TestExecution
from sqlalchemy import func
from datetime import datetime, timedelta
from prometheus_metrics import format_prometheus_metrics, calculate_utilization
from openapi_spec import generate_openapi_spec

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
    """Get system metrics for monitoring and analytics.
    
    Query parameters:
    - format: 'json' (default) or 'prometheus'
    
    Returns JSON format by default, Prometheus text format if format=prometheus
    """
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
        
        # Test execution metrics
        tests_running = session.query(func.count(TestExecution.id)).filter(
            TestExecution.end_time.is_(None)
        ).scalar()
        
        tests_completed_today = session.query(func.count(TestExecution.id)).filter(
            TestExecution.start_time >= today_start,
            TestExecution.end_time.isnot(None)
        ).scalar()
        
        # Average test duration
        avg_test_duration_query = session.query(
            func.avg(
                func.julianday(TestExecution.end_time) - func.julianday(TestExecution.start_time)
            ) * 24 * 60
        ).filter(
            TestExecution.start_time >= today_start,
            TestExecution.end_time.isnot(None)
        ).scalar()
        
        avg_test_duration = round(avg_test_duration_query, 2) if avg_test_duration_query else 0
        
        # Utilization rate
        utilization_rate = calculate_utilization(devices_by_state, total_devices)
        
        # Build metrics dictionary
        metrics_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_devices": total_devices,
            "devices_by_state": devices_by_state,
            "devices_by_rack": devices_by_rack,
            "utilization_percent": utilization_rate,
            "allocations_today": allocations_today or 0,
            "active_allocations": active_allocations or 0,
            "avg_allocation_duration_minutes": avg_allocation_duration,
            "tests_running": tests_running or 0,
            "tests_completed_today": tests_completed_today or 0,
            "avg_test_duration_minutes": avg_test_duration
        }
        
        # Check format parameter
        format_param = request.args.get("format", "json")
        
        if format_param == "prometheus":
            # Return Prometheus text format
            prometheus_text = format_prometheus_metrics(metrics_data)
            return text(prometheus_text, content_type="text/plain; version=0.0.4")
        else:
            # Return JSON format (backward compatible)
            return json({
                "timestamp": metrics_data["timestamp"],
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
                },
                "tests": {
                    "running": tests_running,
                    "completed_today": tests_completed_today,
                    "avg_duration_minutes": avg_test_duration
                }
            }, status=200)
        
    except Exception as e:
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@health_routes.get("/metrics/prometheus")
async def get_prometheus_metrics(request):
    """Dedicated Prometheus metrics endpoint (always returns Prometheus format)."""
    session = SessionLocal()
    try:
        # Re-use metrics collection logic from main endpoint
        # (Same code as get_metrics but always return Prometheus format)
        
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
        
        # Average allocation duration
        avg_duration_query = session.query(
            func.avg(
                func.julianday(AllocationHistory.end_time) - func.julianday(AllocationHistory.start_time)
            ) * 24 * 60
        ).filter(
            AllocationHistory.start_time >= today_start,
            AllocationHistory.end_time.isnot(None)
        ).scalar()
        
        avg_allocation_duration = round(avg_duration_query, 2) if avg_duration_query else 0
        
        # Test execution metrics
        tests_running = session.query(func.count(TestExecution.id)).filter(
            TestExecution.end_time.is_(None)
        ).scalar()
        
        tests_completed_today = session.query(func.count(TestExecution.id)).filter(
            TestExecution.start_time >= today_start,
            TestExecution.end_time.isnot(None)
        ).scalar()
        
        # Average test duration
        avg_test_duration_query = session.query(
            func.avg(
                func.julianday(TestExecution.end_time) - func.julianday(TestExecution.start_time)
            ) * 24 * 60
        ).filter(
            TestExecution.start_time >= today_start,
            TestExecution.end_time.isnot(None)
        ).scalar()
        
        avg_test_duration = round(avg_test_duration_query, 2) if avg_test_duration_query else 0
        
        # Utilization rate
        utilization_rate = calculate_utilization(devices_by_state, total_devices)
        
        # Build metrics dictionary
        metrics_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_devices": total_devices,
            "devices_by_state": devices_by_state,
            "devices_by_rack": devices_by_rack,
            "utilization_percent": utilization_rate,
            "allocations_today": allocations_today or 0,
            "avg_allocation_duration_minutes": avg_allocation_duration,
            "tests_running": tests_running or 0,
            "tests_completed_today": tests_completed_today or 0,
            "avg_test_duration_minutes": avg_test_duration
        }
        
        # Always return Prometheus format
        prometheus_text = format_prometheus_metrics(metrics_data)
        return text(prometheus_text, content_type="text/plain; version=0.0.4")
        
    except Exception as e:
        return json({"error": str(e)}, status=500)
    finally:
        session.close()


@health_routes.get("/openapi.json")
async def get_openapi_spec(request):
    """Get OpenAPI 3.0 specification."""
    try:
        spec = generate_openapi_spec()
        return json(spec, status=200)
    except Exception as e:
        return json({"error": str(e)}, status=500)
