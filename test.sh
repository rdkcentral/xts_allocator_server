#!/bin/bash
# xts_allocator_server test runner
# Usage: ./test.sh [options] [test_path]
#   Options:
#     -v, --verbose          Verbose output
#     -k PATTERN             Run tests matching pattern
#     -x, --exitfirst        Exit on first failure
#     -s, --capture=no       Show print statements
#     --lf                   Run last failed tests
#     --ff                   Run failed tests first
#     --tb=style             Traceback style (short/long/line/native/no)
#     -h, --help             Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Automatically use test database
export XTS_MODE=test
export SQLITE_DB_PATH=xts_allocator_test.db

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Show help
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo "Usage: ./test.sh [options] [test_path]"
    echo ""
    echo "Options:"
    echo "  -v, --verbose         Verbose output"
    echo "  -k PATTERN            Run tests matching pattern"
    echo "  -x, --exitfirst       Exit on first failure"
    echo "  -s, --capture=no      Show print statements"
    echo "  --lf                  Run last failed tests"
    echo "  --ff                  Run failed tests first"
    echo "  --tb=style            Traceback style (short/long/line/native/no)"
    echo "  -h, --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  ./test.sh                                                          # Run all tests"
    echo "  ./test.sh tests/test_allocation.py                                 # Run specific test file"
    echo "  ./test.sh tests/test_federation.py::TestFederatedServers           # Run specific test class"
    echo "  ./test.sh tests/test_federation.py::TestFederatedServers::test_register_server_new  # Run specific test"
    echo "  ./test.sh -k federation                                            # Run tests matching 'federation'"
    echo "  ./test.sh -x tests/test_devices.py                                 # Stop on first failure"
    echo "  ./test.sh --lf                                                     # Re-run last failures"
    echo "  ./test.sh --tb=line tests/test_allocation.py                       # Concise traceback"
    exit 0
fi

echo -e "${GREEN}Running xts_allocator_server tests...${NC}"
echo -e "${YELLOW}Database mode: TEST (xts_allocator_test.db)${NC}\n"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check for pytest
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}pytest not found, installing...${NC}"
    pip install pytest pytest-asyncio --quiet
fi

# Build pytest arguments
PYTEST_ARGS="-v --tb=short"
TEST_PATH="tests/"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            PYTEST_ARGS="$PYTEST_ARGS -vv"
            shift
            ;;
        -k)
            PYTEST_ARGS="$PYTEST_ARGS -k $2"
            shift 2
            ;;
        -x|--exitfirst)
            PYTEST_ARGS="$PYTEST_ARGS -x"
            shift
            ;;
        -s|--capture=no)
            PYTEST_ARGS="$PYTEST_ARGS -s"
            shift
            ;;
        --lf)
            PYTEST_ARGS="$PYTEST_ARGS --lf"
            shift
            ;;
        --ff)
            PYTEST_ARGS="$PYTEST_ARGS --ff"
            shift
            ;;
        --tb=*)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
        tests/*|*/test_*.py)
            TEST_PATH="$1"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Run tests
echo -e "${YELLOW}Running: pytest $TEST_PATH $PYTEST_ARGS${NC}\n"
pytest $TEST_PATH $PYTEST_ARGS

echo -e "\n${GREEN}✓ Tests completed${NC}"
