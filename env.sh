#!/bin/bash
# XTS Allocator Server - Virtual Environment Setup and Activation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

# Check if venv exists, if not create it
if [ ! -d "${VENV_DIR}" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv "${VENV_DIR}"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        return 1
    fi
    
    echo "Virtual environment created at ${VENV_DIR}"
    
    # Activate and install dependencies
    source "${VENV_DIR}/bin/activate"
    echo "Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r "${SCRIPT_DIR}/requirements.txt"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        return 1
    fi
    
    echo "Dependencies installed successfully"
else
    # Just activate existing venv
    source "${VENV_DIR}/bin/activate"
    echo "Virtual environment activated: ${VENV_DIR}"
fi

# Set PYTHONPATH to include project root
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

echo "Python version: $(python --version)"
echo "Python path: $(which python)"
echo ""
echo "Ready to work! Run 'deactivate' to exit the virtual environment."
