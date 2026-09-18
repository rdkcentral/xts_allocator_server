# Test Devices Setup

## Available Test Devices

Four test devices have been added to the allocator for development and testing:

| ID | Hostname | Platform | Make | Description |
|----|----------|----------|------|-------------|
| 1 | pi5.local | ARM64/Linux | Raspberry Pi | Pi 5 development board |
| 2 | spark.local | x86_64/Linux | Generic | Spark development machine |
| 3 | mac.local | macOS | Apple | Mac development machine |
| 4 | hpz4.local | x86_64/Linux | HP | Z4 Workstation (local PC) |

All devices are in the **TestRack** in the "Development Lab".

## Quick Commands

### List all devices
```bash
xts allocator list
```

### Test device connectivity
```bash
# Test all devices
cd /home/gweatherup/git/fast/sky/xts_allocator_server
source venv/bin/activate
PYTHONPATH=. python test/test_device_connectivity.py

# Test specific device
PYTHONPATH=. python test/test_device_connectivity.py 4
```

### Allocate a device
```bash
# Allocate pi5.local for 2 hours
xts allocator alloc_by_id user@example.com 1 2h

# Allocate by platform
xts allocator alloc_by_platform user@example.com "ARM64/Linux" 1h

# Allocate by tags
xts allocator alloc_by_tags user@example.com "arm,linux" 2h
```

### Release a device
```bash
xts allocator release user@example.com 1
```

### List devices by state
```bash
xts allocator list_free
xts allocator list_allocated
```

## Control URIs

Each device has control URIs configured for:

### Pi5 (ID: 1)
```json
{
  "ping": "ping -c 4 pi5.local",
  "ssh": "ssh pi@pi5.local"
}
```

### Spark (ID: 2)
```json
{
  "ping": "ping -c 4 spark.local",
  "ssh": "ssh user@spark.local"
}
```

### Mac (ID: 3)
```json
{
  "ping": "ping -c 4 mac.local",
  "ssh": "ssh user@mac.local"
}
```

### HPZ4 (ID: 4)
```json
{
  "ping": "ping -c 4 hpz4.local",
  "localhost": "localhost",
  "ssh": "ssh gweatherup@hpz4.local"
}
```

## Re-populate Database

To reset the test devices or add them again:

```bash
cd /home/gweatherup/git/fast/sky/xts_allocator_server
source venv/bin/activate
PYTHONPATH=. python test/populate_test_devices.py
```

This script will:
- Create the TestRack if it doesn't exist
- Add all 4 test devices
- Update existing devices if they already exist

## Tags

Devices are tagged for easy searching:

- **pi5.local**: `arm`, `linux`, `sbc`, `development`
- **spark.local**: `x86`, `linux`, `development`
- **mac.local**: `mac`, `macos`, `development`
- **hpz4.local**: `x86`, `linux`, `workstation`, `local`

Search by tags:
```bash
xts allocator search_by_tags arm
xts allocator search_by_tags linux
xts allocator search_by_tags local
```

## Example Workflow

```bash
# 1. Check what's available
xts allocator list_free

# 2. Test connectivity to pi5
cd /home/gweatherup/git/fast/sky/xts_allocator_server
source venv/bin/activate
PYTHONPATH=. python test/test_device_connectivity.py 1

# 3. Allocate it
xts allocator alloc_by_id myemail@example.com 1 2h

# 4. Use it (SSH, ping, etc.)
ssh pi@pi5.local

# 5. Release when done
xts allocator release myemail@example.com 1
```
