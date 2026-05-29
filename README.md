# XTS Allocator Server

A device allocation management system for shared testing environments. Manages STB (Set-Top Box)
allocation across testing racks, preventing conflicts and tracking device states.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or later
- bash shell

### One-Command Setup

```bash
git clone https://github.com/rdkcentral/xts_allocator_server.git
cd xts_allocator_server
./run.sh
```

That's it! The script automatically:

- ✅ Creates isolated virtual environment
- ✅ Installs all dependencies
- ✅ Initializes SQLite database
- ✅ Offers to populate test data
- ✅ Starts server on `http://localhost:5000`

---

## 📝 Commands

### run.sh Usage

```bash
./run.sh          # Full setup and start server (default)
./run.sh setup    # Just setup, don't start
./run.sh test     # Run test suite
./run.sh clean    # Remove venv and database
```

### Stop Server

```bash
./stop.sh         # Gracefully stop running server
```

The stop script will:
- Find the server process on port 5000
- Send SIGTERM for graceful shutdown (10s timeout)
- Force kill if needed
- Provide clear status messages

**Exit Codes:**
- `0` - Success (server stopped)
- `1` - Failed to stop server
- `2` - Non-Python process on port 5000

### Manual Control (Alternative)

If you prefer step-by-step control:

```bash
# Activate virtual environment
source env.sh

# Initialize database
python database_setup.py

# (Optional) Add test data
python test/populate_database.py

# Start server
python app.py

# Deactivate when done
deactivate
```

---

## 📚 Usage

### Server Commands

Start server directly (after setup):

```bash
python app.py
```

Server runs on `http://0.0.0.0:5000`

**Server Exit Codes:**

- `0` - Normal shutdown (Ctrl+C or SIGTERM)
- `1` - Port 5000 already in use
- `2` - Network/socket error
- `3` - Permission denied
- `4` - Missing dependencies
- `5` - Unexpected error

**Graceful Shutdown:**

- Press `Ctrl+C` to stop the server gracefully
- Signal handlers ensure clean shutdown of background tasks
- Or use `./stop.sh` to stop a running server

### Client Commands (Future CLI)

1. **Allocate a Device**:

   ```bash
   xts allocate --id <device_id> --platform <platform_name> --tags <tag1,tag2> --duration <time>
   ```

2. **List All Slots**:

   ```bash
   xts allocator list
   ```

3. **Search for a Slot**:

   ```bash
   xts allocator search --platform <platform_name> --tags <tag1,tag2>
   ```

4. **Deallocate a Slot**:

   ```bash
   xts deallocate --id <device_id>
   ```

5. **Run a Test**:

   ```bash
   xts run --test <test_name> --allocate <device_id>
   ```

---

## 🏗️ Project Structure

```text
├── run.sh              # Universal run script (START HERE!)
├── stop.sh             # Stop running server
├── test-safe.sh        # Run tests with test database
├── env.sh              # Manual venv activation
├── app.py              # Sanic server entry point
├── models.py           # Database models (6 tables)
├── config.py           # Multi-environment configuration
├── database_setup.py   # Database initialization
├── state_machine.py    # Device state transition logic
├── auth.py             # JWT authentication & RBAC
├── rate_limiter.py     # API rate limiting
├── audit_log.py        # Security event logging
├── requirements.txt    # Python dependencies
├── bin/                # Database management utilities
│   ├── db-status       # Show database configuration
│   ├── db-switch       # Switch between test/production
│   └── db-clean        # Clean/reset test database
├── routes/             # API route blueprints (10 blueprints)
│   ├── allocation_routes.py    # Allocate/deallocate
│   ├── device_routes.py        # Device CRUD
│   ├── test_routes.py          # Test execution tracking
│   ├── auth_routes.py          # Authentication
│   ├── audit_log_routes.py     # Audit log queries
│   └── ...
├── templates/          # HTML templates
│   └── dashboard.html
├── test/               # Test scripts and utilities
│   ├── add_pi_devices.py
│   ├── demo_pi_simple.py
│   ├── demo_db_management.sh
│   └── populate_database.py
├── tests/              # pytest test suite (15 test modules)
└── docs/               # Documentation
    ├── DATABASE_MANAGEMENT.md
    ├── AUTHENTICATION.md
    └── POSTGRESQL_MIGRATION.md
```

---

## 🗄️ Database Management

The system supports **separate test and production databases** for safe testing and development.

### Quick Database Commands

```bash
# Check current database status
bin/db-status

# Switch to test mode (safe for experiments)
bin/db-switch test

# Reset test database (clear all data)
bin/db-clean test-reset

# Clear device registrations from test DB
bin/db-clean clear-devices

# Run tests with test database
./test-safe.sh
```

### Database Modes

1. **test** - Isolated test database (`xts_allocator_test.db`)
   - Can be freely rebuilt/cleaned
   - Used by test suite automatically
   - Safe for experimentation

2. **development** - Working database (`xts_allocator.db`)  
   - Your main development database
   - Persistent across sessions
   - Default mode

3. **production** - Production database
   - PostgreSQL (recommended) or SQLite
   - Protected from accidental cleaning
   - Requires explicit configuration

### Typical Workflow

```bash
# Daily development
./run.sh                    # Uses development database

# Running tests
./test-safe.sh              # Automatically uses test database

# API testing
bin/db-switch test          # Switch to test mode
bin/db-clean test-reset     # Clean slate
./run.sh                    # Start with clean test DB
# ... test your API ...
bin/db-clean clear-all      # Clean up

# Back to development
bin/db-switch development
./run.sh
```

See [DATABASE_MANAGEMENT.md](DATABASE_MANAGEMENT.md) for complete guide.

---

## 📖 API Documentation

### API Endpoints

1. **Allocate Slot (`POST /allocate_slot`)**:
   - Allocates a device based on ID, platform, or tags.
   - Parameters:

     ```json
     {
       "user": {
         "username": "user01",
         "name": "John Doe",
         "email": "john.doe@example.com"
       },
       "slot": {
         "id": "1",
         "platform": "alpha.uk",
         "tags": ["tag1", "tag2"]
       }
     }
     ```

2. **List Slots (`GET /list_slots`)**:
   - Lists all available and allocated slots.

3. **Search Slots (`POST /search_slots`)**:
   - Searches for slots matching specific criteria (platform, tags, etc.).

4. **Deallocate Slot (`POST /deallocate_slot`)**:
   - Deallocates a slot based on its ID and user ownership.

---

## 🤝 Contributing

See contributing file: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

See license file: [LICENSE](LICENSE)
