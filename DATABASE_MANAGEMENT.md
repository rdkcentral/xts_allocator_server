# Database Management Guide

This guide explains how to manage separate test and production databases for XTS Allocator Server.

## Overview

The system supports three operational modes:

1. **test** - Isolated test database (`xts_allocator_test.db`) that can be freely rebuilt
2. **development** - Working database (`xts_allocator.db`) for development
3. **production** - Production database (PostgreSQL or main SQLite)

## Quick Start

### Check Current Status

```bash
bin/db-status
```

Shows current mode, database location, and statistics.

### Switch Database Modes

```bash
# Switch to test mode
bin/db-switch test

# Switch to development mode  
bin/db-switch development

# Switch to production mode
bin/db-switch production
```

**Important:** Restart the server after switching modes:
```bash
./stop.sh && ./run.sh
```

### Clean Test Database

```bash
# Rebuild test database from scratch
bin/db-clean test-reset

# Clear all device registrations
bin/db-clean clear-devices

# Clear allocation history only
bin/db-clean clear-history

# Clear test execution records
bin/db-clean clear-tests

# Clear everything (devices, history, tests)
bin/db-clean clear-all
```

**Safety:** Clean commands only work on test database by default. Use `--force` to override.

## Typical Workflows

### Automated Testing Workflow

**The simple way (fully automatic):**
```bash
# Tests automatically use test database
./test.sh

# Server automatically uses development database
./run.sh
```

**Manual control if needed:**
```bash
# 1. Switch to test mode (optional - test.sh does this automatically)
bin/db-switch test

# 2. Reset test database to clean state
bin/db-clean test-reset -f

# 3. Add test devices
python test/populate_database.py

# 4. Run automated tests (automatically uses test DB)
./test.sh

# 5. Run API tests
python test/test_routes.py

# 6. Clean up after tests
bin/db-clean test-reset -f
```

### Development Workflow

```bash
# 1. Use development mode (automatic with ./run.sh)
./run.sh

# 2. Add your real devices
python test/add_pi_devices.py

# 3. Use the system normally
# http://localhost:5000/dashboard
```

### Production Deployment

```bash
# 1. Configure PostgreSQL
export DB_TYPE=postgresql
export POSTGRES_HOST=your-db-host
export POSTGRES_USER=xts_allocator
export POSTGRES_PASSWORD=secure-password
export POSTGRES_DB=xts_allocator

# 2. Switch to production mode
bin/db-switch production

# 3. Run migrations
python database_setup.py

# 4. Start server
./run.sh
```

## Environment Variables

### Mode Selection
- `XTS_MODE` - Operating mode: `test`, `development`, `production`

### Database Configuration
- `DB_TYPE` - Database type: `sqlite` (default) or `postgresql`
- `SQLITE_DB_PATH` - SQLite database file path
- `TEST_DB_PATH` - Test database path (default: `xts_allocator_test.db`)

### PostgreSQL (Production)
- `POSTGRES_HOST` - PostgreSQL host
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_DB` - PostgreSQL database name

## Testing Best Practices

### 1. Use test.sh - It's Automatic!

```bash
# test.sh automatically uses test database
./test.sh

# No need to set XTS_MODE manually!
```

The script automatically:
- Sets `XTS_MODE=test`
- Uses `xts_allocator_test.db`
- Shows database mode confirmation

### 2. Use run.sh for Development

```bash
# run.sh automatically uses development database
./run.sh

# Shows: Database mode: development (xts_allocator.db)
```

### 3. Reset Test Database Between Test Suites

```bash
# Before each major test run:
bin/db-clean test-reset -f
```

### 4. Isolate Test Data

Test database is completely separate from production:
- Test: `xts_allocator_test.db` (used by `./test.sh`)
- Development: `xts_allocator.db` (used by `./run.sh`)
- Production: PostgreSQL or configured SQLite

### 5. Use Force Flag in Automation

```bash
# Skip confirmation prompts in scripts:
bin/db-clean clear-all --force
```

## Database Scripts Reference

### bin/db-status
Shows current database configuration and statistics.

**Usage:**
```bash
bin/db-status
```

**Output:**
- Current mode (test/development/production)
- Database location and size
- Device counts by state
- Allocation and test statistics
- Server status

### bin/db-switch
Switches between database modes.

**Usage:**
```bash
bin/db-switch <mode>
```

**Modes:**
- `test` - Test database
- `development` - Development database  
- `production` - Production database

**Note:** Requires server restart to take effect.

### bin/db-clean
Cleans or resets database (test mode only by default).

**Usage:**
```bash
bin/db-clean <action> [options]
```

**Actions:**
- `test-reset` - Delete and rebuild test database
- `clear-devices` - Remove all device registrations
- `clear-history` - Clear allocation history
- `clear-tests` - Clear test execution records
- `clear-all` - Clear all data

**Options:**
- `-f, --force` - Skip confirmation and allow cleaning non-test databases
- `-q, --quiet` - Minimal output

**Examples:**
```bash
# Safe: Only works on test database
bin/db-clean clear-devices

