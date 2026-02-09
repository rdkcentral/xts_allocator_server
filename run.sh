#!/bin/bash
# XTS Allocator Server - Universal Run Script
# Usage: ./run.sh [command]
# Commands: start (default), setup, clean, test

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

# Set database mode (development by default, unless already set)
if [ -z "${XTS_MODE}" ]; then
    export XTS_MODE=development
    export SQLITE_DB_PATH=xts_allocator.db
fi

DB_FILE="${SCRIPT_DIR}/${SQLITE_DB_PATH}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Clone development dependencies for integrated development
setup_dev_repos() {
    log_info "Checking development dependencies..."
    
    # Create 3rdParty directory if not present
    mkdir -p "${SCRIPT_DIR}/3rdParty"
    
    # Clone xts_core if not present
    if [ ! -d "${SCRIPT_DIR}/3rdParty/xts_core" ]; then
        log_info "Cloning xts_core repository..."
        git clone git@github.com:rdkcentral/xts_core.git "${SCRIPT_DIR}/3rdParty/xts_core"
        if [ $? -ne 0 ]; then
            log_warn "Failed to clone via SSH, trying HTTPS..."
            git clone https://github.com/rdkcentral/xts_core.git "${SCRIPT_DIR}/3rdParty/xts_core"
        fi
        log_info "xts_core cloned"
    else
        log_info "xts_core already present"
    fi
    
    # Clone yaml_runner if not present
    if [ ! -d "${SCRIPT_DIR}/3rdParty/yaml_runner" ]; then
        log_info "Cloning yaml_runner repository..."
        git clone git@github.com:rdkcentral/yaml_runner.git "${SCRIPT_DIR}/3rdParty/yaml_runner"
        if [ $? -ne 0 ]; then
            log_warn "Failed to clone via SSH, trying HTTPS..."
            git clone https://github.com/rdkcentral/yaml_runner.git "${SCRIPT_DIR}/3rdParty/yaml_runner"
        fi
        log_info "yaml_runner cloned"
    else
        log_info "yaml_runner already present"
    fi
    
    log_info "Development dependencies ready"
}

# Check if virtual environment exists, create if not
setup_venv() {
    if [ ! -d "${VENV_DIR}" ]; then
        log_info "Virtual environment not found. Creating..."
        python3 -m venv "${VENV_DIR}"
        
        if [ $? -ne 0 ]; then
            log_error "Failed to create virtual environment"
            exit 1
        fi
        log_info "Virtual environment created"
    fi
    
    # Activate venv
    source "${VENV_DIR}/bin/activate"
    
    # Check if dependencies need installing
    if ! python -c "import sanic" 2>/dev/null; then
        log_info "Installing dependencies from requirements.txt..."
        pip install --upgrade pip -q
        pip install -r "${SCRIPT_DIR}/requirements.txt" -q
        log_info "Dependencies installed"
    else
        log_info "Dependencies already installed"
    fi
}

# Initialize database if it doesn't exist
setup_database() {
    if [ ! -f "${DB_FILE}" ]; then
        log_info "Database not found. Creating with migrations..."
        ./migrate.sh upgrade
        
        if [ $? -ne 0 ]; then
            log_error "Failed to create database"
            exit 1
        fi
        log_info "Database created"
        
        # Ask if user wants to populate test data
        read -p "Do you want to populate with test data? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python "${SCRIPT_DIR}/test/populate_database.py"
            log_info "Test data populated"
        fi
    else
        log_info "Database exists, running migrations..."
        ./migrate.sh upgrade
        log_info "Database up to date"
    fi
}

# Start the server
start_server() {
    log_info "Starting XTS Allocator Server..."
    log_info "Database mode: ${XTS_MODE} (${SQLITE_DB_PATH})"
    log_info "Server will be available at http://localhost:5000"
    log_info "Press Ctrl+C to stop"
    echo ""
    python "${SCRIPT_DIR}/app.py"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    pytest
}

# Clean everything
clean_all() {
    log_warn "This will remove the virtual environment and database"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning up..."
        [ -d "${VENV_DIR}" ] && rm -rf "${VENV_DIR}" && log_info "Removed venv/"
        [ -f "${DB_FILE}" ] && rm -f "${DB_FILE}" && log_info "Removed database"
        log_info "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

# Main execution
main() {
    cd "${SCRIPT_DIR}"
    
    COMMAND="${1:-start}"
    
    case "$COMMAND" in
        start)
            setup_dev_repos
            setup_venv
            setup_database
            start_server
            ;;
        setup)
            setup_dev_repos
            setup_venv
            setup_database
            log_info "Setup complete! Run './run.sh' to start the server"
            ;;
        test)
            # Override to test mode for running tests
            export XTS_MODE=test
            export SQLITE_DB_PATH=xts_allocator_test.db
            DB_FILE="${SCRIPT_DIR}/xts_allocator_test.db"
            setup_dev_repos
            setup_venv
            setup_database
            run_tests
            ;;
        clean)
            clean_all
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            echo "Usage: ./run.sh [command]"
            echo "Commands:"
            echo "  start  - Setup and start the server (default)"
            echo "  setup  - Just setup venv and database"
            echo "  test   - Run tests"
            echo "  clean  - Remove venv and database"
            exit 1
            ;;
    esac
}

main "$@"
