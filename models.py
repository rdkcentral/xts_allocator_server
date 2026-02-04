from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import Config
from datetime import datetime

DATABASE_URL = Config.DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=True)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    state_changed_at = Column(DateTime, default=datetime.utcnow)
    
    # Allocation details
    owner_email = Column(String, nullable=True, index=True)
    allocation_expiry = Column(DateTime, nullable=True)  # When allocation expires
    software_version = Column(String, nullable=True)  # Software version on device
    last_verified = Column(DateTime, nullable=True)  # Last health check/verification
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_requested = Column(Integer, nullable=True)  # Minutes requested
    
    # State tracking
    state_before = Column(String, nullable=True)  # State before allocation
    state_after = Column(String, nullable=True)  # State after deallocation
    software_version = Column(String, nullable=True)  # Software version at allocation time
    
    # Relationships
    device = relationship("Device", back_populates="allocations")
