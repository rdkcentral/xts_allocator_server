# XTS Allocator Server - AI Agent Instructions

## RDK Central Development Standards

This project follows RDK Central community-driven open-source development standards.

### Git Flow Branching Model

All development follows Git Flow ([reference](https://github.com/rdkcentral/ut-core/wiki/FAQ:-Git%E2%80%90Flow:-Developers-Branching-Model)):

1. **Feature Branches**: Create from `develop` branch with naming: `feature/<issue-number>_<brief-description>`
2. **Issue Tracking**: All branches MUST reference a GitHub issue ID for traceability
3. **Pull Requests**: Target `develop` branch, assigned to CODEOWNERS for review
4. **Testing**: Include comprehensive test results in PR before submission
5. **Merge**: After approval, merge using `git flow feature finish`

Example:
```bash
git flow init -d
git flow feature start 123_add-logging-enhancements
# Make changes, commit, test
git push origin feature/123_add-logging-enhancements
# Create PR to develop, wait for review
git flow feature finish 123_add-logging-enhancements
```

### Git Commit Message Standards (50/72 Rule)

All commits MUST follow the 50/72 rule ([reference](https://rdkcentral.github.io/rdk-halif-aidl/0.13.0/whitepapers/standardizing_git_commit_messages/)):

**Subject Line (≤50 characters):**
- Use imperative mood: "Add", "Fix", "Update", "Remove", "Refactor"
- No period at the end
- Capitalize first word
- Be concise and descriptive

**Body (≤72 characters per line):**
- Separate from subject with blank line
- Explain WHAT and WHY, not HOW
- Wrap text at 72 characters
- Use bullet points for multiple changes

**Example:**
```
Add duration-based allocation with expiry

Implement automatic deallocation after specified time period.
Background task checks every 60 seconds for expired allocations
and transitions devices to 'resetting' state.

- Add parse_duration() supporting 'm', 'h' formats
- Create asyncio background task for expiry checking
- Update allocation endpoints to accept duration parameter
```

**Common Verbs:**
- Add: New feature or file
- Fix: Bug fix
- Update: Modify existing functionality
- Remove: Delete code or files
- Refactor: Code restructure without behavior change
- Improve: Enhancement to existing feature
- Test: Add or update tests
- Clean: Code cleanup or formatting
- Merge: Merge branches
- Docs: Documentation only changes

### Issue Templates

GitHub issue templates exist and are enforced. Use correct type:

1. **FEATURE**: `Feature:<Short summary>` with Problem/Solution/Acceptance Criteria
2. **TASK**: `Task:<Short summary>` with clear goal statement
3. **BUG**: `Bug:<Short summary>` with Problem/Steps/Expected/Actual behavior

Reference: [Engineering Goals White Paper](https://rdkcentral.github.io/rdk-halif-aidl/0.13.0/whitepapers/engineering_goals/)

### Contribution Requirements

- Adherence to Git Flow
- Clear and concise commit messages (50/72 rule)
- Peer review approval from CODEOWNERS
- Thorough testing and validation with results
- GitHub Project assignment for tracking

## Project Overview

XTS Allocator Server manages device/STB allocation in shared testing environments. Prevents conflicts through state machine-controlled device lifecycle, supports test execution tracking, federated multi-server architecture, and provides XTS config export for test automation. Built with Sanic (async) + SQLAlchemy + SQLite.

## Architecture

### Core Components
- **`app.py`**: Sanic server, registers 9 blueprints, runs background expiry checker (`check_expired_allocations()` every 60s)
- **`models.py`**: 5 SQLAlchemy models: `Rack`, `Device`, `AllocationHistory`, `Server`, `TestExecution`
- **`state_machine.py`**: Enforces valid device state transitions (7 states: free→allocated→testing→resetting, etc.)
- **`logging_config.py`**: Structured logging with rotating file handler (10MB, 5 backups in `logs/`)
- **`routes/`**: Blueprint-based organization (9 blueprints):
  - `allocation_routes.py`: Allocate/deallocate with duration, state changes, permanent allocations
  - `device_routes.py`: Device CRUD (list/add/update/delete slots)
  - `rack_routes.py`: Rack management
  - `test_routes.py`: Test lifecycle (start/heartbeat/end), auto-extends allocations during tests
  - `export_routes.py`: YAML/Python config export for XTS integration (`/export/raft_config`)
  - `federation_routes.py`: Master/slave server registration, heartbeat, federated device queries
  - `health_routes.py`: Health checks, metrics
  - `usage_routes.py`: Usage stats per device/summary
  - `__init__.py`: Empty blueprint init

### Data Model Architecture
- **Rack → Device (1:many)**: Devices belong to physical racks (`rack_id` FK, unique `rack_id+slot_name`)
- **Device**: 30+ columns including:
  - Physical: `make`, `model`, `serial_number`, `host_mac`, `host_ipv4`, `control_uris` (JSON), `external_equipment` (JSON)
  - State: `state` (indexed), `state_changed_at`, 7 valid states enforced by state machine
  - Allocation: `owner_email` (indexed), `allocation_type` (temporary/permanent), `allocation_expiry` (DateTime for temporary)
  - Monitoring: `last_seen`, `connectivity_status`, `system_metrics` (JSON)
  - Tags: Comma-separated string (`"tag1,tag2"` - split/join in handlers)
- **AllocationHistory**: Full audit trail with user info, timing, test counts, idle time tracking
- **TestExecution**: Tracks active tests with heartbeat monitoring, links to `Device` and `AllocationHistory`
- **Server**: Federation support for multi-server deployments (master/slave role, heartbeat tracking)

### State Machine Rules (Critical!)
Valid states: `free`, `allocated`, `testing`, `busy`, `resetting`, `maintenance`, `offline`

Key transitions enforced by `state_machine.py`:
- `free` → `allocated`: Allocation
- `allocated` → `testing`: Test start
- `testing` → `allocated`: Test complete
- `testing` → `resetting`: Test hung/failed
- `allocated` → `resetting`: Expiry (background task)
- `resetting` → `free`: Reset complete

**All state changes MUST use `transition_device(device, new_state, session)` function** which validates transitions and updates `state_changed_at`. Direct state assignment bypasses validation!

## Critical Workflows

### Integrated Development Setup

This project works with two companion repositories for full functionality:
- **xts_core**: XTS testing framework client library
- **yaml_runner**: YAML-based test execution engine

The `./run.sh` script automatically clones these into `3rdParty/` directory for integrated development. The entire 3rdParty directory is gitignored to keep repos independent while allowing simultaneous work.

**Directory structure:**
```
xts_allocator_server/
├── 3rdParty/          # Development dependencies (gitignored)
│   ├── xts_core/      # Cloned from rdkcentral/xts_core
│   └── yaml_runner/   # Cloned from rdkcentral/yaml_runner
├── routes/            # Allocator API routes
└── ...
```

**Working across all three projects:**
1. Modify code in any of the three directories
2. Each has its own git history (independent repos)
3. Test integration locally before committing to individual repos
4. Push changes to respective upstream repositories
5. Delete entire 3rdParty/ directory to clean dependencies: `rm -rf 3rdParty/`

### Setup and Running (One-Command!)
```bash
./run.sh          # Clone deps, setup venv, install deps, init DB, start server
./run.sh setup    # Just setup, don't start
./run.sh test     # Run pytest suite
./run.sh clean    # Remove venv and database (keeps 3rdParty/)
./stop.sh         # Gracefully stop running server (SIGTERM, then SIGKILL)
rm -rf 3rdParty/  # Delete all development dependencies
```

**Manual setup alternative:**
```bash
source env.sh                         # Activate venv (creates if missing)
python database_setup.py              # Create tables
python test/populate_database.py     # Optional: Add test data
python app.py                         # Start server
deactivate                            # When done
```

### Database Migrations
- **Alembic**: Configured in `alembic.ini` with `migrations/` directory (2 versions exist)
- **Manual migrations**: `migrate_phase2.py` and `migrate_phase3.py` for schema evolution
- **Caution**: Direct `Base.metadata.create_all()` in `database_setup.py` creates all tables - no migration history

### Testing Strategy
- **Unit tests**: `tests/` directory with pytest (see `pytest.ini`)
- **Fixtures**: `tests/conftest.py` provides `app`, `test_client`, `db_session`, `sample_racks`, `sample_devices`
- **Run tests**: `./run.sh test` or `pytest` (requires venv activated)
- **Test coverage**: State machine, allocations, devices, racks, federation, health, history, usage, export
- **Manual API testing**: `test/test_routes.py` (requires running server on localhost:5000)

## Key Conventions

### Session Handling Pattern (Universal)
Every route handler MUST follow this pattern:
```python
session = SessionLocal()
try:
    # Database operations
    session.commit()
    return json({"data": result}, status=200)
except Exception as e:
    session.rollback()
    logger.error(f"Operation failed: {e}")
    return json({"error": str(e)}, status=500)
finally:
    session.close()  # ALWAYS close session
```

### Allocation Request/Response Pattern
Allocation endpoints expect:
```json
{
  "user": {"email": "user@example.com", "username": "jdoe", "name": "John Doe"},
  "slot": {"id": 1},  // OR "platform": "alpha.uk", "tags": ["4k"]
  "duration": "2h"    // Optional: "30m", "2h", "90m" (max 1 week)
}
```

Response includes device details, rack info, allocation metadata, history ID.

### Duration Parsing
`parse_duration()` in `allocation_routes.py`:
- Accepts: `"30m"`, `"2h"`, `"1.5h"`, `"90"` (assumes minutes)
- Returns: Integer minutes or None if invalid
- Max: 10080 minutes (1 week)
- Used for: Temporary allocations with `allocation_expiry` calculation

### Temporary vs Permanent Allocations
- **Temporary** (default): Has `allocation_expiry` timestamp, auto-deallocates via background task
- **Permanent** (`/allocate_permanent` endpoint): No expiry, manual deallocation only
- Test execution auto-extends temporary allocations if `expected_duration` exceeds remaining time (+15min buffer)

### Tag Handling (Important!)
- **Storage**: Comma-separated string in DB: `"tag1,tag2,tag3"`
- **Response**: Split to list: `device.tags.split(",") if device.tags else []`
- **Request**: Join from list: `",".join(slot_params.get("tags", []))`
- **Search**: Uses SQLAlchemy `.contains()` - substring match, not exact tag match
- **Future**: Consider proper many-to-many tag table for exact matching

### Logging Pattern
```python
from logging_config import get_logger
logger = get_logger()

logger.info(f"Slot allocated: device_id={device.id}, rack={device.rack.name}, email={user_email}")
logger.warning(f"Test {test_id} exceeded max duration, marking as timeout")
logger.error(f"Failed to transition device {device.id}: {message}")
```

Logs to: `logs/xts_allocator.log` (rotating, 10MB limit, 5 backups)

## Integration Points

### Database
- **File**: `xts_allocator.db` (SQLite in project root)
- **Engine**: `echo=True` → verbose SQL logging to console (disable for production!)
- **Sessions**: Manual `SessionLocal()` - no Flask-SQLAlchemy helpers
- **Schema**: See `models.py` for 5 tables with relationships, indexes, constraints

### API Endpoints (Key Routes)
- **Allocation**: POST `/allocate_slot`, POST `/allocate_permanent`, POST `/deallocate_slot`
- **State**: POST `/change_device_state`, GET `/device/<id>/valid_states`
- **Devices**: GET/POST `/list_slots` (GET=all, POST=filtered), POST `/add_slot`, POST `/update_slot`
- **Tests**: POST `/start_test`, POST `/test_heartbeat`, POST `/end_test`, GET `/test_executions`
- **Export**: GET `/export/raft_config?allocation_id=X` (YAML for XTS), GET `/export/python_raft_config` (Python dict)
- **Federation**: POST `/register` (slave→master), POST `/heartbeat`, GET `/servers`, GET `/devices/federated`
- **Monitoring**: GET `/health`, GET `/metrics`, GET `/device/<id>/usage_stats`, GET `/usage_summary`
- **History**: GET `/allocation_history?device_id=X&user_email=Y`

### Frontend
- **Dashboard**: `templates/dashboard.html` (main UI)
- **Legacy**: `templates/index.html` (old single-page view)
- **Static**: `/logo.png`, `/xts_allocator.xts` (XTS config file)

### Background Tasks
`check_expired_allocations()` in `app.py` runs every 60 seconds:
1. Finds expired temporary allocations (where `allocation_expiry <= now` and `state == allocated`)
2. Transitions devices to `resetting` state (not `free` - requires reset first!)
3. Finds hung tests (no heartbeat > `heartbeat_timeout` OR duration > `max_duration`)
4. Marks hung tests as timeout, transitions devices to resetting

### Federation Architecture
- **Master server**: Central coordination, accepts slave registrations
- **Slave servers**: Register via POST `/register`, send heartbeats, report device counts
- **Heartbeat**: Every 2 minutes expected, slaves marked offline if missed
- **Device queries**: Master can query slave devices via `/servers/<id>/devices`
- **Federated search**: GET `/devices/federated` aggregates devices across all servers

## Common Pitfalls & Known Issues

### State Machine Violations
❌ `device.state = "allocated"` - Bypasses validation!
✅ `transition_device(device, DeviceState.ALLOCATED.value, session)` - Enforces rules

### Allocation Expiry Logic
- Background task checks `state == allocated` ONLY - skips `testing` state devices
- Tests extend allocation automatically if `expected_duration` > remaining time
- Expired devices go to `resetting`, not `free` - assume device needs cleanup

### Tag Search Limitations
- `.contains()` does substring matching: searching "4k" matches "4k_hdr"
- No exact tag matching without custom query
- Consider full-text search or proper tag table for production

### History Tracking
- `AllocationHistory` now FULLY implemented with test counts, idle time, state tracking
- Created on allocation, updated during test execution, closed on deallocation
- Linked to `TestExecution` records via `allocation_history_id`

### Test Execution Edge Cases
- Test start requires `state == allocated` (not `free`)
- Heartbeat updates `last_heartbeat` - missing heartbeats → hung test detection
- Test end transitions `testing` → `allocated` (not `free`) - allocation persists
- Max duration (default 240min) prevents runaway tests

### Session Management
- Forgotten `session.close()` causes connection leaks in SQLite
- Always use try/finally pattern
- Rollback on exception prevents partial commits

### Performance Notes
- `engine = create_engine(DATABASE_URL, echo=True)` logs ALL SQL - disable for production
- SQLite has limited concurrency - consider PostgreSQL for high-load deployments
- `single_process=True` in Sanic - no worker processes, limited throughput
