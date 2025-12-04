# Examples

This directory contains example scripts demonstrating how to use the tenforty tax calculation library.

## Running the Examples

All examples automatically add the tenforty library to the Python path, so you can run them directly:

```bash
# From project root - examples will find tenforty automatically
python3 examples/test_tenforty.py
python3 examples/example_complex_income.py
python3 examples/example_schedule_c.py
python3 examples/tax_return_builder.py
```

Or use the helper script:

```bash
./examples/run_example.sh test_tenforty.py
```

**Note:** The examples automatically detect and add the `tenforty/` directory to Python's path, so you don't need to install tenforty separately or activate a virtual environment (unless you want to use the tenforty venv for consistency).

## Example Files

- **test_tenforty.py** - Comprehensive test suite with 9 different tax scenarios
- **example_complex_income.py** - Examples with multiple income sources (W2, rental, investments)
- **example_schedule_c.py** - Schedule C (business income/expenses) examples
- **example_advanced_ots_fields.py** - How to access all 256+ OTS fields (not just simplified API)
- **how_to_discover_api.py** - Guide to discovering the tenforty API
- **tax_return_builder.py** - Multi-business tax return builder with clean architecture

## Notes

- All examples import from `tenforty` which should be installed or available in the path
- The examples are designed to be run from the project root directory
- Some examples may require the tenforty virtual environment to be activated

