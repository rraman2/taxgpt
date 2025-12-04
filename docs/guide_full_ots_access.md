# Guide: Accessing ALL OTS Fields (Not Just the Simplified API)

## The Problem

The `evaluate_return()` function only exposes **~15 common fields**:
- `w2_income`, `taxable_interest`, `qualified_dividends`, etc.

But the underlying **OTS library supports 256+ fields** for the 2024 US_1040 form alone!

## The Solution: Use `evaluate_form()` for Full Access

The library has a **lower-level interface** that gives you access to **every field** that OTS supports.

## Architecture Layers

```
Layer 3: evaluate_return()      ← Simplified API (~15 fields)
         ↓
Layer 2: evaluate_form()         ← Line-level API (256+ fields) ⭐ USE THIS!
         ↓
Layer 1: otslib._evaluate_form() ← Raw OTS C++ interface
```

## How to Access All Fields

### Step 1: Discover Available Fields

```python
from tenforty.core import OTS_FORM_CONFIG

# Get the form configuration
form = OTS_FORM_CONFIG[(2024, "US_1040")]

# See ALL available fields
print(f"Total fields: {len(form.fields)}")  # 256 fields!

for field in form.fields:
    print(f"{field.key:20s} (default: {field.default})")
```

### Step 2: Use Line-Level Fields

Instead of:
```python
from tenforty import evaluate_return

result = evaluate_return(
    w2_income=100000,
    filing_status="Married/Joint"
)
```

Use:
```python
from tenforty.core import evaluate_form

result = evaluate_form(
    year=2024,
    federal_form_id="US_1040",
    federal_form_values={
        "Status": "Married/Joint",
        "L1a": 100000,           # Wages (Line 1a)
        "L2b": 5000,             # Taxable interest (Line 2b)
        "L3a": 10000,            # Qualified dividends (Line 3a)
        "L3b": 12000,            # Ordinary dividends (Line 3b)
        "S1_8z": 3000,           # Schedule 1 other income (rental, etc.)
        "Dependents": 2,
        # You can add ANY of the 256 fields here!
    }
)

federal = result["federal"]
print(f"Total Tax: ${federal.get('L24', 0)}")
print(f"AGI: ${federal.get('L11', 0)}")
```

## Common Field Mappings

### Income Fields
- `L1a` - Wages, salaries, tips
- `L1b` - Tax-exempt interest
- `L2a` - Tax-exempt interest
- `L2b` - Taxable interest
- `L3a` - Qualified dividends
- `L3b` - Ordinary dividends
- `L4a`, `L4b` - IRA distributions
- `L5a`, `L5b` - Pensions and annuities
- `L6a` - Social Security benefits
- `S1_8z` - Schedule 1 other income (rental, business, etc.)

### Deduction Fields
- `A6` - Total itemized deductions
- `A1` - Medical and dental expenses
- `A2` - Taxes you paid
- `A5a` - Home mortgage interest
- `A8a` - Charitable contributions

### Credit Fields
- `L25a` - Child tax credit
- `L25b` - Credit for other dependents
- `L26` - Other credits

### Schedule Fields
- `S1_*` - Schedule 1 fields (additional income)
- `S2_*` - Schedule 2 fields (additional taxes)
- `S3_*` - Schedule 3 fields (refundable credits)

## Example: Complex Scenario with Full Field Access

```python
from tenforty.core import evaluate_form

# Complex scenario using line-level fields
federal_form_values = {
    "Status": "Married/Joint",
    "Dependents": 2,
    
    # Income
    "L1a": 300000,              # Your W2
    "L1b": 280000,              # Spouse W2 (if separate lines needed)
    "L2b": 5000,                # Taxable interest
    "L3a": 10000,               # Qualified dividends
    "L3b": 12000,               # Ordinary dividends
    "S1_8z": 3000,              # Rental income
    
    # Deductions (if itemizing)
    "A1": 5000,                 # Medical expenses
    "A2": 15000,                # State and local taxes
    "A5a": 12000,               # Mortgage interest
    "A8a": 5000,                # Charitable contributions
    
    # Credits
    "L25a": 4000,               # Child tax credit
}

result = evaluate_form(
    year=2024,
    federal_form_id="US_1040",
    federal_form_values=federal_form_values
)

federal = result["federal"]
print(f"Total Tax: ${federal.get('L24', 0):,.2f}")
print(f"AGI: ${federal.get('L11', 0):,.2f}")
print(f"Taxable Income: ${federal.get('L15', 0):,.2f}")
```

## Finding Fields for Your Needs

### Method 1: Search by keyword
```python
form = OTS_FORM_CONFIG[(2024, "US_1040")]
search_term = "rental"  # or "business", "self", "schedule", etc.

matching = [f.key for f in form.fields if search_term.lower() in f.key.lower()]
print(matching)
```

### Method 2: Check OTS documentation
The OTS library comes with example files showing field usage. Check the `ots/ots-releases/` directory.

### Method 3: Enable debug logging
```python
import os
os.environ["FILE_LOG_LEVEL"] = "DEBUG"

# Run your calculation
# Check tenforty.log to see the raw OTS input/output
```

## Available Forms

```python
from tenforty.core import OTS_FORM_CONFIG

# See all available forms
for (year, form_id) in OTS_FORM_CONFIG.keys():
    form = OTS_FORM_CONFIG[(year, form_id)]
    print(f"{year} {form_id}: {len(form.fields)} fields")
```

Common forms:
- `US_1040` - Federal 1040
- `CA_540` - California state
- `NY_IT201` - New York state
- `MA_1` - Massachusetts state
- Plus many more...

## Key Differences

| Feature | evaluate_return() | evaluate_form() |
|---------|------------------|-----------------|
| **Fields** | ~15 common fields | 256+ all fields |
| **Validation** | ✅ Pydantic validation | ❌ No validation |
| **Ease of use** | ✅ Very easy | ⚠️ Requires form knowledge |
| **Flexibility** | ❌ Limited | ✅ Full power |
| **Use case** | 80% of scenarios | Complex/edge cases |

## When to Use Each

**Use `evaluate_return()` when:**
- You have simple, common scenarios
- You want validation and helpful error messages
- You don't need specific form lines

**Use `evaluate_form()` when:**
- You need fields not exposed in the simplified API
- You have complex tax situations
- You need specific line-level control
- You're comfortable with tax form structure

## Summary

The simplified API (`evaluate_return`) is great for most cases, but when you need the **full power of OTS**, use `evaluate_form()` with line-level field identifiers. You get access to **all 256+ fields** that OTS supports!

