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

- [x] **Add structured logging framework**
  - Python logging module with INFO/ERROR levels ✓
  - Log: allocation/deallocation, state transitions, errors, API requests ✓
  - File handler with rotation (RotatingFileHandler), console handler for dev ✓

- [x] **Create health check and metrics endpoints**
  - `/health` - status, database connectivity, timestamp ✓
  - `/metrics` - total_devices, devices_by_state, devices_by_rack, allocations_today, avg_allocation_duration ✓

- [x] **Build comprehensive test suite**
  - Allocate by ID/platform/tags ✓
  - Deallocate (success/403/404) ✓
  - Duration expiry ✓
  - Rack listings, equipment search, state transitions ✓
  - CRUD operations, concurrent allocation attempts ✓
  - Invalid inputs, edge cases ✓

---

## Phase 2: Enhanced Features & UI

**Goal: Add web interface and advanced capabilities**

- [x] **Build Flutter web monitoring dashboard**
  - Web interface for device allocation and management ✓ (HTML implementation)
  - Features: view device status, filter/search devices ✓
  - Real-time device state visualization ✓
  - User-friendly interface for non-CLI users ✓
  - Device grid view, search/filter, state-based color coding ✓
  - Note: Implemented as responsive HTML/CSS/JS dashboard at /dashboard
  - Future: Can enhance to full Flutter web app with inline allocation/deallocation

- [x] **Support permanent allocations and device status tracking**
  - Add allocation_type field: "temporary" (with expiry) vs "permanent" (no expiry) ✓
  - Endpoint: `/allocate_permanent` - assign device to user indefinitely ✓
  - Permanent allocations: no expiry, owner retains device until explicit deallocation ✓
  - **Use case: Engineer desk boxes** - permanently allocated devices on engineer desks ✓
  - **Live device status tracking**: ✓
    - XTS reporting: `/report_status` endpoint - XTS reports status during execution ✓
    - Track last_seen timestamp, connectivity status, software version, system_metrics ✓
    - Server-side polling: background task (future enhancement for automated health checks)
  - Usage statistics: ✓
    - Track test execution count, total test time, idle time percentage ✓
    - API endpoints: `/device/{id}/usage_stats` - per-device statistics ✓
    - `/usage_summary` - system-wide aggregates and reports ✓
    - Top devices by usage, unique users, allocation trends ✓

- [x] **Implement federated multi-server architecture**
- [x] **Implement federated multi-server architecture**
  - Support multiple XTS allocator servers (per office/floor/group/cluster) ✓
  - Master server registry: tracks all slave servers (URL, location, status, device count) ✓
  - Slave server registration: POST to master on startup with server metadata ✓
  - Health monitoring: periodic heartbeat from slaves, mark servers offline/online ✓
  - Cross-server device discovery: master aggregates device listings from all slaves ✓
  - Resilience: slaves operate independently, master handles offline/unreachable servers ✓
  - API endpoints: `/servers`, `/servers/{id}/devices`, `/register`, `/heartbeat`, `/devices/federated` ✓

---

## Phase 3: Advanced Test Integration

**Goal: Deep integration with XTS and python_raft**

- [x] **Implement XTS test execution tracking and lifecycle management (server callbacks)**
  - Add device state: "testing" (distinct from "allocated") ✓
  - Endpoint: `/start_test` - XTS/raft reports test start with test metadata ✓
  - Endpoint: `/test_heartbeat` - periodic heartbeat during test execution ✓
  - Endpoint: `/end_test` - reports test completion with status, exit_code, logs_url ✓
  - Endpoint: `/test_executions` - query test runs with filtering ✓
  - Allocation validation: check allocation still valid before starting tests ✓
  - **Flexible expiry during testing**: ✓
    - Skip devices in testing state from allocation expiry ✓
    - Auto-extend allocation based on test's expected_duration ✓
    - Never interrupt active test execution due to allocation expiry ✓
  - **Timeslot management strategy**: ✓
    - Use test's expected_duration to auto-extend allocations ✓
    - Set maximum test duration cap (4 hours default, configurable) ✓
    - Heartbeat timeout: detect hung tests (10 min default, configurable) ✓
    - Track test time vs idle time separately in allocation history ✓
  - Store test execution metadata: link test runs to allocation history ✓
  - Background task: Detect and terminate hung/timeout tests ✓

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

