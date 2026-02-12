# TODO - Phased Delivery Plan

_Last reviewed: 2026-02-11_

# TODO - Phased Delivery Plan

_Last reviewed: 2026-02-11_

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

- [ ] **Remove `datetime.utcnow()` usage**
  - Migrate to timezone-aware UTC timestamps to reduce warnings and future break risk

## Code Review: Outstanding Issues

### Critical: 9 Test Failures (Audit Log Routes)

**Root cause:** The 3 route handlers in `audit_log_routes.py` are defined as sync functions, but the `@require_auth` decorator uses `await` to call them.

**Error:** `TypeError: object JSONResponse can't be used in 'await' expression`

**Affected handlers:**
- [ ] `audit_log_routes.py:17` — `def get_audit_logs` needs `async def`
- [ ] `audit_log_routes.py:138` — `def get_audit_summary` needs `async def`
- [ ] `audit_log_routes.py:236` — `def get_event_types` needs `async def`

### Security Issues (High Priority)

- [ ] **`/allocate_permanent` has no auth or input validation** — `allocation_routes.py:759`
  - No `@require_auth`, no `validate_user_data`, no `validate_integer` on `slot_id`
  - Anyone can permanently allocate devices

- [ ] **`/report_status` has no auth** — `allocation_routes.py:834`
  - Anyone can set device connectivity status, software version, and system_metrics

- [ ] **`/allocation_history` has no auth** — `allocation_routes.py:689`
  - Allocation history (including user emails) is publicly visible

- [ ] **`GET /test_executions` has no auth** — `test_routes.py:259`
  - Test execution data is publicly accessible

- [ ] **Hardcoded plaintext passwords** — `auth.py:238-254`
  - `DEMO_USERS` dict with `"password": "admin123"` etc.
  - Even for dev, this is a risk if deployed

- [ ] **`/delete_slot` only requires `ROLE_ENGINEER`** — `device_routes.py:272`
  - Destructive operation should arguably require `ROLE_ADMIN`

### Code Quality Issues

- [ ] **`build_target_id()` duplicated in 5 route files**
  - Identical function in: `allocation_routes.py:39`, `device_routes.py:11`, `rack_routes.py:10`, `export_routes.py:10`, `usage_routes.py:12`
  - Should be extracted to a shared module (e.g., `utils.py` or `helpers.py`)

- [ ] **Orphaned `allocator.xts` file**
  - `allocator.xts` is a subset copy of `xts_allocator.xts`
  - Missing: `register`, `whoami`, `tutorial`, `borrow`/`return` commands, `brief`/`alias_name` fields
  - The served file is `config/xts_allocator.xts`
  - This orphan will drift out of sync — should be removed or documented

- [ ] **State machine description missing `TESTING`** — `state_machine.py:141-151`
  - `get_state_description()` has no entry for `DeviceState.TESTING`
  - Returns "Unknown state" for testing devices

### Deprecation Warnings (2,381 in test run)

- [ ] **`datetime.utcnow()` — 66 occurrences across 17 files**
  - Already in your TODO
  - Python 3.12+ deprecation warning, will break in a future version
  - Should use `datetime.now(timezone.utc)`

- [ ] **`declarative_base()` from legacy import** — `models.py:2`
  - `from sqlalchemy.ext.declarative import declarative_base` is deprecated since SQLAlchemy 2.0
  - Should be `from sqlalchemy.orm import declarative_base`

### Minor / Informational

- [ ] **`GET /list_slots` has no rate limiting** — `device_routes.py:48`
  - The POST version at line 84 does have it

- [ ] **Synchronous DB sessions in an async framework**
  - All routes use `SessionLocal()` (synchronous SQLAlchemy)
  - Blocks Sanic's event loop during DB operations
  - For production scale this would need async sessions

### Summary

| Category | Count | Severity |
|----------|-------|----------|
| Failing tests | 9 | **Critical** (easy fix — add `async`) |
| Unprotected endpoints | 4 | **High** |
| Code duplication | 2 | Medium |
| Deprecation warnings | 2 | Medium (will break eventually) |
| Minor issues | 3 | Low |

**Highest-impact quick win:** Fix the 3 `def` → `async def` in `audit_log_routes.py` to get all 9 tests passing.

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
  - End-to-end workflow tests (allocate→test→deallocate)
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
