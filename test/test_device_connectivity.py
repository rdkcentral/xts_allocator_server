#!/usr/bin/env python3
"""Test connectivity to devices in the allocator."""

import subprocess
import sys
from models import SessionLocal, Device

def ping_device(device):
    """Ping a device and return status."""
    if not device.control_uris or 'ping' not in device.control_uris:
        return None, "No ping command configured"
    
    ping_cmd = device.control_uris['ping']
    try:
        result = subprocess.run(
            ping_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Extract response time from ping output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'time=' in line:
                    time_part = line.split('time=')[1].split()[0]
                    return True, f"{time_part} ms"
            return True, "Success"
        else:
            return False, "Unreachable"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def test_all_devices():
    """Test connectivity to all devices."""
    session = SessionLocal()
    try:
        devices = session.query(Device).all()
        
        if not devices:
            print("No devices found in database.")
            print("Run: python test/populate_test_devices.py")
            return
        
        print(f"\nTesting connectivity to {len(devices)} devices...\n")
        print(f"{'ID':<4} {'Host':<20} {'Platform':<20} {'Status':<15} {'Response'}")
        print("-" * 80)
        
        online_count = 0
        offline_count = 0
        
        for device in devices:
            host = device.host_ipv4 or "No hostname"
            platform = device.platform or "Unknown"
            
            success, message = ping_device(device)
            
            if success is None:
                status = "⚠ No ping cmd"
                status_color = ""
            elif success:
                status = "✓ Online"
                status_color = "\033[32m"  # Green
                online_count += 1
            else:
                status = "✗ Offline"
                status_color = "\033[31m"  # Red
                offline_count += 1
            
            reset_color = "\033[0m"
            print(f"{device.id:<4} {host:<20} {platform:<20} {status_color}{status:<15}{reset_color} {message}")
        
        print("-" * 80)
        print(f"\nSummary: {online_count} online, {offline_count} offline, {len(devices) - online_count - offline_count} untested\n")
        
    except Exception as e:
        print(f"Error testing devices: {e}")
        raise
    finally:
        session.close()

def test_single_device(device_id):
    """Test connectivity to a single device."""
    session = SessionLocal()
    try:
        device = session.query(Device).filter_by(id=device_id).first()
        
        if not device:
            print(f"Device ID {device_id} not found.")
            return
        
        print(f"\nTesting device {device.id}:")
        print(f"  Host: {device.host_ipv4}")
        print(f"  Platform: {device.platform}")
        print(f"  Description: {device.description}")
        
        if device.control_uris and 'ping' in device.control_uris:
            print(f"  Ping command: {device.control_uris['ping']}")
            print(f"\nRunning ping test...")
            
            success, message = ping_device(device)
            
            if success:
                print(f"  ✓ Device is ONLINE - {message}")
            else:
                print(f"  ✗ Device is OFFLINE - {message}")
        else:
            print(f"  ⚠ No ping command configured")
        
        # Show SSH command if available
        if device.control_uris and 'ssh' in device.control_uris:
            print(f"\nSSH command: {device.control_uris['ssh']}")
        
    except Exception as e:
        print(f"Error testing device: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            device_id = int(sys.argv[1])
            test_single_device(device_id)
        except ValueError:
            print(f"Invalid device ID: {sys.argv[1]}")
            print("Usage: python test/test_device_connectivity.py [device_id]")
    else:
        test_all_devices()
