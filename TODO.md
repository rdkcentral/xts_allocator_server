# TODO - XTS Allocator Server

_Last reviewed: 2026-02-12_

## Current Focus

**Items that block daily engineering workflows or affect code correctness.**

- [ ] **Add pagination/sorting for large fleets (100+ boxes)**
  - Add `limit`, `offset`, and stable sort options to `/list_slots` and `/devices/search`
  - Ensure CLI defaults remain concise while still allowing full exports

- [ ] **Add compact box status endpoint for RAFT/XTS polling**
  - Include state, active test name/id, elapsed duration, and heartbeat age
  - Keep payload lightweight for frequent polling from automation

- [ ] **Finish XTS core integration items (cross-repo)**
  - Complete allocator command execution path in xts_core
  - Support internal shallow clone for remote-repo analysis

- [ ] **Add input validation to remaining route files**
  - `device_routes.py` — add_slot, update_slot, delete_slot (no validation)
  - `rack_routes.py` — all endpoints (no validation)
  - `export_routes.py` — all endpoints (no validation)
  - `usage_routes.py` — all endpoints (no validation)
  - `federation_routes.py` — all endpoints (no validation)
  - `audit_log_routes.py` — all endpoints (no validation)
  - Already validated: allocation_routes, test_routes, auth_routes

- [ ] **Update OpenAPI spec to match actual routes**
  - `openapi_spec.py` only documents 13 of 42 endpoints
  - Missing: all auth, audit, federation, usage, rack detail, export, and several allocation/device/test routes
  - Spec should match reality for client generation and docs

---

## Auth Model

Authentication is based on XTS user settings (email, etc.) transferred to the
server as first-stage auth. Users who don't provide their identity can't get an
allocation. Admin features (who can change what) will be configured on the server
based on user settings or email address. The `@require_auth` decorator and JWT
flow serve as the mechanism; endpoints that currently lack `@require_auth` will be
protected once the XTS client integration is complete.

### Endpoints pending auth integration (by design, not a bug)

- `/allocate_permanent` — will require auth via XTS user settings
- `/report_status` — will require device identity
- `/allocation_history` — will require at least readonly auth
- `GET /test_executions` — will require at least readonly auth

### Other auth notes

- `DEMO_USERS` in `auth.py` — placeholder for dev/testing only
- `/delete_slot` requires `ROLE_ENGINEER` — review whether `ROLE_ADMIN` is more appropriate

---

## Code Quality

- [ ] **Bare `except:` in `format_allocator_output.py:51`** — should catch `ValueError`
- [ ] **Align terminology and schema aliases**
  - `slot_contents` / `external_equipment`, `labels` / `tags` — keep documented or consolidate
- [ ] **Synchronous DB sessions in async framework**
  - All routes use `SessionLocal()` (synchronous SQLAlchemy)
  - Blocks Sanic's event loop during DB ops — needs async sessions for production scale

---

## Test Coverage

**189 passed, 3 skipped, 0 failed**

- [ ] **3 skipped federation tests** (`tests/test_federation.py`)
  - `test_get_server_devices_success` (line 176)
  - `test_get_server_devices_unreachable` (line 214)
  - `test_list_federated_devices` (line 242)
  - All skipped: "Complex httpx mocking — requires integration test with real server"

- [ ] **Background task tests**
  - `check_expired_allocations()` runs in async loop — not tested directly
  - Background task error handling and restart not covered

- [ ] **End-to-end workflow tests**
  - Full allocate -> test -> heartbeat -> end_test -> deallocate flow
  - Multi-server federation scenarios

---

## Future Phases

### Phase 4: Flutter GUI (Cross-platform Client)

- [ ] Flutter project setup (multi-platform: Android, iOS, desktop, web)
- [ ] REST API client layer for all allocator endpoints
- [ ] Core screens: device list, device detail, allocation, test execution, usage stats
- [ ] Real-time updates, push notifications, offline support
- [ ] Federation support: switch between multiple allocator servers

### Phase 5: Security & Access Control

- [ ] Transaction isolation level configuration
- [ ] Database backup strategy

### Phase 6: Observability & Production Readiness

- [ ] Automated backup & disaster recovery (daily, 30-day retention)
- [ ] Health monitoring: DB connections, disk, memory/CPU, background tasks

### Phase 7: Real-Time Communication

- [ ] WebSocket support (`/ws/devices`) for device state changes
- [ ] Notification system (email, Slack/Teams webhooks)
- [ ] Waiting queue & reservation system

### Phase 8: Advanced Features & Scale

- [ ] Advanced scheduling & reservations (future bookings, recurring, maintenance windows)
- [ ] Multi-tenancy (team isolation, quotas, resource limits)
- [ ] Device health monitoring (heartbeat, auto-offline, health history)
- [ ] Proper tag management (many-to-many, tag table, exact matching)
- [ ] Allocation transfer & delegation

### Phase 9: Test Coverage Improvements

- [ ] Database failure & resilience tests
- [ ] Migration testing (Alembic upgrade/downgrade)
- [ ] Input validation & security tests (SQL injection, XSS, fuzzing)
- [ ] Load & performance tests (100+ concurrent, memory leaks)
- [ ] API contract tests (schema validation, breaking change detection)

---

## External Dependencies

**We control all repos** — can raise tickets and branch using git flow across
xts_allocator_server, xts_core, and python_raft.

- [ ] **python_raft**: Add dual-mode config support
  - Standard mode: existing rack_config.yml + device_config.yml
  - Allocator mode: config from XTS allocator server
  - Auto-detect or explicit flag