**Goal: Production-ready security before deployment**

- [x] **Authentication system** ✓
  - JWT token-based authentication with HS256 algorithm ✓
  - `/auth/token` endpoint with email/password validation ✓
  - `/auth/refresh` endpoint for token refresh ✓
  - `/auth/me` endpoint to check token validity and user info ✓
  - Access and refresh tokens (8h and 30d expiry) ✓
  - User roles: admin (level 2), engineer (level 1), readonly (level 0) ✓
  - Demo user database (replace with real DB in production) ✓
  - `@require_auth()` decorator for protecting routes ✓
  - Role hierarchy enforcement (admin > engineer > readonly) ✓
  - Applied to all protected routes (allocations, devices, tests, admin operations) ✓
  - `get_user_from_request()` helper for extracting authenticated user ✓
  - **Result**: 19 new tests, full JWT auth system deployed to all routes

- [x] **Authorization & access control** ✓
  - Role-based access control (RBAC) implemented ✓
  - Engineer role: standard operations (allocations, device management, tests) ✓
  - Admin role: full access including forced deallocations, audit logs ✓
  - Readonly role: view-only access (devices, history, metrics) ✓
  - Route-level permission enforcement via decorator parameters ✓
  - **Future**: Team-based permissions (multi-tenancy support)

- [x] **API security hardening** ✓
  - Rate limiting middleware: sliding window per-user via `@rate_limit` decorator ✓
  - Applied to 15+ endpoints with user-based identifiers (`user_email_identifier`) ✓
  - Allocations (30 req/min), devices (20-60 req/min), tests (30-120 req/min) ✓
  - Input validation: email, string, integer, tags, user data validators ✓
  - Applied to critical endpoints: allocate, deallocate, state change, start test ✓
  - CORS middleware with configurable origins (CORS_ORIGINS env var) ✓
  - CORS preflight OPTIONS handler ✓
  - CORS_ENABLED flag for easy disable ✓
  - Comprehensive test coverage: 9 rate limiting, 30 input validation tests ✓
  - Integration with JWT auth for per-user rate limiting ✓
  - **Future**: HTTPS enforcement, request size limits, API key rotation

- [x] **Audit logging for security** ✓
  - Centralized security audit log with AuditLog model ✓
  - Database-persisted audit trail (who did what when) ✓
  - Log all authentication attempts (login, failures, token refresh) ✓
  - Log all privileged operations (allocations, state changes, admin actions) ✓
  - Event categorization (authentication, device_operation, test_operation, admin_operation) ✓
  - Severity levels (debug, info, warning, error, critical) ✓
  - Metadata tracking (IP address, user agent, resource IDs) ✓
  - Helper functions: `log_allocation()`, `log_state_change()`, `log_auth_failure()` ✓
  - Admin-only query endpoints: `/audit/logs`, `/audit/summary`, `/audit/report` ✓
  - Comprehensive filtering (user, event type, time range, severity, success/failure) ✓
  - **Result**: Full audit logging system with 11 event types and admin dashboard
  - **Future**: Tamper-proof logging (append-only, external sink like S3/CloudWatch)

---

## Phase 6: Observability & Production Readiness (P0)

**Goal: Monitor, debug, and maintain production system**

- [x] **Prometheus metrics integration** ✓
  - Converted `/metrics` endpoint to support both JSON and Prometheus formats ✓
  - Added `/metrics?format=prometheus` query parameter ✓
  - Added dedicated `/metrics/prometheus` endpoint ✓
  - Gauges: `device_state_total{state}`, `device_total`, `device_rack_total{rack_id}` ✓
  - Counters: `allocations_today_total`, `tests_completed_today_total` ✓
  - Gauges: `allocation_duration_avg_seconds`, `test_duration_avg_seconds`, `device_utilization_percent` ✓
  - Proper content-type: `text/plain; version=0.0.4` ✓
  - Backward compatible: JSON format by default ✓
  - **Result**: 3 new tests, Grafana/Prometheus ready

