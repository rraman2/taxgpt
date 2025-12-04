#!/bin/bash
# Setup and install script for tenforty library

set -e  # Exit on error

echo "=== tenforty Library Setup and Installation ==="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Must run from tenforty directory"
    exit 1
fi

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python: $PYTHON_VERSION"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install build dependencies
echo "Installing build dependencies (Cython, setuptools, wheel)..."
pip install --upgrade "setuptools>=68.0" "wheel" "Cython>=3.0"

# Install package dependencies
echo "Installing package dependencies..."
pip install "pandas>=2.0" "pyarrow" "pydantic>=2" "python-dotenv"

# Install the package in editable mode (this will compile the Cython extension)
echo ""
echo "Installing tenforty package (this will compile Cython extensions)..."
echo "This may take a few minutes..."
pip install -e .

# Verify installation
echo ""
echo "Verifying installation..."
python3 -c "import tenforty; print(f'Successfully imported tenforty!')" 2>&1 || {
    echo "Error: Failed to import tenforty"
    exit 1
}

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "To use the library, activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "Then you can use it in Python:"
echo "  python3 -c \"from tenforty import evaluate_return; print(evaluate_return(w2_income=100000, state='CA', filing_status='Married/Joint', num_dependents=2).model_dump())\""
echo ""

