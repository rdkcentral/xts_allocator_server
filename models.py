from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import Config

DATABASE_URL = Config.DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Device(Base):
    """Device/STB model for allocation management.
    
    TODO: This model needs major expansion for STB requirements!
    See TODO.md task #3 for full requirements:
    - Hardware fields (Make, Model, Serial, Firmware, etc.)
    - Network fields (MAC, IPv4, IPv6)
    - Control URIs (JSON field for Video, Remote, Power, etc.)
    - External equipment (JSON field for cameras, IR blasters, etc.)
    - Enhanced state management (free/allocated/busy/resetting/maintenance)
    - Allocation tracking (expiry, software_version, last_verified)
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rack_name = Column(String, nullable=False)  # TODO: Replace with rack_id FK after Rack model added
    slot_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # TODO: comma-separated is fragile, consider proper tag matching
    platform = Column(String, nullable=True)
    state = Column(String, default="free")  # TODO: Expand to full state machine (task #6)
    owner_email = Column(String, nullable=True)  # TODO: Add email validation

class AllocationHistory(Base):
    """Allocation history for audit trail.
    
    TODO: This model is defined but never populated!
    Need to create records in allocate_slot and deallocate_slot.
    See TODO.md task #9 for implementation details.
    """
    __tablename__ = "allocation_history"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    user = Column(String)
    email = Column(String)
    name = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    # TODO: Add duration_requested, software_version fields

    device = relationship("Device", back_populates="allocations")

Device.allocations = relationship("AllocationHistory", back_populates="device")
