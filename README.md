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
├── env.sh              # Manual venv activation
├── app.py              # Sanic server entry point
├── models.py           # Database models (Device, AllocationHistory)
├── config.py           # Configuration settings
├── database_setup.py   # Database initialization
├── requirements.txt    # Python dependencies
├── routes/             # API route blueprints
│   ├── allocation_routes.py    # Allocate/deallocate operations
│   └── device_routes.py        # Device CRUD operations
├── templates/          # HTML templates
│   └── index.html
├── test/               # Test scripts
│   ├── test_routes.py
│   └── populate_database.py
└── design/             # Design documentation
    └── endpoints.md
```

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