# Force: Works on current database
bin/db-clean clear-devices --force
```

## Safety Features

### Protected Production Data

Clean commands verify you're in test mode:

```bash
$ bin/db-clean clear-devices
Error: Not in TEST mode!
Current database: xts_allocator.db

To clean test database:
  export XTS_MODE=test
  bin/db-clean clear-devices

Or use force flag to clean current database:
  bin/db-clean clear-devices --force
```

### Confirmation Prompts

All destructive operations require confirmation:

```bash
$ bin/db-clean test-reset
⚠  This will DELETE and rebuild xts_allocator_test.db
Continue? [y/N]
```

Use `--force` flag to skip prompts in automation.

## Integration with Existing Tools

### Test Runner (./test.sh)

**Automatically uses test database!** No setup needed:

```bash
./test.sh              # Automatic test mode
./test.sh -k allocation # Still uses test database
```

Output shows: `Database mode: TEST (xts_allocator_test.db)`

### Server (./run.sh)

**Automatically uses development database!** No setup needed:

```bash
./run.sh  # Automatic development mode
```

Output shows: `Database mode: development (xts_allocator.db)`

**Override if needed:**
```bash
XTS_MODE=test ./run.sh       # Run with test database
XTS_MODE=production ./run.sh  # Run with production database
```

### Database Setup (database_setup.py)

Respects `XTS_MODE` environment variable (automatically set by `./test.sh` and `./run.sh`):

```bash
# Not usually needed - scripts set this automatically
XTS_MODE=test python database_setup.py  # Creates test DB
XTS_MODE=production python database_setup.py  # Creates prod DB
```

### Server (./run.sh)

**Automatically sets development mode:**

```bash
./run.sh  # Uses development database (default)
```

Override if needed:
```bash
XTS_MODE=test ./run.sh  # Run with test database
./run.sh  # Back to development database
```

## Troubleshooting

### "Server is running" Warning

```bash
⚠  Server is running! Restart to apply changes:
    ./stop.sh && ./run.sh
```

Database mode changes require server restart.

### "Not in TEST mode" Error

You're trying to clean production data. Either:

1. Switch to test mode: `bin/db-switch test`
2. Use force flag: `bin/db-clean <action> --force`

### Database File Not Found

```bash
bin/db-clean test-reset  # Rebuild database
```

### Wrong Database in Use

```bash
bin/db-status  # Check current configuration
bin/db-switch test  # Switch to correct mode
./stop.sh && ./run.sh  # Restart server
```

## Examples

### CI/CD Pipeline

```yaml
# .gitlab-ci.yml or .github/workflows/test.yml
test:
  script:
    - bin/db-clean test-reset -f
    - python test/populate_database.py
    - ./test.sh  # Automatically uses test database
    - python test/test_routes.py
```

### Local Development

```bash
# Morning: Start fresh (automatic development mode)
./run.sh

# During day: Test changes (automatic test mode)
./test.sh

# Or test with fresh database
bin/db-clean test-reset
python test/add_pi_devices.py
./test.sh
```

### Production Maintenance

```bash
# Check production status
bin/db-status

# Never clean production directly!
# Instead, use test mode for validation:
bin/db-switch test
bin/db-clean test-reset
# Test migrations/changes
bin/db-switch production
```

## Migration from Old Setup

If you have existing `xts_allocator.db`:

```bash
# 1. Your existing DB becomes development DB (no change)
bin/db-status  # Verify

# 2. Create separate test DB
bin/db-switch test
bin/db-clean test-reset

# 3. Update test scripts to use test-safe.sh
./test-safe.sh  # Instead of ./test.sh

# 4. Your existing data is safe in xts_allocator.db
```

## API Endpoints Unaffected

All API endpoints work identically regardless of database mode. The mode only affects:
- Which physical database file is used
- Which cleanup scripts are allowed
- Logging/monitoring labels

## Best Practices Summary

✅ **DO:**
- Just use `./test.sh` for running tests (automatic!)
- Just use `./run.sh` for development (automatic!)
- Reset test DB before major test runs
- Check mode with `bin/db-status` if unsure
- Use force flag in CI/CD scripts

❌ **DON'T:**
- Worry about setting XTS_MODE manually (scripts do it!)
- Clean production database without backup
- Mix test and production data
- Forget to restart server after manual mode switch
- Use force flag casually on production systems
