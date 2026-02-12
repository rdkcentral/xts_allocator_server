# TODO - Phased Delivery Plan

_Last reviewed: 2026-02-12_

## Current Focus (Feb 2026)

**Purpose: keep the short list of items that still block daily engineering workflows**

- [ ] **Add pagination/sorting for large fleets (100+ boxes)**
  - Add `limit`, `offset`, and stable sort options to `/list_slots` and `/devices/search`
  - Ensure CLI defaults remain concise while still allowing full exports

- [ ] **Add compact box status endpoint for RAFT/XTS polling**
  - Include state, active test name/id, elapsed duration, and heartbeat age
  - Keep payload lightweight for frequent polling from automation

- [ ] **Finish XTS core integration items (cross-repo)**
  - Complete allocator command execution path in xts_core
  - Support internal shallow clone for remote-repo analysis

- [ ] **Align terminology and schema expectations**
  - Treat rack slot as the platform target consistently across API/docs/export formats
  - Keep aliases (`slot_contents`/`external_equipment`, `labels`/`tags`) documented

- [x] **Remove `datetime.utcnow()` usage**
  - Migrated to `datetime.now(timezone.utc)` across all `.py` files

## Code Review: Resolved Issues

### Fixed: 9 Test Failures (Audit Log Routes)

- [x] `audit_log_routes.py` — 3 handlers changed from `def` to `async def`

### Fixed: Code Quality Issues

- [x] **`build_target_id()` and `normalize_tags()` extracted to `routes/utils.py`**
  - Removed duplication from 5 route files

- [x] **`allocator.xts` is now the canonical XTS config file**
  - Served from root as `/allocator.xts` (avoids `xts` appearing twice in alias registration)
  - `config/xts_allocator.xts` is the old path, no longer served

- [x] **State machine description added for `TESTING` state** — `state_machine.py`

### Fixed: Deprecation Warnings

- [x] **`datetime.utcnow()`** — Migrated all 66 occurrences to `datetime.now(timezone.utc)`

- [x] **`declarative_base()` import** — `models.py` now uses `from sqlalchemy.orm import declarative_base`

### Fixed: Minor Issues

- [x] **`GET /list_slots` now has rate limiting** — `device_routes.py`

## Auth Model (Design Notes)

Authentication will be based on XTS user settings (email, etc.) transferred to the
server as first-stage auth. Users who don't provide their identity can't get an
allocation. Admin features (who can change what) will be configured on the server
based on user settings or email address. The current `@require_auth` decorator and
JWT flow serve as the mechanism; endpoints that currently lack `@require_auth` will
be protected once the XTS client integration is complete.

### Endpoints pending auth integration (by design, not a bug)

- `/allocate_permanent` — will require auth via XTS user settings
- `/report_status` — will require device identity
- `/allocation_history` — will require at least readonly auth
- `GET /test_executions` — will require at least readonly auth

### Other auth notes

- Hardcoded `DEMO_USERS` in `auth.py` — placeholder for dev/testing only
- `/delete_slot` requires `ROLE_ENGINEER` — review whether `ROLE_ADMIN` is more appropriate

---

## Phase 4: Flutter-based GUI (Cross-platform Client)

**Goal: Native mobile and desktop applications for device management**

- [ ] **Flutter project setup**
  - Create new Flutter project in `xts_allocator_flutter/` directory
  - Set up project structure with screens, models, services, widgets
  - Configure for multi-platform (Android, iOS, Windows, macOS, Linux, Web)
  - Add dependencies: http/dio, provider/riverpod, flutter_secure_storage

- [ ] **API client implementation**
  - Create REST API service layer for all allocator endpoints
  - Implement models for Device, AllocationHistory, TestExecution, Server
  - Add authentication/authorization with user email storage
  - Handle error responses and network failures gracefully

- [ ] **Core screens**
  - Device list screen: grid/list view with filters (state, platform, tags, search)
  - Device detail screen: full device info, allocation history, usage stats
  - Allocation screen: temporary/permanent allocation with duration picker
  - Test execution screen: start test, monitor progress, heartbeat display
  - Usage statistics screen: charts and metrics (per-device and system-wide)

- [ ] **Advanced features**
  - Real-time updates: polling or WebSocket for device state changes
  - Push notifications: allocation expiry warnings, test completion alerts
  - Offline support: cache device list, queue actions for later sync
  - Federation support: switch between multiple allocator servers
  - QR code scanner: quick device allocation by scanning rack labels

- [ ] **State management and UX**
  - Implement Provider/Riverpod for app-wide state
  - Add loading states, error handling, retry logic
  - Material Design for Android, Cupertino for iOS
  - Responsive layouts for tablet/desktop
  - Dark mode support

- [ ] **Testing and deployment**
  - Unit tests for API client and business logic
  - Widget tests for UI components
  - Integration tests for core workflows
  - Build release APK/IPA/executables
  - Publish to stores or distribute internally

---

## Phase 5: Security & Access Control (P0 - CRITICAL)

- [ ] **Database connection improvements**
  - Transaction isolation level configuration
  - Database backup strategy

