from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import config
from datetime import datetime, timezone
import os

# Get database URL from config
DATABASE_URL = config.get_database_url(echo=os.environ.get("SQL_ECHO", "true").lower() == "true")

Base = declarative_base()

# Engine configuration for PostgreSQL vs SQLite
engine_kwargs = {"echo": os.environ.get("SQL_ECHO", "true").lower() == "true"}

if config.DB_TYPE == "postgresql":
    # PostgreSQL-specific settings
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 3600    # Recycle connections after 1 hour
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Rack(Base):
    """Rack model for organizing devices by physical location.
    
    Represents a physical rack in a building/location that contains multiple device slots.
    """
    __tablename__ = "racks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)  # e.g., "190.02", "cats-rack-sn-627"
    location = Column(String, nullable=True)  # Room/floor identifier
    building = Column(String, nullable=True)  # Building name/code
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship to devices in this rack
    devices = relationship("Device", back_populates="rack", cascade="all, delete-orphan")

class Device(Base):
    """Device/STB model for allocation management.
    
    Expanded model for Set-Top Box management with hardware specs, network info,
    control URIs, and external equipment tracking.
    """
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Rack relationship
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=False, index=True)
    rack = relationship("Rack", back_populates="devices")
    slot_name = Column(String, nullable=False)  # e.g., "14(A14)", "Slot1"
    
    # Hardware specifications
    make = Column(String, nullable=True)  # e.g., "Candela"
    model = Column(String, nullable=True)  # e.g., "LF350"
    model_alias = Column(String, nullable=True)  # e.g., "RFElectronics-Chamber-HDRF-1560-Q"
    serial_number = Column(String, nullable=True)
    manufacturer = Column(String, nullable=True)
    firmware = Column(String, nullable=True)
    
    # Network information
    host_mac = Column(String, nullable=True)  # e.g., "00:0D:B9:46:3E:8C"
    host_ipv4 = Column(String, nullable=True)
    host_ipv6 = Column(String, nullable=True)
    
    # Control URIs (JSON for flexibility)
    # Example: {"video": "axis://...", "remote": "irnetboxpro3://...", "power": "synaccess://..."}
    control_uris = Column(JSON, nullable=True)
    
    # External equipment (JSON array)
    # Example: [{"type": "camera", "name": "Axis", "model": "...", "notes": "..."}]
    external_equipment = Column(JSON, nullable=True)
    
    # Allocation and state management
    platform = Column(String, nullable=True, index=True)  # e.g., "Cisco", "Dell"
    tags = Column(String, nullable=True)  # Comma-separated for now, consider proper tagging later
    description = Column(String, nullable=True)
    state = Column(String, default="free", nullable=False, index=True)  # free, allocated, busy, resetting, maintenance, offline
    state_changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Allocation details
    owner_email = Column(String, nullable=True, index=True)
    allocation_type = Column(String, default="temporary", nullable=False)  # temporary (with expiry) or permanent (no expiry)
    allocation_expiry = Column(DateTime, nullable=True)  # When allocation expires (null for permanent)
    software_version = Column(String, nullable=True)  # Software version on device
    last_verified = Column(DateTime, nullable=True)  # Last health check/verification
    
    # Device status tracking (for live monitoring)
    last_seen = Column(DateTime, nullable=True)  # Last time device was seen/reported
    connectivity_status = Column(String, nullable=True)  # online, offline, unreachable
    system_metrics = Column(JSON, nullable=True)  # CPU, memory, uptime, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('rack_id', 'slot_name', name='uix_rack_slot'),
        Index('ix_device_state_rack', 'state', 'rack_id'),
    )
    
    # Relationships
    allocations = relationship("AllocationHistory", back_populates="device")

class AllocationHistory(Base):
    """Allocation history for audit trail.
    
    Tracks all allocation and deallocation events for compliance and debugging.
    """
    __tablename__ = "allocation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    
    # User information
    user = Column(String)  # Username (if available)
    email = Column(String, nullable=False, index=True)
    name = Column(String)  # Full name (if available)
    
    # Allocation timing
    start_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime, nullable=True)
    duration_requested = Column(Integer, nullable=True)  # Minutes requested
    allocation_type = Column(String, default="temporary")  # temporary or permanent
    
    # State tracking
    state_before = Column(String, nullable=True)  # State before allocation
    state_after = Column(String, nullable=True)  # State after deallocation
    software_version = Column(String, nullable=True)  # Software version at allocation time
    
    # Test execution tracking (usage statistics)
    test_execution_count = Column(Integer, default=0)  # Number of tests run during this allocation
    total_test_time = Column(Integer, default=0)  # Total minutes spent in testing state
    idle_time = Column(Integer, default=0)  # Total minutes idle (allocated but not testing)
    
    # Relationships
    device = relationship("Device", back_populates="allocations")

