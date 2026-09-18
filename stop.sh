#!/bin/bash
# XTS Allocator Server - Stop Script
# Gracefully stops the running server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Find process using port 5000
PID=$(lsof -ti:5000 2>/dev/null)

if [ -z "$PID" ]; then
    log_warn "No server process found on port 5000"
    exit 0
fi

# Check if it's our server
PROCESS_NAME=$(ps -p "$PID" -o comm= 2>/dev/null)

if [[ "$PROCESS_NAME" == *"python"* ]]; then
    log_info "Found server process (PID: $PID)"
    log_info "Sending SIGTERM for graceful shutdown..."
    
    # Send SIGTERM for graceful shutdown
    kill -TERM "$PID" 2>/dev/null
    
    # Wait up to 10 seconds for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            log_info "Server stopped gracefully"
            exit 0
        fi
        sleep 1
    done
    
    # If still running, force kill
    log_warn "Server did not stop gracefully, forcing..."
    kill -KILL "$PID" 2>/dev/null
    sleep 1
    
    if ! kill -0 "$PID" 2>/dev/null; then
        log_info "Server stopped (forced)"
        exit 0
    else
        log_error "Failed to stop server"
        exit 1
    fi
else
    log_error "Process on port 5000 (PID: $PID) is not Python. Please check manually."
    log_info "Process name: $PROCESS_NAME"
    exit 2
fi
