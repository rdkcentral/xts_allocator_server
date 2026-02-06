from sanic import Sanic, response
from routes.allocation_routes import allocation_routes
from routes.device_routes import device_routes
from routes.rack_routes import rack_routes
from routes.export_routes import export_routes
from routes.health_routes import health_routes
from routes.usage_routes import usage_routes
from routes.federation_routes import federation_routes
from routes.test_routes import test_routes
from models import SessionLocal, Device, TestExecution
from state_machine import DeviceState, transition_device
from logging_config import setup_logging, get_logger
from datetime import datetime, timedelta
import os
import sys
import signal
import asyncio

# Setup logging
logger = setup_logging()

app = Sanic("XTS_Allocator_Server")

# Register routes
app.blueprint(allocation_routes)
app.blueprint(device_routes)
app.blueprint(rack_routes)
app.blueprint(export_routes)
app.blueprint(health_routes)
app.blueprint(usage_routes)
app.blueprint(federation_routes)
app.blueprint(test_routes)
app.static('/logo.png', './logo.png', name='logo')
app.static('/xts_allocator.xts', './config/xts_allocator.xts', name='xts_config')


async def check_expired_allocations():
    """Background task to check expired allocations and hung tests."""
    logger = get_logger()
    
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            session = SessionLocal()
            try:
                now = datetime.utcnow()
                
                # 1. Check for expired allocations (skip devices in testing state)
                expired_devices = session.query(Device).filter(
                    Device.state == DeviceState.ALLOCATED.value,
                    Device.allocation_type == "temporary",
                    Device.allocation_expiry.isnot(None),
                    Device.allocation_expiry <= now
                ).all()
                
                if expired_devices:
                    logger.info(f"Found {len(expired_devices)} expired allocations")
                
                for device in expired_devices:
                    logger.info(f"Expiring allocation for device {device.id} (owner: {device.owner_email})")
                    
                    # Transition to resetting state
                    success, message = transition_device(device, DeviceState.RESETTING.value, session)
                    if success:
                        logger.info(f"Device {device.id} transitioned to resetting")
                    else:
                        logger.error(f"Failed to transition device {device.id}: {message}")
                
                # 2. Check for hung tests (no heartbeat or exceeded max duration)
                active_tests = session.query(TestExecution).filter(
                    TestExecution.end_time.is_(None)
                ).all()
                
                for test in active_tests:
                    test_duration = (now - test.start_time).total_seconds() / 60
                    
                    # Check max duration exceeded
                    if test_duration > test.max_duration:
                        logger.warning(f"Test {test.id} exceeded max duration ({test.max_duration}min), marking as timeout")
                        test.end_time = now
                        test.status = "timeout"
                        test.error_message = f"Test exceeded maximum duration of {test.max_duration} minutes"
                        
                        # Transition device back to allocated or resetting
                        device = session.query(Device).filter(Device.id == test.device_id).first()
                        if device and device.state == DeviceState.TESTING.value:
                            success, message = transition_device(device, DeviceState.RESETTING.value, session)
                            if success:
                                logger.info(f"Device {device.id} transitioned to resetting after test timeout")
                        continue
                    
                    # Check heartbeat timeout
                    if test.last_heartbeat:
                        minutes_since_heartbeat = (now - test.last_heartbeat).total_seconds() / 60
                        if minutes_since_heartbeat > test.heartbeat_timeout:
                            logger.warning(f"Test {test.id} has not sent heartbeat for {minutes_since_heartbeat:.1f}min, marking as hung")
                            test.end_time = now
                            test.status = "hung"
                            test.error_message = f"No heartbeat received for {minutes_since_heartbeat:.1f} minutes (timeout: {test.heartbeat_timeout}min)"
                            
                            # Transition device to resetting
                            device = session.query(Device).filter(Device.id == test.device_id).first()
                            if device and device.state == DeviceState.TESTING.value:
                                success, message = transition_device(device, DeviceState.RESETTING.value, session)
                                if success:
                                    logger.info(f"Device {device.id} transitioned to resetting after hung test")
                
                session.commit()
                
            except Exception as e:
                logger.error(f"Error in expiry/hung test check: {e}", exc_info=True)
                session.rollback()
            finally:
                session.close()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Critical error in expiry task: {e}")


@app.before_server_start
async def start_expiry_task(app, loop):
    """Start the background expiry checker when server starts."""
    app.ctx.expiry_task = asyncio.create_task(check_expired_allocations())


@app.before_server_stop
async def stop_expiry_task(app, loop):
    """Stop the background task when server stops."""
    if hasattr(app.ctx, 'expiry_task'):
        app.ctx.expiry_task.cancel()
        try:
            await app.ctx.expiry_task
        except asyncio.CancelledError:
            pass


# Serve the main page
@app.route("/")
async def main_page(request):
    return await response.file(os.path.join("templates", "index.html"))


# Serve the dashboard
@app.route("/dashboard")
async def dashboard_page(request):
    return await response.file(os.path.join("templates", "dashboard.html"))


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger = get_logger()
    signal_name = signal.Signals(sig).name
    logger.info(f"Received {signal_name} signal, shutting down gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command
    
    try:
        logger.info("Starting XTS Allocator Server...")
        app.run(host="0.0.0.0",
                port=5000,
                single_process=True)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.error("❌ Port 5000 is already in use. Stop the existing server first.")
            logger.error("   Run: lsof -ti:5000 | xargs kill")
            sys.exit(1)
        else:
            logger.error(f"❌ Network error: {e}")
            sys.exit(2)
    except PermissionError as e:
        logger.error(f"❌ Permission denied: {e}")
        logger.error("   Check file permissions or try running with appropriate privileges")
        sys.exit(3)
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.error("   Run: pip install -r requirements.txt")
        sys.exit(4)
    except Exception as e:
        logger.error(f"❌ Unexpected error starting server: {e}", exc_info=True)
        sys.exit(5)
    finally:
        logger.info("XTS Allocator Server stopped")
