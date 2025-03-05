from models import SessionLocal, Device

def populate_database():
    session = SessionLocal()
    try:
        # Clear existing data for a clean start
        session.query(Device).delete()

        # Add sample devices
        devices = [
            Device(rack_name="Rack1", slot_name="Slot1", description="Device in Rack1", tags="network,router", platform="Cisco", state="free"),
            Device(rack_name="Rack2", slot_name="Slot2", description="Device in Rack2", tags="storage,backup", platform="Dell", state="free"),
            Device(rack_name="Rack3", slot_name="Slot3", description="Test device", tags="test,lab", platform="HP", state="free"),
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
