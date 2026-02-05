# XTS Allocator Server - AI Agent Instructions

## Project Overview
XTS Allocator Server is a device allocation management system for shared testing environments. It prevents conflicts by tracking device states (free/allocated) and ownership via email-based authorization. Built with Sanic (async web framework) and SQLAlchemy ORM with SQLite backend.

## Architecture

### Core Components
- **`app.py`**: Sanic application entry point, registers blueprints for routes
- **`models.py`**: SQLAlchemy models (`Device`, `AllocationHistory`) and session management
- **`routes/`**: Blueprint-based route organization
  - `allocation_routes.py`: Allocate/deallocate slot operations (state transitions)
  - `device_routes.py`: CRUD operations for device inventory (list, add, update, delete)
- **`config.py`**: Database URL configuration (currently hardcoded SQLite path)
- **`database_setup.py`**: One-time database initialization script

### Data Model
- **Device table**: Tracks physical devices with `rack_name`, `slot_name`, `platform`, `tags` (comma-separated), `state` (free/allocated), `owner_email`
- **AllocationHistory table**: Historical allocation records (currently defined but not actively used in routes)
- Tags stored as comma-separated strings, split/joined in route handlers

## Critical Workflows

### Database Initialization
```bash
python database_setup.py  # Creates tables, run once before first start
```

### Running Server
```bash
python app.py  # Starts Sanic on 0.0.0.0:5000 with single_process=True
```

### Building Binary
```bash
./build.sh  # Uses PyInstaller to create standalone binary in bin/ directory
```

### Testing
Manual testing via `test/test_routes.py` - requires server running on localhost:5000:
```bash
python test/test_routes.py
```

## Key Conventions

### Request/Response Patterns
All allocation/deallocation requests follow this structure:
```json
{
  "user": {"email": "user@example.com"},
  "slot": {"id": 1, "platform": "alpha.uk", "tags": ["tag1"]}
}
```

### State Management
- Devices have two states: `"free"` or `"allocated"`
- Allocation sets `state="allocated"` and `owner_email=user_email`
- Deallocation requires email match for authorization (403 if mismatch)
- No JWT/token auth - email-based ownership only

### Session Handling Pattern
Every route uses try/finally with session cleanup:
```python
session = SessionLocal()
try:
    # database operations
    session.commit()
except Exception as e:
    session.rollback()
    return json({"error": str(e)}, status=500)
finally:
    session.close()
```

### Tag Handling
- Stored as comma-separated strings in database: `"tag1,tag2"`
- Split to list in responses: `tags.split(",") if tags else []`
- Joined from list in requests: `",".join(tags)`
- Search uses SQLAlchemy `.contains()` method (partial match)

## Integration Points

### Database
- SQLite file: `xts_allocator.db` (created in project root)
- SQLAlchemy engine with `echo=True` (verbose SQL logging in console)
- Direct session management via `SessionLocal()` (no Flask-SQLAlchemy helpers)

### API Design
- RESTful endpoints documented in `design/endpoints.md`
- Mixed GET/POST patterns: `/list_slots` supports both GET (all) and POST (filtered)
- Status codes: 200 (success), 201 (created), 400 (bad request), 403 (unauthorized), 404 (not found), 409 (conflict), 500 (server error)

### Frontend
- Single-page HTML served at `/` from `templates/index.html`
- Static logo served via `app.static()` route

## Git Commit Message Standards

Follow the 50/72 rule for all commit messages as defined in [RDK Central Standards](https://rdkcentral.github.io/rdk-halif-aidl/0.13.0/whitepapers/standardizing_git_commit_messages/):

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

## Common Pitfalls
- `AllocationHistory` model exists but no routes populate it - history tracking incomplete
- Tags filtering uses `.contains()` which does substring matching (not exact tag match)
- No duration/timeout enforcement despite README mentioning `--duration` flag
- Allocation by platform without `id` returns first match only (no multi-device allocation)
- `single_process=True` in Sanic means no multi-worker support
