#!/usr/bin/env python3
"""
Simplified Pi device workflow demonstration.
Shows complete allocation lifecycle without API calls.
"""

import sys
import time
from datetime import datetime, timedelta, timezone
from models import SessionLocal, Device, AllocationHistory, TestExecution
from state_machine import transition_device, DeviceState

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def main():
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║     RASPBERRY PI WORKFLOW - DATABASE DEMONSTRATION                   ║")
    print("║     Shows complete lifecycle using direct database operations        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    session = SessionLocal()
    try:
        # STEP 1: Find available Pi device
        print_header("STEP 1: Find Available Raspberry Pi")
        
        pi_device = session.query(Device).filter_by(
            platform="raspberrypi",
            state="free"
        ).first()
        
        if not pi_device:
            print("❌ No free Raspberry Pi devices found!")
            return
        
        print(f"✅ Found device:")
        print(f"   ID: {pi_device.id}")
        print(f"   Model: {pi_device.model}")
        print(f"   Hostname: {pi_device.host_ipv4}")
        print(f"   SSH: {pi_device.control_uris.get('ssh') if pi_device.control_uris else 'N/A'}")
        print(f"   State: {pi_device.state}")
        print(f"   Tags: {pi_device.tags}")
        
        time.sleep(1)
        
        # STEP 2: Allocate the device
        print_header("STEP 2: Allocate Device for 2 Hours")
        
        user_email = "test.engineer@example.com"
        duration_minutes = 120  # 2 hours
        
        # Transition to allocated state
        success, message = transition_device(pi_device, DeviceState.ALLOCATED.value, session)
        if not success:
            print(f"❌ State transition failed: {message}")
            return
        
        # Set allocation details
        pi_device.owner_email = user_email
        pi_device.allocation_type = "temporary"
        pi_device.allocation_expiry = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        
        # Create allocation history
        history = AllocationHistory(
            device_id=pi_device.id,
            email=user_email,
            user="test_engineer",
            name="Test Engineer",
            start_time=datetime.now(timezone.utc),
            duration_requested=duration_minutes,
            allocation_type="temporary"
        )
        session.add(history)
        session.commit()
        
        print(f"✅ Device allocated:")
        print(f"   Owner: {user_email}")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   Expires: {pi_device.allocation_expiry}")
        print(f"   History ID: {history.id}")
        print(f"   Device State: {pi_device.state}")
        
        time.sleep(1)
        
        # STEP 3: Start test
        print_header("STEP 3: Start Test Execution")
        
        # Transition to testing state
        success, message = transition_device(pi_device, DeviceState.TESTING.value, session)
        if not success:
            print(f"❌ State transition failed: {message}")
            return
        
        # Create test execution
        test = TestExecution(
            device_id=pi_device.id,
            allocation_history_id=history.id,
            test_suite="pi_validation_suite",
            test_name="connectivity_and_basic_tests",
            start_time=datetime.now(timezone.utc),
            expected_duration=5,  # 5 minutes
            max_duration=10,  # 10 minutes
            heartbeat_timeout=2,  # 2 minutes
            last_heartbeat=datetime.now(timezone.utc),
            status="running"
        )
        session.add(test)
        session.commit()
        
        print(f"✅ Test started:")
        print(f"   Test ID: {test.id}")
        print(f"   Suite: {test.test_suite}")
        print(f"   Name: {test.test_name}")
        print(f"   Device State: {pi_device.state}")
        print(f"   Expected Duration: {test.expected_duration} min")
        
        print(f"\n⏳ Simulating test execution...")
        time.sleep(2)
        
        print(f"📡 Heartbeat sent (keeping test alive)")
        test.last_heartbeat = datetime.now(timezone.utc)
        session.commit()
        
        time.sleep(1)
        
        # STEP 4: Complete test
        print_header("STEP 4: Complete Test Execution")
        
        test.end_time = datetime.now(timezone.utc)
        test.status = "passed"
        test.exit_code = 0
        
        # Update allocation history with test count
        history.test_execution_count = (history.test_execution_count or 0) + 1
        
        # Transition back to allocated
        success, message = transition_device(pi_device, DeviceState.ALLOCATED.value, session)
        if not success:
            print(f"❌ State transition failed: {message}")
            return
        
        session.commit()
        
        print(f"✅ Test completed:")
        print(f"   Status: {test.status}")
        print(f"   Exit Code: {test.exit_code}")
        duration = int((test.end_time - test.start_time).total_seconds() / 60)
        print(f"   Duration: {duration} minutes")
        print(f"   Device State: {pi_device.state} (back to allocated)")
        
        time.sleep(1)
        
        # STEP 5: Check allocation history
        print_header("STEP 5: Allocation History")
        
        print(f"📊 Current allocation details:")
        print(f"   Allocated at: {history.start_time}")
        print(f"   Duration requested: {history.duration_requested} min")
        print(f"   Test executions: {history.test_execution_count}")
        print(f"   User: {history.email}")
        
        time.sleep(1)
        
        # STEP 6: Deallocate
        print_header("STEP 6: Deallocate Device")
        
        # Complete allocation history
        history.end_time = datetime.now(timezone.utc)
        history.state_after = "free"
        actual_duration = int((history.end_time - history.start_time).total_seconds() / 60)
        
        # Clear device allocation
        pi_device.owner_email = None
        pi_device.allocation_expiry = None
        
        # Transition to resetting (normal workflow before going back to free)
        success, message = transition_device(pi_device, DeviceState.RESETTING.value, session)
        if not success:
            print(f"❌ State transition failed: {message}")
            return
        
        # Immediately transition to free (simulating quick reset)
        success, message = transition_device(pi_device, DeviceState.FREE.value, session)
        if not success:
            print(f"❌ State transition failed: {message}")
            return
        
        session.commit()
        
        print(f"✅ Device deallocated:")
        print(f"   Final state: {pi_device.state}")
        actual_duration = int((history.end_time - history.start_time).total_seconds() / 60)
        print(f"   Allocation duration: {actual_duration} minutes")
        print(f"   History completed: {history.end_time}")
        print(f"   Device available: {pi_device.state == 'free'}")
        
        time.sleep(1)
        
        # SUMMARY
        print_header("WORKFLOW COMPLETE ✅")
        
        print("🎉 Successfully demonstrated:")
        print("   ✅ Device discovery (platform='raspberrypi')")
        print("   ✅ Device allocation with duration")
        print("   ✅ State transitions (free → allocated → testing → allocated → resetting → free)")
        print("   ✅ Test execution tracking")
        print("   ✅ Allocation history")
        print("   ✅ Device deallocation")
        print()
        print("📊 Final Statistics:")
        print(f"   Device: {pi_device.model} ({pi_device.host_ipv4})")
        print(f"   Total allocation time: {actual_duration} minutes")
        print(f"   Tests run: {history.test_execution_count}")
        print(f"   Current state: {pi_device.state}")
        print()
        print("🔗 Real Usage:")
        print(f"   SSH to device: ssh {pi_device.host_ipv4}")
        print("   Run tests via SSH")
        print("   API tracks everything automatically")
        print()
        print("🌐 View dashboard: http://localhost:5000/dashboard")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
