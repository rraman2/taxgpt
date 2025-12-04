#!/bin/bash
# Helper script to run examples with correct Python path

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Add project root to Python path
export PYTHONPATH="$PROJECT_ROOT/tenforty:$PYTHONPATH"

# Check if tenforty venv exists and activate it
if [ -d "$PROJECT_ROOT/tenforty/venv" ]; then
    echo "Activating tenforty virtual environment..."
    source "$PROJECT_ROOT/tenforty/venv/bin/activate"
fi

# Run the example
if [ -z "$1" ]; then
    echo "Usage: $0 <example_file.py>"
    echo ""
    echo "Available examples:"
    ls -1 "$SCRIPT_DIR"/*.py | xargs -n1 basename
    exit 1
fi

EXAMPLE_FILE="$SCRIPT_DIR/$1"

if [ ! -f "$EXAMPLE_FILE" ]; then
    echo "Error: $1 not found in $SCRIPT_DIR"
    exit 1
fi

echo "Running $1..."
echo "PYTHONPATH: $PYTHONPATH"
echo ""

python3 "$EXAMPLE_FILE"

