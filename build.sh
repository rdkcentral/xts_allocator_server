#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

SCRIPT_NAME="app.py"
OUTPUT_DIR="dist"
BINARY_NAME="xts_allocator"
TEMPLATES_SOURCE="templates/style.css"
TEMPLATES_DEST="templates"
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
REQUIRED_PYTHON_VERSION="3.8+"

# Function to check if a version meets requirements
function version_check() {
    local check_version="$1"
    local required_version="$2"
    local check_version_split=(${check_version//\./" "})
    local req_version_split=(${required_version//\./" "})
    local stop=$(("${#req_version_split[@]}"-1))
    for i in $(seq 0 ${stop})
    do
        local req_version_section="${req_version_split[$i]}"
        local check_version_section="${check_version_split[$i]}"
        case "${req_version_section}" in
            *"+")
                req_version_section="${req_version_section%+}"
                if [[ "$check_version_section" -ge "${req_version_section}" ]]; then
                    return 0
                fi
                return 1
                ;;
            *"-")
                req_version_section="${req_version_section%-}"
                if [[ "$check_version_section" -le "${req_version_section}" ]]; then
                    return 0
                fi
                return 1
                ;;
            *)
                if [[ "${check_version_section}" != "${req_version_section}" ]]; then
                    return 1
                fi
                ;;
        esac
    done
    return 0
}

# Function to check Python version
function check_python_version() {
    local python_version
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo "Detected Python version: $python_version"
    if ! version_check "$python_version" "$REQUIRED_PYTHON_VERSION"; then
        echo "Error: Python $REQUIRED_PYTHON_VERSION or higher is required."
        exit 1
    fi
}

function setup_venv() {
    echo "Setting up Python virtual environment..."
    if [ -d "$VENV_DIR" ]; then
        echo "Virtual environment already exists. Checking Python version..."
        source "$VENV_DIR/bin/activate"
        local venv_python_version
        venv_python_version=$(python --version 2>&1 | awk '{print $2}')
        if version_check "$venv_python_version" "$REQUIRED_PYTHON_VERSION"; then
            echo "Reusing existing virtual environment with Python version: $venv_python_version"
            return
        else
            echo "Python version in the virtual environment does not meet requirements. Recreating..."
            deactivate
            rm -rf "$VENV_DIR"
        fi
    fi
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
}

function install_dependencies() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        echo "Installing dependencies..."
        pip install -r "$REQUIREMENTS_FILE"
    else
        echo "No requirements.txt found. Skipping dependency installation."
    fi
}

function build_binary() {
    echo "Building binary with PyInstaller..."
    pyinstaller --onefile --noconsole --name "$BINARY_NAME" \
        --distpath "$OUTPUT_DIR" \
        --add-data "$TEMPLATES_SOURCE:$TEMPLATES_DEST" \
        "$SCRIPT_NAME"
    echo "Build complete. Binary is located in the '$OUTPUT_DIR' directory."
}

function clean_up() {
    echo "Cleaning up temporary build files..."
    rm -rf build __pycache__ "$BINARY_NAME.spec"
}

function main() {
    echo "Starting build process..."
    check_python_version
    setup_venv
    install_dependencies
    build_binary
    clean_up
    echo "Build process completed successfully!"
}

main