class Server(Base):
    """Server model for federated multi-server architecture.
    
    Tracks slave servers that register with the master server.
    """
    __tablename__ = "servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # Server identifier
    url = Column(String, nullable=False, unique=True)  # Base URL (e.g., http://192.168.1.100:5000)
    location = Column(String, nullable=True)  # Physical location (office, floor, building)
    role = Column(String, default="slave", nullable=False)  # master or slave
    status = Column(String, default="online", nullable=False)  # online, offline, unreachable
    device_count = Column(Integer, default=0)  # Cached device count
    last_heartbeat = Column(DateTime, nullable=True)  # Last heartbeat from slave
    server_metadata = Column(JSON, nullable=True)  # Additional server metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TestExecution(Base):
    """Test execution tracking for active test runs.
    
    Tracks test lifecycle from start to completion with heartbeat monitoring.
    Links to allocation history for complete audit trail.
    """
    __tablename__ = "test_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    allocation_history_id = Column(Integer, ForeignKey("allocation_history.id"), nullable=True, index=True)
    
    # Test information
    test_name = Column(String, nullable=False)
    test_suite = Column(String, nullable=True)
    expected_duration = Column(Integer, nullable=True)  # Expected duration in minutes
    max_duration = Column(Integer, default=240)  # Maximum allowed duration (4 hours default)
    
    # Test lifecycle
    start_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    end_time = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    heartbeat_timeout = Column(Integer, default=10)  # Minutes without heartbeat before considering hung
    
    # Test results
    status = Column(String, nullable=True)  # success, failure, error, timeout, hung
    exit_code = Column(Integer, nullable=True)
    logs_url = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Metadata
    test_metadata = Column(JSON, nullable=True)  # Additional test-specific data
    
    # Relationships
    device = relationship("Device")
    allocation_history = relationship("AllocationHistory")

class AuditLog(Base):
    """Audit log for security and compliance tracking.
    
    Records all authentication attempts, authorization decisions, and privileged operations
    for security auditing, compliance, and forensic analysis.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Event categorization
    event_type = Column(String, nullable=False, index=True)  # auth_login, auth_failure, auth_logout, allocation, deallocation, state_change, device_add, device_update, device_delete, test_start, test_end, unauthorized_access
    event_category = Column(String, nullable=False, index=True)  # authentication, authorization, device_operation, test_operation, admin_operation
    severity = Column(String, nullable=False, default="info")  # debug, info, warning, error, critical
    
    # Actor information
    user_email = Column(String, nullable=True, index=True)  # Email of user performing action
    user_role = Column(String, nullable=True)  # Role at time of action (admin, engineer, readonly)
    source_ip = Column(String, nullable=True)  # IP address of request
    user_agent = Column(String, nullable=True)  # User agent string
    
    # Action details
    action = Column(String, nullable=False)  # Human-readable action description
    resource_type = Column(String, nullable=True, index=True)  # device, rack, allocation, test, server
    resource_id = Column(Integer, nullable=True, index=True)  # ID of affected resource
    
    # Request details
    endpoint = Column(String, nullable=True)  # API endpoint called
    http_method = Column(String, nullable=True)  # GET, POST, PUT, DELETE
    request_id = Column(String, nullable=True, index=True)  # Unique request identifier for correlation
    
    # Result
    success = Column(String, nullable=False, default="true")  # "true" or "false" for compatibility
    status_code = Column(Integer, nullable=True)  # HTTP status code
    error_message = Column(String, nullable=True)  # Error message if failed
    
    # Additional context
    details = Column(JSON, nullable=True)  # Additional structured data (before/after values, etc.)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_user_time', 'user_email', 'timestamp'),
        Index('idx_audit_event_time', 'event_type', 'timestamp'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )