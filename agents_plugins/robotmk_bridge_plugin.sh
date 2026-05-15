#!/bin/bash
# Robotmk Bridge Plugin — Linux/Unix wrapper
# Checks for Python and the main Python script before execution.

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/robotmk_bridge_plugin.py"

# Error section helper
emit_error() {
    local message="$1"
    echo "<<<robotmk_bridge>>>"
    echo "{\"status\": \"error\", \"error_type\": \"wrapper\", \"message\": \"${message}\"}"
}

# Check 1: Python3 available on PATH
if ! command -v python3 &> /dev/null; then
    emit_error "Python not found on PATH."
    exit 1
fi

# Check 2: Python script exists next to this wrapper
if [ ! -f "${PYTHON_SCRIPT}" ]; then
    emit_error "robotmk_bridge_plugin.py not found next to wrapper."
    exit 1
fi

# All checks passed — execute Python script and pass through stdout
exec python3 "${PYTHON_SCRIPT}"
