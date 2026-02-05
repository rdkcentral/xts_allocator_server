# TODO - Phased Delivery Plan

## Phase 1: Core MVP - Command Line Ready (PRIORITY)

**Goal: Get operational ASAP with full CLI functionality**

- [x] **Add rack/equipment search and listing endpoints**
  - `/list_racks` - all racks with device counts ✓
  - `/rack/{id}/devices` - all devices in rack with status ✓
  - `/devices/search` - filter by: rack, platform, tags, state, has_equipment_type ✓
  - Update `/list_slots` to include rack info and external equipment ✓

- [x] **Implement proper state machine (5+ states)**
  - Expand Device state from free/allocated to: free, allocated, busy, resetting, maintenance, offline ✓
  - Add state transition validation ✓
  - Track state_changed_at timestamp ✓

- [x] **Implement duration-based allocation with expiry**
  - Add duration to allocation request (minutes/hours), calculate expiry ✓
  - Create Sanic background task to check expired allocations every N minutes ✓
  - Auto-deallocate and trigger state change to 'resetting' ✓

- [x] **Create .xts command definition file and serve it**
  - Build `xts_allocator.xts` file with YAML command definitions for XTS tool integration ✓
  - Add server endpoint to serve the .xts file (e.g., `/xts_allocator.xts`) ✓
  - Users can run: `xts alias http://<server>/xts_allocator.xts` to access commands remotely ✓
  - **XTS orchestration commands** (E2E testing workflow):
    - `xts allocate` - allocate device, receive config, save locally for raft ✓
    - `xts list` - list available test suites/devices ✓
    - `xts deallocate` - cleanup after tests complete ✓
  - Commands use curl to interact with REST API endpoints ✓
  - Include passthrough params for dynamic arguments (email, duration, filters) ✓
  - Allows central management and evolution of commands over time ✓
  - **Goal**: Single unified tool (XTS) for engineers to control entire test lifecycle ✓

- [x] **Design and implement allocator-driven configuration for python_raft**
  - **Integration architecture**: XTS orchestrates allocator server + python_raft ✓
    - XTS calls allocator server → receives config → saves locally → invokes raft ✓
    - XTS is the unified interface for engineers to run entire E2E test workflow ✓
  - **Server endpoints:** ✓
    - `/export/raft_config` - return allocator-optimized YAML config (new format) ✓
    - `/export/python_raft_config` - python_raft-compatible manual format (existing rack_config + device_config schema) ✓
    - Config includes allocation_id for reference ✓
  - **New allocator-driven config format** (optimized for XTS allocator integration): ✓
    - Include server communication metadata (allocator_url, allocation_id) ✓
    - Unified config structure combining device + rack info in single file ✓
    - Support dynamic/allocated devices vs static rack definitions ✓
    - Store allocation context (duration, expiry, owner_email) for reference ✓
  - **Manual config format** (python_raft-compatible): ✓
    - Follows existing rack_config.yml + device_config.yml structure ✓
    - Used by python_raft for manually-defined test environments ✓
    - Allocator generates this format from current device allocation ✓
    - Maintains compatibility with existing python_raft workflows ✓
  - **Config storage and usage:** ✓
    - XTS saves config locally when received from allocator ✓
    - XTS passes config path to raft when invoking tests ✓
    - Raft loads config for device connection details ✓
  - **Benefits of allocator-driven format:** ✓
    - Not constrained by manual schema limitations ✓
    - Optimized for allocation workflow (XTS → allocator → raft) ✓
    - Can evolve independently while maintaining backward compatibility ✓
    - Simplifies E2E testing: engineers use XTS commands, everything else is automated ✓

- [x] **Implement AllocationHistory audit trail**
  - Populate AllocationHistory on allocate/deallocate ✓
  - Track: user_email, device_id, start_time, end_time, duration_requested, software_version, state_before/after ✓
  - Add `GET /allocation_history` endpoint with filters ✓

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

---

## Phase 2: Enhanced Features & UI

**Goal: Add web interface and advanced capabilities**

- [ ] **Build Flutter web monitoring dashboard**
  - Web interface for device allocation and management
  - Features: allocate/deallocate devices, view device status, manage system
  - Real-time device state visualization
  - User-friendly interface for non-CLI users
  - Consider: device grid view, search/filter, allocation history view

