#!/usr/bin/env python3
"""
Guide: How to Discover How to Use the tenforty Library

This demonstrates various methods to discover the API and input parameters.
"""

import inspect
from tenforty import evaluate_return, evaluate_returns


print("=" * 70)
print("METHOD 1: Read the README.md")
print("=" * 70)
print("""
The README.md file contains comprehensive documentation:
- List of all available parameters
- Parameter types and defaults
- Valid values for enums (like filing_status, state)
- Output fields
- Examples

Location: tenforty/README.md
Lines 58-107 contain the complete parameter documentation.
""")


print("\n" + "=" * 70)
print("METHOD 2: Use Python's help() function")
print("=" * 70)
print("\nRun: help(evaluate_return)")
print("\nThis shows:")
print("- Function signature with all parameters")
print("- Parameter types and default values")
print("- Docstring (if available)")


print("\n" + "=" * 70)
print("METHOD 3: Use inspect.signature()")
print("=" * 70)
sig = inspect.signature(evaluate_return)
print(f"\nFunction signature: {sig}")
print("\nAll parameters with defaults:")
for name, param in sig.parameters.items():
    default = param.default if param.default != inspect.Parameter.empty else "required"
    annotation = param.annotation if param.annotation != inspect.Parameter.empty else "any"
    print(f"  {name:25s} : {annotation:20s} = {default}")


print("\n" + "=" * 70)
print("METHOD 4: Check the source code")
print("=" * 70)
print("""
Location: tenforty/src/tenforty/core.py

The function definition shows:
- All parameter names
- Type hints
- Default values
- Return type

Example (lines 338-355):
    def evaluate_return(
        year: int = 2024,
        state: str | None = None,
        filing_status: str = "Single",
        num_dependents: int = 0,
        ...
    ) -> InterpretedTaxReturn:
""")


print("\n" + "=" * 70)
print("METHOD 5: Check the models to understand valid values")
print("=" * 70)
print("""
Location: tenforty/src/tenforty/models.py

Check the enums to see valid values:
- OTSFilingStatus: Valid filing statuses
- OTSState: Valid states
- OTSYear: Valid years

You can also import and inspect them:
""")

from tenforty.models import OTSFilingStatus, OTSState, OTSYear

print("Valid filing statuses:")
for status in OTSFilingStatus:
    print(f"  - {status.value}")

print("\nValid states:")
for state in OTSState:
    if state.value:  # Skip None
        print(f"  - {state.value}")


print("\n" + "=" * 70)
print("METHOD 6: Try it and see what errors you get")
print("=" * 70)
print("""
The library uses Pydantic for validation, so invalid inputs give helpful errors:

Try: evaluate_return(filing_status="Invalid")
You'll get: ValidationError with list of valid options

This is a great way to discover valid enum values!
""")


print("\n" + "=" * 70)
print("METHOD 7: Look at examples in the codebase")
print("=" * 70)
print("""
Check these files for usage examples:
- README.md (has multiple examples)
- tests/basic_test.py (shows basic usage)
- notebooks/tenforty_Package_Demo.ipynb (Jupyter examples)
""")


print("\n" + "=" * 70)
print("METHOD 8: Check the return type")
print("=" * 70)
print("""
The function returns InterpretedTaxReturn (a Pydantic model).

You can inspect what fields are available:
""")

from tenforty.models import InterpretedTaxReturn

# Get all fields from the model
fields = InterpretedTaxReturn.model_fields
print("Available output fields:")
for field_name, field_info in fields.items():
    print(f"  - {field_name}: {field_info.annotation}")


print("\n" + "=" * 70)
print("QUICK REFERENCE: All Parameters")
print("=" * 70)
print("""
Required: None (all have defaults)

Optional Parameters:
  year (int): Tax year (2018-2024), default=2024
  state (str|None): State code or None, default=None
  filing_status (str): "Single", "Married/Joint", etc., default="Single"
  num_dependents (int): Number of dependents, default=0
  standard_or_itemized (str): "Standard" or "Itemized", default="Standard"
  
Income Sources (all float, default=0.0):
  w2_income: W2 wages/salary
  taxable_interest: Interest income
  qualified_dividends: Qualified dividends
  ordinary_dividends: Ordinary dividends
  short_term_capital_gains: Short-term capital gains
  long_term_capital_gains: Long-term capital gains
  schedule_1_income: Rental, business, other income
  incentive_stock_option_gains: ISO gains (triggers AMT)
  
Deductions (float, default=0.0):
  itemized_deductions: Total itemized deductions
  state_adjustment: State-specific adjustments
""")


print("\n" + "=" * 70)
print("EXAMPLE: Discovering valid values interactively")
print("=" * 70)
print("""
# Try invalid input to see valid options
try:
    evaluate_return(filing_status="Wrong")
except Exception as e:
    print(e)  # Will show valid options!

# Check what the function returns
result = evaluate_return(w2_income=100000)
print(result.model_dump())  # See all available fields
print(result.total_tax)     # Access specific fields
""")

