from sanic import Sanic, response
from routes.allocation_routes import allocation_routes
from routes.device_routes import device_routes
from routes.rack_routes import rack_routes
from routes.export_routes import export_routes
from routes.health_routes import health_routes
from models import SessionLocal, Device
from state_machine import DeviceState, transition_device
from logging_config import setup_logging, get_logger
from datetime import datetime
import os
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
app.static('/logo.png', './logo.png', name='logo')
app.static('/xts_allocator.xts', './xts_allocator.xts', name='xts_config')


async def check_expired_allocations():
    """Background task to check and reset expired allocations."""
    logger = get_logger()
    
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            session = SessionLocal()
            try:
                now = datetime.utcnow()
                
                # Find expired allocations
                expired_devices = session.query(Device).filter(
                    Device.state == DeviceState.ALLOCATED.value,
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
                
            except Exception as e:
                logger.error(f"Error in expiry check: {e}")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0",
            port=5000,
            single_process=True)