- [ ] **Support permanent allocations and device status tracking**
  - Add allocation_type field: "temporary" (with expiry) vs "permanent" (no expiry)
  - Endpoint: `/allocate_permanent` - assign device to user indefinitely (requires admin/special permission)
  - Permanent allocations: no expiry, owner retains device until explicit deallocation
  - **Use case: Engineer desk boxes** - permanently allocated devices on engineer desks for manual testing/development
  - **Live device status tracking** (Phase 2/3 - not essential for MVP):
    - XTS reporting (when running): `/report_status` endpoint - XTS reports status during test execution
    - Server-side polling: background task to check device health directly
      - Critical for desk boxes where engineers may use device manually without XTS
      - Use control_uris from device model to reach device (SSH, HTTP, SNMP, etc.)
      - Check reachability (ping/connection test), fetch software version, system metrics
      - Update device status automatically without requiring XTS
    - Track last_seen timestamp, connectivity status, software version, system metrics
    - Store device uptime, reboot history, error conditions
  - Usage statistics:
    - Track test execution count (when XTS is used), total test time, idle time percentage
    - Test suite breakdown: which tests ran, frequency, success rates
    - Generate usage reports: daily/weekly/monthly activity summaries
    - API endpoint: `/device/{id}/usage_stats` - retrieve historical usage data
  - Note: Server allocation is ideal but not mandatory - devices can exist without allocation

- [ ] **Implement federated multi-server architecture**
  - Support multiple XTS allocator servers (per office/floor/group/cluster)
  - Master server registry: tracks all slave servers globally (URL, location, status, device count)
  - Slave server registration: POST to master on startup with server metadata
  - Health monitoring: periodic heartbeat from slaves, mark servers offline/online
  - Cross-server device discovery: master aggregates device listings from all active slaves
  - Resilience: slaves operate independently, master handles offline/unreachable servers gracefully
  - API endpoints: `/servers` (list all), `/servers/{id}/devices` (proxy to slave), `/register` (slave registration)

---

## Phase 3: Advanced Test Integration

**Goal: Deep integration with XTS and python_raft**

- [ ] **Implement XTS test execution tracking and lifecycle management (server callbacks)**
  - Add device state: "testing" (distinct from "allocated" - indicates active test execution)
  - Endpoint: `/start_test` - XTS/raft reports test start with expected_duration, test_name, test_suite
  - Endpoint: `/test_heartbeat` - periodic heartbeat during test execution
  - Endpoint: `/end_test` - reports test completion with status (success/failure/error), exit_code, logs_url
  - Allocation validation: check allocation still valid before starting tests
  - Server metadata in allocation response: include server_url for callbacks
  - **Flexible expiry during testing**:
    - Pause/disable expiry timer when device enters "testing" state
    - OR auto-extend allocation based on test's expected_duration
    - Never interrupt active test execution due to allocation expiry
    - Resume normal expiry after test completes and device returns to "allocated"
  - **Timeslot management strategy**:
    - Use test's `expected_duration` to calculate test_expiry (separate from allocation_expiry)
    - Set maximum test duration cap (e.g., 4 hours) as safety net for hung tests
    - Heartbeat timeout: if no heartbeat for N minutes during "testing", assume failure and reset
    - Allocation_expiry behavior: freeze during testing, resume countdown after test ends
    - Optional: Add "soft warning" period - notify user X minutes before hard limit
    - Optional: Queue system - allow reservation of future timeslots for predictable scheduling
    - Track "idle time" vs "test time" separately in allocation history for metrics
  - Store test execution metadata: link test runs to allocation history
  - **Coordinate with xts_core and python_raft**: Add callback support for status reporting

---

## External Dependencies (Coordinate with other teams)

**Note:** We control all repos - can raise tickets and branch using git flow for coordinated development across
xts_allocator_server, xts_core, and python_raft

### XTS Core Team

- [ ] Implement allocator commands in xts_core
  - Parse and execute .xts file from allocator server
  - Handle config download and local storage
  - Orchestrate allocation → raft invocation workflow
  - Support passthrough parameters for dynamic test arguments
  - **Ticket/Branch**: Can work in parallel with allocator server development

### Python RAFT Team

- [ ] Add dual-mode config support in python_raft
  - Standard mode: existing rack_config.yml + device_config.yml (manual/static setups)
  - Allocator mode: config from XTS allocator server (dynamic/allocated devices)
  - Auto-detect mode based on config source or explicit flag
  - Parse device connection details from new config format
  - **Ticket/Branch**: Can work in parallel with allocator server development
  - Health monitoring: periodic heartbeat from slaves, mark servers offline/online
  - Cross-server device discovery: master aggregates device listings from all active slaves
  - Resilience: slaves operate independently, master handles offline/unreachable servers gracefully
  - API endpoints: `/servers` (list all), `/servers/{id}/devices` (proxy to slave), `/register` (slave registration)
