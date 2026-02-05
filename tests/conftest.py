"""Pytest configuration and fixtures for test suite."""

import pytest
from models import Base, engine, SessionLocal, Device, Rack
from app import app as sanic_app
from datetime import datetime


@pytest.fixture
def app():
    """Sanic application fixture."""
    return sanic_app


@pytest.fixture
def test_client(app):
    """Test client for making requests."""
    return app.test_client


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # Clean up tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_racks(db_session):
    """Create sample racks for testing."""
    racks = [
        Rack(name="TestRack1", location="Lab A", building="Building 1"),
        Rack(name="TestRack2", location="Lab B", building="Building 2"),
        Rack(name="TestRack3", location="Lab C", building="Building 1")
    ]
    for rack in racks:
        db_session.add(rack)
    db_session.commit()
    return racks


@pytest.fixture
def sample_devices(db_session, sample_racks):
    """Create sample devices for testing."""
    devices = [
        Device(
            rack_id=sample_racks[0].id,
            slot_name="Slot1",
            platform="Cisco",
            tags="network,router",
            state="free",
            make="Cisco",
            model="XR9000"
        ),
        Device(
            rack_id=sample_racks[1].id,
            slot_name="Slot2",
            platform="Dell",
            tags="storage,backup",
            state="free",
            make="Dell",
            model="PowerEdge"
        ),
        Device(
            rack_id=sample_racks[2].id,
            slot_name="Slot3",
            platform="HP",
            tags="test,lab",
            state="free",
            make="HP",
            model="ProLiant"
        ),
        Device(
            rack_id=sample_racks[0].id,
            slot_name="Slot4",
            platform="Cisco",
            tags="network",
            state="maintenance",
            make="Cisco",
            model="XR8000"
        )
    ]
    for device in devices:
        db_session.add(device)
    db_session.commit()
    return devices
