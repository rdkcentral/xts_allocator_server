from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///xts_allocator.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    rack_name = Column(String, nullable=False)
    slot_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # comma-separated tags
    platform = Column(String, nullable=True)
    state = Column(String, default="free")
    owner_email = Column(String, nullable=True)

class AllocationHistory(Base):
    __tablename__ = "allocation_history"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    user = Column(String)
    email = Column(String)
    name = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    device = relationship("Device", back_populates="allocations")

Device.allocations = relationship("AllocationHistory", back_populates="device")

# what database url
# look at dynaconf