---

## Phase 6: Observability & Production Readiness (P0)

- [ ] **Automated backup & disaster recovery**
  - Daily automated database backups
  - Backup retention policy (30 days)
  - Point-in-time recovery capability
  - Backup verification/restore testing
  - Configuration backup (environment vars, secrets)

- [ ] **Health monitoring enhancements**
  - Database connection health checks
  - Disk space monitoring
  - Memory/CPU usage metrics
  - Background task health status
  - Dependency health (federation slave servers)

---

## Phase 7: Real-Time Communication & Notifications (P1)

**Goal: Reduce polling, improve user experience**

- [ ] **WebSocket support for real-time updates**
  - `/ws/devices` endpoint for device state changes
  - Push device allocation/deallocation events
  - Push test execution status updates
  - Client subscription to specific devices or racks
  - Connection management and reconnection logic

- [ ] **Notification system**
  - Email notifications for allocation expiry warnings
  - Slack/Teams webhook integration
  - Configurable notification preferences per user
  - Notification templates (allocation, expiry, test completion)
  - Notification delivery tracking

- [ ] **Waiting queue & reservation system**
  - Queue for devices when all allocated
  - Automatic allocation when device becomes free
  - Priority queue for urgent tests
  - Estimated wait time calculation
  - Queue position notifications

---

## Phase 8: Advanced Features & Scale (P1-P2)

**Goal: Support complex workflows and larger deployments**

- [ ] **Advanced scheduling & reservations**
  - Future reservations: "allocate device at 3pm tomorrow"
  - Recurring allocations: "every Monday 9am for 2 hours"
  - Maintenance windows: block devices from allocation
  - Calendar view for device availability
  - Conflict resolution for overlapping requests

- [ ] **Multi-tenancy support**
  - Team/project isolation with separate device pools
  - Quota management: "Team A max 5 devices, Team B max 10"
  - Resource limits per user (max allocation duration, max concurrent)
  - Cost tracking per team/project
  - Admin dashboard for tenant management

- [ ] **Device health monitoring**
  - Device heartbeat from STBs themselves
  - Automated health checks (ping, HTTP, SSH)
  - Proactive failure detection
  - Auto-mark devices offline when unreachable
  - Health history tracking and alerting

- [ ] **Proper tag management**
  - Many-to-many relationship for device tags
  - Tag table with normalized storage
  - Exact tag matching in queries
  - Tag creation/deletion API
  - Tag usage statistics

- [ ] **Allocation transfer & delegation**
  - Transfer allocation to another user
  - Delegation: temporary access without changing owner
  - Approval workflow for transfers
  - Audit trail for ownership changes

---

## Phase 9: Test Coverage Improvements (Ongoing)

- [ ] **Integration test suite**
  - Re-enable 3 skipped federation httpx tests
  - Test with real httpx calls (not mocked)
  - Multi-server federation scenarios
  - End-to-end workflow tests (allocate->test->deallocate)
  - XTS client integration tests

- [ ] **Background task execution tests**
  - Test `check_expired_allocations()` in running async loop
  - Test background task error handling
  - Test background task restart on failure
  - Verify async task doesn't block main server

- [ ] **Database failure & resilience tests**
  - Connection pool exhaustion scenarios
  - SQLite locked/busy error handling
  - Disk full scenarios
  - Database connection loss and recovery
  - Transaction rollback behavior

- [ ] **Migration testing**
  - Alembic upgrade/downgrade test suite
  - Data preservation during schema changes
  - Migration idempotency verification
  - Rollback capability testing
  - Production migration dry-run support

- [ ] **Input validation & security tests**
  - Extremely long input strings (10MB+ fields)
  - SQL injection attempts (verify SQLAlchemy protection)
  - Malformed JSON edge cases
  - XSS attack vectors in web dashboard
  - API fuzzing with random inputs

- [ ] **Load & performance tests**
  - Load test: 100+ concurrent allocations
  - Stress test: find breaking point
  - Response time under load measurement
  - Memory leak detection (long-running tests)
  - Database query performance with large datasets (10k+ devices)

- [ ] **API contract tests**
  - Response schema validation for all endpoints
  - Field presence/absence verification
  - Type checking (string vs int vs null)
  - Breaking change detection
  - Backward compatibility testing

---

## Remaining Minor Issues

- [ ] **Synchronous DB sessions in an async framework**
  - All routes use `SessionLocal()` (synchronous SQLAlchemy)
  - Blocks Sanic's event loop during DB operations
  - For production scale this would need async sessions

---

## External Dependencies (Coordinate with other teams)

**Note:** We control all repos - can raise tickets and branch using git flow for coordinated development across
xts_allocator_server, xts_core, and python_raft

### Python RAFT Team

- [ ] Add dual-mode config support in python_raft
  - Standard mode: existing rack_config.yml + device_config.yml (manual/static setups)
  - Allocator mode: config from XTS allocator server (dynamic/allocated devices)
  - Auto-detect mode based on config source or explicit flag
  - Parse device connection details from new config format
  - **Ticket/Branch**: Can work in parallel with allocator server development
