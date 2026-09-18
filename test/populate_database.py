from models import SessionLocal, Device, Rack

def populate_database():
    session = SessionLocal()
    try:
        # Clear existing data for a clean start
        session.query(Device).delete()
        session.query(Rack).delete()
        session.commit()

        # Add sample racks first
        racks = [
            Rack(name="Rack1", location="Lab A", building="Building 1"),
            Rack(name="Rack2", location="Lab B", building="Building 1"),
            Rack(name="Rack3", location="Lab C", building="Building 2"),
        ]
        session.add_all(racks)
        session.commit()

        # Add sample devices
        devices = [
            Device(rack_id=1, slot_name="Slot1", description="Device in Rack1", tags="network,router", platform="Cisco", state="free"),
            Device(rack_id=2, slot_name="Slot2", description="Device in Rack2", tags="storage,backup", platform="Dell", state="free"),
            Device(rack_id=3, slot_name="Slot3", description="Test device", tags="test,lab", platform="HP", state="free"),
        ]
        session.add_all(devices)
        session.commit()
        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    populate_database()
