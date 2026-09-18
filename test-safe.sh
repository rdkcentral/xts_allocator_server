#!/usr/bin/env bash
# Run tests with test database
# Ensures XTS_MODE=test is set

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Ensure test mode
export XTS_MODE=test
export SQLITE_DB_PATH=xts_allocator_test.db

# Activate venv if needed
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Run ./run.sh setup first."
    exit 1
fi

source venv/bin/activate

# Create test database if it doesn't exist
if [ ! -f "xts_allocator_test.db" ]; then
    echo "Creating test database..."
    python database_setup.py
fi

# Run pytest with all arguments passed through
echo "Running tests with test database: xts_allocator_test.db"
python -m pytest "$@"
