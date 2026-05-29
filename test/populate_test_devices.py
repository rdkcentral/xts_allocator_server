#!/usr/bin/env python3
"""Populate database with test devices for development."""

from models import SessionLocal, Device, Rack

def populate_test_devices():
    """Add test devices: pi5.local, spark.local, mac.local, hpz4.local."""
    session = SessionLocal()
    try:
        # Create a test rack if it doesn't exist
        test_rack = session.query(Rack).filter_by(name="TestRack").first()
        if not test_rack:
            test_rack = Rack(
                name="TestRack",
                location="Development Lab",
                building="Local Network",
                description="Test devices on local network"
            )
            session.add(test_rack)
            session.commit()
            print(f"✓ Created rack: {test_rack.name} (ID: {test_rack.id})")
        else:
            print(f"✓ Using existing rack: {test_rack.name} (ID: {test_rack.id})")

        # Define test devices with ping commands in control_uris
        test_devices = [
            {
                "slot_name": "pi5-slot",
                "make": "Raspberry Pi",
                "model": "Pi 5",
                "description": "Raspberry Pi 5 development board",
                "platform": "ARM64/Linux",
                "tags": "arm,linux,sbc,development",
                "host_ipv4": "pi5.local",
                "control_uris": {
                    "ping": "ping -c 4 pi5.local",
                    "ssh": "ssh pi@pi5.local"
                },
                "state": "free"
            },
            {
                "slot_name": "spark-slot",
                "make": "Generic",
                "model": "Unknown",
                "description": "Spark development machine",
                "platform": "x86_64/Linux",
                "tags": "x86,linux,development",
                "host_ipv4": "spark.local",
                "control_uris": {
                    "ping": "ping -c 4 spark.local",
                    "ssh": "ssh user@spark.local"
                },
                "state": "free"
            },
            {
                "slot_name": "mac-slot",
                "make": "Apple",
                "model": "Unknown Mac",
                "description": "Mac development machine",
                "platform": "macOS",
                "tags": "mac,macos,development",
                "host_ipv4": "mac.local",
                "control_uris": {
                    "ping": "ping -c 4 mac.local",
                    "ssh": "ssh user@mac.local"
                },
                "state": "free"
            },
            {
                "slot_name": "hpz4-slot",
                "make": "HP",
                "model": "Z4 Workstation",
                "description": "HP Z4 development workstation (local PC)",
                "platform": "x86_64/Linux",
                "tags": "x86,linux,workstation,local",
                "host_ipv4": "hpz4.local",
                "control_uris": {
                    "ping": "ping -c 4 hpz4.local",
                    "localhost": "localhost",
                    "ssh": "ssh gweatherup@hpz4.local"
                },
                "state": "free"
            }
        ]

        # Add devices
        added_count = 0
        updated_count = 0
        
        for device_data in test_devices:
            # Check if device already exists
            existing = session.query(Device).filter_by(
                rack_id=test_rack.id,
                slot_name=device_data["slot_name"]
            ).first()
            
            if existing:
                # Update existing device
                for key, value in device_data.items():
                    if key != "slot_name":  # Don't update slot_name
                        setattr(existing, key, value)
                updated_count += 1
                print(f"✓ Updated device: {device_data['slot_name']} ({device_data['description']})")
            else:
                # Create new device
                device = Device(
                    rack_id=test_rack.id,
                    **device_data
                )
                session.add(device)
                added_count += 1
                print(f"✓ Added device: {device_data['slot_name']} ({device_data['description']})")
        
        session.commit()
        
        print(f"\n✓ Database populated successfully!")
        print(f"  - Added: {added_count} new devices")
        print(f"  - Updated: {updated_count} existing devices")
        print(f"  - Total: {added_count + updated_count} test devices")
        
        # Show summary
        print(f"\nTest devices in TestRack:")
        devices = session.query(Device).filter_by(rack_id=test_rack.id).all()
        for device in devices:
            print(f"  - ID {device.id}: {device.slot_name} ({device.host_ipv4}) - {device.state}")
        
    except Exception as e:
        print(f"✗ Error populating database: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    populate_test_devices()
