# XTS Allocator Server - TODO List

## 🚨 Critical (Fix Before Commit)

### ~~1. Fix critical allocation bug (slot undefined)~~
**Priority:** URGENT  
**Status:** ✅ Completed (2026-02-04)  
**Description:** ~~In `allocation_routes.py` line 41, the code references `slot` variable that is undefined when allocating by ID.~~

**Fixed:** Moved slot allocation and state update inside both if/else branches. Each path now properly:
- Queries for the slot
- Validates availability
- Updates state and owner
- Commits transaction
- Returns response

Also added proper error handling to `deallocate_slot` with try/except/finally pattern.

---

## 🔧 Phase 1: Database Foundation (Current Focus)

### 2. Create Rack model and rack management
**Status:** Not Started  
**Dependencies:** Setup Alembic (completed)

**Tasks:**
- [ ] Add Rack model (name, location, building, description)
- [ ] Update Device with rack_id foreign key
- [ ] Create migration for Rack table
- [ ] Add endpoints: `/list_racks`, `/rack/{id}/devices`
- [ ] Add rack filtering to device queries

### 3. Redesign Device model for STB requirements
**Status:** Not Started  
**Dependencies:** Rack model, Alembic setup

**Required Fields:**
- Hardware: Make, Model, ModelAlias, Serial, Firmware, Manufacturer
- Network: HostMac, IPv4, IPv6
- Control URIs: VideoURI, RemoteURI, PowerURI, TraceURI, AudioURI (JSON field)
- Allocation: software_version, last_verified, allocation_expiry
- State: state, state_changed_at

**Tasks:**
- [ ] Define expanded Device model with all fields
- [ ] Use JSON column for control_uris flexibility
- [ ] Create Alembic migration
- [ ] Update routes to handle new fields
- [ ] Update populate_database.py with realistic test data

### 4. Add external equipment tracking per device
**Status:** Not Started  
**Dependencies:** Redesigned Device model

**Implementation:**
Add JSON field `external_equipment` to Device:
```json
[
  {"type": "camera", "name": "Axis Network Camera", "model": "...", "uri": "axis://...", "notes": "..."},
  {"type": "ir_blaster", "name": "IRNetBox Pro3", "connection": "..."},
  {"type": "audio_amp", "name": "...", "specs": "..."},
  {"type": "hdmi_hotplug", "name": "HDMI CEC Device"},
  {"type": "raspberry_pi", "name": "...", "purpose": "..."},
  {"type": "speaker", "name": "..."}
]
```

**Tasks:**
- [ ] Add external_equipment JSON field to Device model
- [ ] Create migration
- [ ] Add search by equipment type capability
- [ ] Update endpoints to include equipment info
- [ ] Add equipment filtering to device search

### 5. Add database constraints and indexes
**Status:** Not Started  
**Dependencies:** Rack model, redesigned Device model

**Tasks:**
- [ ] Add unique constraint on (rack_id, slot_name)
- [ ] Add indexes: state, rack_id, platform, owner_email
- [ ] Define cascade delete rules for rack→devices
- [ ] Create migration for constraints/indexes

---

## ⚙️ Phase 2: Core Features

### 6. Implement proper state machine (5+ states)
**Status:** Not Started  
**Dependencies:** Redesigned Device model

**States:**
- `free` - Available for allocation
- `allocated` - Assigned to user but not in use
- `busy` - Test running
- `resetting` - Reset/flush in progress
- `maintenance` - Requires manual intervention
- `offline` - Not available

**Tasks:**
- [ ] Define state enum/constants
- [ ] Add state transition validation logic
- [ ] Add state_changed_at timestamp tracking
- [ ] Update allocation/deallocation to use new states
- [ ] Document state transition rules

### 7. Implement duration-based allocation with expiry
**Status:** Not Started  
**Dependencies:** State machine

**Tasks:**
- [ ] Add duration parameter to allocate_slot request
- [ ] Calculate and store allocation_expiry timestamp
- [ ] Create Sanic background task to check expiries
- [ ] Auto-deallocate expired allocations
- [ ] Transition expired devices to 'resetting' state
- [ ] Add grace period handling

### 8. Add rack/equipment search and listing endpoints
**Status:** Not Started  
**Dependencies:** Rack model, external equipment

