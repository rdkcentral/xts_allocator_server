#!/usr/bin/env python3
"""
Add real Raspberry Pi test devices to the database.

These are actual devices on the network (pi5.local and pi4.local)
that can be used for real testing via SSH.
"""
from models import SessionLocal, Device, Rack
from datetime import datetime

def add_pi_devices():
    session = SessionLocal()
    try:
        # Create or get "Test Lab" rack
        test_rack = session.query(Rack).filter_by(name="Test Lab").first()
        if not test_rack:
            test_rack = Rack(
                name="Test Lab",
                location="Local Network",
                building="Development",
                description="Local test devices for development and testing"
            )
            session.add(test_rack)
            session.flush()  # Get the rack ID
            print(f"✅ Created rack: {test_rack.name}")
        else:
            print(f"ℹ️  Using existing rack: {test_rack.name}")

        # Add Raspberry Pi 5
        pi5 = session.query(Device).filter_by(slot_name="pi5").first()
        if not pi5:
            pi5 = Device(
                rack_id=test_rack.id,
                slot_name="pi5",
                make="Raspberry Pi Foundation",
                model="Raspberry Pi 5",
                model_alias="Pi5",
                platform="raspberrypi",
                description="Raspberry Pi 5 - Local development/test device",
                
                # Network configuration
                host_ipv4="pi5.local",  # mDNS hostname
                
                # Control URIs for SSH access
                control_uris={
                    "ssh": "ssh://pi5.local",
                    "hostname": "pi5.local"
                },
                
                # Tags for search/filtering
                tags="raspberry-pi,linux,arm64,test-device,local",
                
                # State
                state="free",
                state_changed_at=datetime.utcnow(),
                
                # Connectivity
                connectivity_status="online",
                last_seen=datetime.utcnow(),
                
                # Allocation type
                allocation_type="temporary"
            )
            session.add(pi5)
            print(f"✅ Added device: Raspberry Pi 5 (pi5.local)")
        else:
            print(f"ℹ️  Device already exists: pi5 (updating details)")
            pi5.host_ipv4 = "pi5.local"
            pi5.control_uris = {
                "ssh": "ssh://pi5.local",
                "hostname": "pi5.local"
            }
            pi5.tags = "raspberry-pi,linux,arm64,test-device,local"
            pi5.connectivity_status = "online"
            pi5.last_seen = datetime.utcnow()
            # Reset to free state
            pi5.state = "free"
            pi5.owner_email = None
            pi5.allocation_expiry = None

        # Add Raspberry Pi 4
        pi4 = session.query(Device).filter_by(slot_name="pi4").first()
        if not pi4:
            pi4 = Device(
                rack_id=test_rack.id,
                slot_name="pi4",
                make="Raspberry Pi Foundation",
                model="Raspberry Pi 4",
                model_alias="Pi4",
                platform="raspberrypi",
                description="Raspberry Pi 4 - Local development/test device",
                
                # Network configuration
                host_ipv4="pi4.local",  # mDNS hostname
                
                # Control URIs for SSH access
                control_uris={
                    "ssh": "ssh://pi4.local",
                    "hostname": "pi4.local"
                },
                
                # Tags for search/filtering
                tags="raspberry-pi,linux,arm64,test-device,local",
                
                # State
                state="free",
                state_changed_at=datetime.utcnow(),
                
                # Connectivity
                connectivity_status="online",
                last_seen=datetime.utcnow(),
                
                # Allocation type
                allocation_type="temporary"
            )
            session.add(pi4)
            print(f"✅ Added device: Raspberry Pi 4 (pi4.local)")
        else:
            print(f"ℹ️  Device already exists: pi4 (updating details)")
            pi4.host_ipv4 = "pi4.local"
            pi4.control_uris = {
                "ssh": "ssh://pi4.local",
                "hostname": "pi4.local"
            }
            pi4.tags = "raspberry-pi,linux,arm64,test-device,local"
            pi4.connectivity_status = "online"
            pi4.last_seen = datetime.utcnow()
            # Reset to free state
            pi4.state = "free"
            pi4.owner_email = None
            pi4.allocation_expiry = None

        session.commit()
        
        print("\n" + "="*70)
        print("🎉 Raspberry Pi devices added/updated successfully!")
        print("="*70)
        print(f"\n📦 Rack: {test_rack.name} (ID: {test_rack.id})")
        print(f"   Location: {test_rack.location}")
        print(f"   Building: {test_rack.building}")
        print(f"\n🖥️  Devices:")
        print(f"   1. Raspberry Pi 5")
        print(f"      - Hostname: pi5.local")
        print(f"      - SSH: ssh://pi5.local")
        print(f"      - State: {pi5.state}")
        print(f"      - ID: {pi5.id}")
        print(f"\n   2. Raspberry Pi 4")
        print(f"      - Hostname: pi4.local")
        print(f"      - SSH: ssh://pi4.local")
        print(f"      - State: {pi4.state}")
        print(f"      - ID: {pi4.id}")
        print(f"\n💡 Usage:")
        print(f"   - Allocate via device ID or platform='raspberrypi'")
        print(f"   - Search by tags: 'raspberry-pi', 'test-device', 'local'")
        print(f"   - Access via SSH: ssh pi5.local or ssh pi4.local")
        print(f"   - Control URIs stored for automation\n")
        
    except Exception as e:
        print(f"❌ Error adding Pi devices: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_pi_devices()
