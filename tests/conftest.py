"""Pytest configuration and fixtures for test suite."""

import pytest
import os
from models import Base, engine, SessionLocal, Device, Rack, Server, TestExecution, AllocationHistory, AuditLog
from app import app as sanic_app
from auth import generate_token, ROLE_ENGINEER, ROLE_ADMIN, ROLE_READONLY
from rate_limiter import get_rate_limiter

# Ensure tests always use test database
os.environ['XTS_MODE'] = 'test'
os.environ['SQLITE_DB_PATH'] = 'xts_allocator_test.db'

# Create all tables once at the start of the test session
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Set up database tables for all tests."""
    Base.metadata.create_all(bind=engine)
    yield
    # Optionally clean up after all tests
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function", autouse=True)
def clean_database():
    """Clean database before AND after each test to ensure isolation."""
    # Reset rate limiter between tests
    get_rate_limiter().reset()

    # Clean before test
    session = SessionLocal()
    try:
        session.query(AllocationHistory).delete()
        session.query(TestExecution).delete()
        session.query(Device).delete()
        session.query(Rack).delete()
        session.query(Server).delete()
        session.query(AuditLog).delete()
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

    yield  # Run test
    
    # Clean after test
    session = SessionLocal()
    try:
        session.query(AllocationHistory).delete()
        session.query(TestExecution).delete()
        session.query(Device).delete()
        session.query(Rack).delete()
        session.query(Server).delete()
        session.query(AuditLog).delete()
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def app():
    """Sanic application fixture."""
    return sanic_app


@pytest.fixture
def test_client(app):
    """Test client for making requests."""
    return app.test_client


@pytest.fixture
def auth_headers_engineer():
    """Generate Authorization header for engineer role."""
    token = generate_token("engineer@example.com", ROLE_ENGINEER)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin():
    """Generate Authorization header for admin role."""
    token = generate_token("admin@example.com", ROLE_ADMIN)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_readonly():
    """Generate Authorization header for readonly role."""
    token = generate_token("viewer@example.com", ROLE_READONLY)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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