**New Endpoints:**
- [ ] `GET /list_racks` - All racks with device counts
- [ ] `GET /rack/{id}/devices` - All devices in specific rack
- [ ] `POST /devices/search` - Advanced search (rack, platform, tags, state, has_equipment_type)
- [ ] Update `/list_slots` to include rack info and equipment

### 9. Implement AllocationHistory audit trail
**Status:** Not Started  
**Dependencies:** State machine

**Tasks:**
- [ ] Populate AllocationHistory on allocate (user_email, device_id, start_time, duration_requested, software_version)
- [ ] Populate AllocationHistory on deallocate (end_time, state_before, state_after)
- [ ] Add `GET /allocation_history` endpoint with filters (device, user, date range)
- [ ] Add pagination to history endpoint

### 10. Add error handling and input validation
**Status:** Not Started  

**Tasks:**
- [ ] Fix deallocate_slot missing try/except/finally
- [ ] Standardize error responses: `{"error": str, "details": dict}`
- [ ] Standardize success responses: `{"message": str, "data": dict}`
- [ ] Add email format validation (regex)
- [ ] Add duration validation (min/max limits)
- [ ] Add state enum validation
- [ ] Add request body schema validation

---

## 🛠️ Phase 3: Tooling & Quality

### 11. Build CLI tool for MVP operations
**Status:** Not Started  
**Dependencies:** Core endpoints

**Commands:**
```bash
xts allocate --platform X --duration 2h
xts deallocate --id N
xts list --rack R --state free
xts racks
xts device add
xts device info --id N
```

**Tasks:**
- [ ] Create xts_cli.py with Click framework
- [ ] Implement all commands
- [ ] Add config file for server URL
- [ ] Add colored output for better UX
- [ ] Package as standalone executable

### 12. Add structured logging framework
**Status:** Not Started  

**Tasks:**
- [ ] Configure Python logging module (INFO/ERROR levels)
- [ ] Log allocation/deallocation events (who, device_id, duration)
- [ ] Log state transitions
- [ ] Log errors with stack traces
- [ ] Log API requests
- [ ] Add RotatingFileHandler for log rotation
- [ ] Add console handler for development

### 13. Create health check and metrics endpoints
**Status:** Not Started  

**Tasks:**
- [ ] Add `GET /health` endpoint (status, database connectivity, timestamp)
- [ ] Add `GET /metrics` endpoint:
  - total_devices
  - devices_by_state
  - devices_by_rack
  - allocations_today
  - avg_allocation_duration
- [ ] Add Prometheus-compatible metrics (optional)

### 14. Build comprehensive test suite
**Status:** Not Started  

**Test Coverage:**
- [ ] Allocation by ID tests
- [ ] Allocation by platform/tags tests
- [ ] Deallocation tests (success/403/404)
- [ ] Duration expiry tests
- [ ] Rack listing tests
- [ ] Equipment search tests
- [ ] State transition tests
- [ ] CRUD operation tests
- [ ] Concurrent allocation tests
- [ ] Invalid input tests
- [ ] Edge cases (null values, malformed JSON)

---

## ✅ Completed

### ~~Fix critical allocation bug (slot undefined)~~
**Status:** Completed ✓  
**Completed:** 2026-02-04

- ✓ Fixed slot undefined error in allocation_routes.py
- ✓ Moved allocation logic inside both if/else branches
- ✓ Added proper error handling to deallocate_slot
- ✓ Added try/except/finally pattern for consistency

### ~~Setup Alembic for database migrations~~
**Status:** Completed ✓  
**Completed:** 2026-02-04

- ✓ Added alembic==1.13.1 to requirements.txt
- ✓ Created venv with all dependencies
- ✓ Ready for `alembic init` when needed

---

## 📝 Notes

- CATS integration removed from scope (future consideration)
- Focus on local STB/rack management first
- Flutter UI is future work, CLI is MVP
- Keep schema flexible for adding fields later

---

## 🔖 Code TODOs

These items are tracked in code comments (TODO/FIXME):

- `config.py:4` - TODO: Implement environment variable support for DATABASE_URL and SECRET_KEY
- `models.py:15-33` - TODO: Device model needs major expansion for STB requirements
- `models.py:38-51` - TODO: AllocationHistory never populated, needs implementation

---

**Last Updated:** 2026-02-04