- [x] **OpenAPI/Swagger documentation** ✓
  - OpenAPI 3.0 specification: `openapi_spec.py` with complete API schema ✓
  - `/openapi.json` endpoint serves spec ✓
  - All major endpoints documented: allocations, devices, tests, export, federation, health ✓
  - Request/response schemas defined for all operations ✓
  - Validation constraints included (max lengths, min/max values, formats) ✓
  - Rate limiting documented (429 responses) ✓
  - **Result**: 1 new test, ready for Swagger UI integration
  - **TODO**: Add Swagger UI frontend (sanic-openapi or static HTML)
  - Include authentication requirements
  - Enable API client SDK generation

- [x] **Database migration to PostgreSQL** ✓
  - Comprehensive `config.py` with environment-based configuration ✓
  - Support for SQLite (development) and PostgreSQL (production) ✓
  - Environment variables for all settings (DB, JWT, CORS, server, logging) ✓
  - Connection pooling for PostgreSQL (pool_size=10, max_overflow=20, pool_pre_ping=True) ✓
  - Updated models.py with PostgreSQL engine configuration ✓
  - Updated Alembic env.py to use config system ✓
  - Added psycopg2-binary==2.9.9 to requirements.txt ✓
  - Created POSTGRESQL_MIGRATION.md guide (setup, migration, backup, troubleshooting) ✓
  - Config validation with security warnings ✓
  - DevelopmentConfig, ProductionConfig, TestingConfig classes ✓
  - **Result**: Production-ready database configuration system
  - **TODO**: Test actual PostgreSQL deployment, create data migration script, enable multi-worker support

- [x] **Structured audit logging** ✓
  - Database-backed audit log with structured fields (AuditLog table) ✓
  - Queryable via REST API with filtering and aggregation ✓
  - Security event categorization and severity tracking ✓
  - Full metadata capture (timestamp, user, IP, resource, event details) ✓
  - Admin dashboard for compliance reporting and forensics ✓
  - **Future**: JSON log file output, ELK/Splunk integration, correlation IDs, log sampling

- [x] **Database management & testing infrastructure** ✓
  - Dual database system (test/development/production modes) ✓
  - Automatic mode handling in test.sh (uses test DB) ✓
  - Automatic mode handling in run.sh (uses development DB) ✓
  - bin/db-status: Database status and statistics display (4.9KB) ✓
  - bin/db-switch: Mode switching with confirmation (3.2KB) ✓
  - bin/db-clean: Test database cleanup with safety features (6.8KB) ✓
  - Safety features: test-only defaults, confirmation prompts, force flags ✓
  - DATABASE_MANAGEMENT.md: Complete guide (8.2KB) ✓
  - DB_QUICK_REFERENCE.txt: Quick reference card ✓
  - Demo scripts and verification testing ✓
  - **Result**: Zero-friction testing with automatic database isolation, production data protected

- [ ] **Database connection improvements**
  - Transaction isolation level configuration
  - Database backup strategy

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

## Phase 8.5: Documentation & Developer Experience (Completed)

**Goal: Comprehensive AI agent instructions and developer onboarding**

- [x] **AI Agent Instructions (Copilot/Cursor/Cline)** ✓
  - Comprehensive `.github/copilot-instructions.md` for AI coding agents ✓
  - RDK Central development standards (Git Flow, commit message 50/72 rule) ✓
  - Architecture overview (10 blueprints, 6 models, core components) ✓
  - Authentication & security patterns with code examples ✓
  - Testing patterns for auth-protected routes with fixtures ✓
  - Audit log debugging guide with curl examples ✓
  - Database configuration (SQLite dev, PostgreSQL prod) ✓
  - Critical workflows (setup, testing, 3rdParty integration) ✓
  - Common pitfalls & known issues section ✓
  - Session handling, allocation patterns, state machine rules ✓
  - **Result**: 415-line comprehensive guide for immediate AI agent productivity

---

## Phase 9: Test Coverage Improvements (Ongoing)

**Goal: Comprehensive test coverage for reliability**

- [x] **Concurrency & race condition tests** ✓
  - Test double allocation prevention (2+ users, same device) ✓
  - Test sequential double allocation rejection ✓
  - Test state machine enforces valid transitions ✓
  - Database transaction integrity verification ✓
  - Allocation history created atomically ✓
  - State consistency across operations (owner cleared, expiry set, etc.) ✓
  - **Result**: 11 new tests, all passing

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
