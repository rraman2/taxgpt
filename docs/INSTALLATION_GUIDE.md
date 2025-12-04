# tenforty Library Installation Guide

## Prerequisites

This library requires **Xcode Command Line Tools** to compile the Cython extensions.

### Step 1: Install Xcode Command Line Tools

1. A dialog should have appeared asking to install the tools. If not, run:
   ```bash
   xcode-select --install
   ```

2. Follow the installation wizard (this may take 10-15 minutes)

3. Verify installation:
   ```bash
   xcode-select -p
   ```
   This should output something like `/Library/Developer/CommandLineTools`

### Step 2: Install the Library

Once Xcode Command Line Tools are installed, run:

```bash
cd /Users/ramesh/Documents/Projects/taxgpt/tenforty
./setup_and_install.sh
```

Or manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install build dependencies
pip install --upgrade "setuptools>=68.0" "wheel" "Cython>=3.0"

# Install package dependencies
pip install "pandas>=2.0" "pyarrow" "pydantic>=2" "python-dotenv"

# Install tenforty (this compiles the Cython extension)
pip install -e .
```

### Step 3: Verify Installation

```bash
source venv/bin/activate
python3 -c "from tenforty import evaluate_return; print('Success!')"
```

## Alternative: Install from PyPI (Pre-built)

If you want to skip compilation, you can install a pre-built wheel from PyPI:

```bash
pip install tenforty
```

However, note that pre-built wheels may not be available for all platforms.

## Troubleshooting

### If compilation fails:
- Ensure Xcode Command Line Tools are fully installed
- Check that you have a C++ compiler: `g++ --version` or `clang++ --version`
- Try upgrading setuptools: `pip install --upgrade setuptools wheel Cython`

### If import fails:
- Make sure you've activated the virtual environment
- Check that the package was installed: `pip list | grep tenforty`

## Usage Example

```python
from tenforty import evaluate_return

result = evaluate_return(
    w2_income=100_000,
    state="CA",
    filing_status="Married/Joint",
    num_dependents=2
)

print(result.model_dump())
```

