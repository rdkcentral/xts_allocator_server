# TODO

## Outstanding Tasks

- [x] **Add rack/equipment search and listing endpoints**
  - `/list_racks` - all racks with device counts ✓
  - `/rack/{id}/devices` - all devices in rack with status ✓
  - `/devices/search` - filter by: rack, platform, tags, state, has_equipment_type ✓
  - Update `/list_slots` to include rack info and external equipment ✓

- [ ] **Implement proper state machine (5+ states)**
  - Expand Device state from free/allocated to: free, allocated, busy (test running), resetting, maintenance, offline
  - Add state transition validation
  - Track state_changed_at timestamp

- [ ] **Implement duration-based allocation with expiry**
  - Add duration to allocation request (minutes/hours), calculate expiry
  - Create Sanic background task to check expired allocations every N minutes
  - Auto-deallocate and trigger state change to 'resetting'

- [ ] **Implement AllocationHistory audit trail**
  - Populate AllocationHistory on allocate/deallocate
  - Track: user_email, device_id, start_time, end_time, duration_requested, software_version, state_before/after
  - Add `GET /allocation_history` endpoint with filters

- [ ] **Build CLI tool for MVP operations**
  - `xts allocate --platform X --duration 2h`
  - `xts deallocate --id N`
  - `xts list --rack R --state free`
  - `xts racks`
  - `xts device add`
  - `xts device info --id N`

- [ ] **Add structured logging framework**
  - Python logging module with INFO/ERROR levels
  - Log: allocation/deallocation, state transitions, errors, API requests
  - File handler with rotation (RotatingFileHandler), console handler for dev

- [ ] **Create health check and metrics endpoints**
  - `/health` - status, database connectivity, timestamp
  - `/metrics` - total_devices, devices_by_state, devices_by_rack, allocations_today, avg_allocation_duration

- [ ] **Build comprehensive test suite**
  - Allocate by ID/platform/tags
  - Deallocate (success/403/404)
  - Duration expiry
  - Rack listings, equipment search, state transitions
  - CRUD operations, concurrent allocation attempts
  - Invalid inputs, edge cases
