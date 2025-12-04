"""Test Form 8812 with OTS to identify segfault cause."""
import sys
from pathlib import Path

# Add tenforty to path
tenforty_paths = [
    Path(__file__).parent.parent / "tenforty" / "venv" / "lib" / "python3.9" / "site-packages",
    Path(__file__).parent.parent / "tenforty" / "src",
]
for p in tenforty_paths:
    if p.exists():
        sys.path.insert(0, str(p))

try:
    from tenforty.core import evaluate_form  # type: ignore
except ImportError:
    import tenforty.core
    evaluate_form = tenforty.core.evaluate_form

def test_form8812_minimal():
    """Test Form 8812 with minimal required fields."""
    print("\n=== Test 1: Minimal Form 8812 inputs ===")
    form_8812_inputs = {
        "Status": "Married/Joint",  # Exact match per OTS source
        "L1": 205000.0,  # AGI (from Form 1040 line 11)
        "L4": 2,  # Number of qualifying children
        "L13": 0.0,  # Credit Limit Worksheet A
        "Amnt19": 0.0,  # Child tax credit (will be calculated)
        "L2a": 0.0,  # Puerto Rico income
        "L2b": 0.0,  # Form 2555 amounts
        "L2c": 0.0,  # Form 4563 amounts
        "L6": 0,  # Other dependents
    }
    
    print(f"Inputs: {form_8812_inputs}")
    
    try:
        result = evaluate_form(
            year=2024,
            federal_form_id="Form_8812",
            federal_form_values=form_8812_inputs,
        )
        print(f"✓ SUCCESS: Form 8812 calculated by OTS")
        print(f"Outputs: {result.get('federal', {})}")
        return True
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_form8812_with_strings():
    """Test Form 8812 with string values (might cause issues)."""
    print("\n=== Test 2: Form 8812 with string values ===")
    form_8812_inputs = {
        "Status": "Married/Joint",
        "L1": "205000",  # String instead of float
        "L4": "2",  # String instead of int
        "L13": "0",
        "Amnt19": "0",
        "L2a": "0",
        "L2b": "0",
        "L2c": "0",
        "L6": "0",
    }
    
    print(f"Inputs: {form_8812_inputs}")
    
    try:
        result = evaluate_form(
            year=2024,
            federal_form_id="Form_8812",
            federal_form_values=form_8812_inputs,
        )
        print(f"✓ SUCCESS: Form 8812 calculated with string values")
        return True
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("Testing Form 8812 with OTS library...")
    print("(Note: Segfaults will cause exit code 139)")
    
    success1 = test_form8812_minimal()
    if success1:
        print("\n✓ Form 8812 works with correct field mapping!")
    else:
        print("\n✗ Form 8812 still has issues")
        # Don't test with strings if minimal fails
        if "segfault" not in str(success1).lower():
            test_form8812_with_strings()

