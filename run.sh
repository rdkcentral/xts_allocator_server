#!/bin/bash
# XTS Allocator Server - Universal Run Script
# Usage: ./run.sh [command]
# Commands: start (default), setup, clean, test

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
DB_FILE="${SCRIPT_DIR}/xts_allocator.db"

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
        log_info "Database not found. Initializing..."
        python "${SCRIPT_DIR}/database_setup.py"
        
        if [ $? -ne 0 ]; then
            log_error "Failed to initialize database"
            exit 1
        fi
        log_info "Database initialized"
        
        # Ask if user wants to populate test data
        read -p "Do you want to populate with test data? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python "${SCRIPT_DIR}/test/populate_database.py"
            log_info "Test data populated"
        fi
    else
        log_info "Database already exists"
    fi
}

# Start the server
start_server() {
    log_info "Starting XTS Allocator Server..."
    log_info "Server will be available at http://localhost:5000"
    log_info "Press Ctrl+C to stop"
    echo ""
    python "${SCRIPT_DIR}/app.py"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    python "${SCRIPT_DIR}/test/test_routes.py"
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
            setup_venv
            setup_database
            start_server
            ;;
        setup)
            setup_venv
            setup_database
            log_info "Setup complete! Run './run.sh' to start the server"
            ;;
        test)
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
