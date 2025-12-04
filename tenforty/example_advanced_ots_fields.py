#!/usr/bin/env python3
"""
Example: Accessing ALL OTS Fields (Not Just the Simplified API)

The tenforty library's evaluate_return() only exposes ~15 common fields,
but the underlying OTS library supports HUNDREDS of fields for every line
on the 1040 form and all schedules.

This example shows how to access the full power of OTS using the lower-level
evaluate_form() function.
"""

from tenforty.core import evaluate_form, OTS_FORM_CONFIG


def show_available_fields():
    """Show all available fields for a given form."""
    print("=" * 70)
    print("DISCOVERING ALL AVAILABLE OTS FIELDS")
    print("=" * 70)
    
    year = 2024
    form_id = "US_1040"
    key = (year, form_id)
    
    if key not in OTS_FORM_CONFIG:
        print(f"Form {form_id} for year {year} not found")
        return
    
    form = OTS_FORM_CONFIG[key]
    print(f"\nForm: {form_id} for year {year}")
    print(f"Total fields available: {len(form.fields)}\n")
    
    print("Sample of available fields (first 50):")
    print("-" * 70)
    for i, field in enumerate(form.fields[:50]):
        default_str = f" (default: {field.default})" if field.default is not None else ""
        print(f"  {field.key:20s}{default_str}")
    
    if len(form.fields) > 50:
        print(f"  ... and {len(form.fields) - 50} more fields")
    
    print("\n" + "=" * 70)
    print("These are line-level identifiers from the actual 1040 form!")
    print("=" * 70)


def example_using_line_level_fields():
    """Example: Using line-level fields directly."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Using Line-Level Fields Directly")
    print("=" * 70)
    
    # Instead of using the simplified API:
    # evaluate_return(w2_income=100000, filing_status="Married/Joint")
    
    # You can use line-level fields directly:
    federal_form_values = {
        "Status": "Married/Joint",  # Filing status
        "L1a": 100000,              # Wages, salaries, tips (Line 1a)
        "L2b": 5000,                # Taxable interest (Line 2b)
        "L3a": 10000,               # Qualified dividends (Line 3a)
        "L3b": 12000,               # Ordinary dividends (Line 3b)
        "Dependents": 2,            # Number of dependents
        # You can add ANY field from the form here!
        # Check OTS_FORM_CONFIG to see all available fields
    }
    
    result = evaluate_form(
        year=2024,
        federal_form_id="US_1040",
        federal_form_values=federal_form_values
    )
    
    print("\nInput (line-level fields):")
    for key, value in federal_form_values.items():
        print(f"  {key}: {value}")
    
    print("\nOutput (parsed results):")
    federal = result["federal"]
    print(f"  Total Tax (L24): ${federal.get('L24', 'N/A')}")
    print(f"  AGI (L11): ${federal.get('L11', 'N/A')}")
    print(f"  Taxable Income (L15): ${federal.get('L15', 'N/A')}")
    print(f"  Tax Bracket: {federal.get('tax_bracket', 'N/A')}%")
    print(f"  Effective Rate: {federal.get('effective_tax_rate', 'N/A')}%")
    
    print("\nAll available output fields:")
    for key in sorted(federal.keys())[:20]:
        print(f"  {key}")
    if len(federal) > 20:
        print(f"  ... and {len(federal) - 20} more output fields")


def example_finding_specific_fields():
    """Example: Finding fields for specific tax situations."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Finding Fields for Specific Situations")
    print("=" * 70)
    
    year = 2024
    form_id = "US_1040"
    key = (year, form_id)
    form = OTS_FORM_CONFIG[key]
    
    # Search for fields related to specific topics
    search_terms = ["S1", "A", "Schedule", "Rental", "Business", "Self"]
    
    print("\nSearching for fields containing:")
    for term in search_terms:
        matching = [f.key for f in form.fields if term.lower() in f.key.lower()]
        if matching:
            print(f"\n  '{term}': {len(matching)} fields found")
            for field_key in matching[:10]:  # Show first 10
                print(f"    - {field_key}")
            if len(matching) > 10:
                print(f"    ... and {len(matching) - 10} more")


def example_comparing_simplified_vs_full():
    """Compare the simplified API vs full OTS access."""
    print("\n" + "=" * 70)
    print("COMPARISON: Simplified API vs Full OTS Access")
    print("=" * 70)
    
    print("\nSimplified API (evaluate_return):")
    print("  - Only ~15 common fields exposed")
    print("  - Easy to use, validated inputs")
    print("  - Good for 80% of use cases")
    print("  - Limited to common scenarios")
    
    print("\nFull OTS Access (evaluate_form):")
    print("  - Access to ALL form fields (100+ fields)")
    print("  - Use actual line numbers (L1a, L2b, S1_8z, etc.)")
    print("  - Can handle complex scenarios")
    print("  - Requires knowledge of tax form structure")
    print("  - No input validation (you must know valid values)")
    
    print("\nWhen to use each:")
    print("  - Use evaluate_return() for: Simple scenarios, common cases")
    print("  - Use evaluate_form() for: Complex scenarios, specific form lines")


def show_form_structure():
    """Show the structure of available forms."""
    print("\n" + "=" * 70)
    print("AVAILABLE FORMS AND THEIR FIELD COUNTS")
    print("=" * 70)
    
    # Group by form_id
    forms_by_id = {}
    for (year, form_id), form in OTS_FORM_CONFIG.items():
        if form_id not in forms_by_id:
            forms_by_id[form_id] = []
        forms_by_id[form_id].append((year, len(form.fields)))
    
    print("\nForms available:")
    for form_id in sorted(forms_by_id.keys()):
        years = forms_by_id[form_id]
        avg_fields = sum(count for _, count in years) / len(years)
        print(f"\n  {form_id}:")
        print(f"    Years: {[y for y, _ in years]}")
        print(f"    Average fields per year: {avg_fields:.0f}")
        print(f"    Field count range: {min(c for _, c in years)} - {max(c for _, c in years)}")


if __name__ == "__main__":
    show_available_fields()
    example_using_line_level_fields()
    example_finding_specific_fields()
    example_comparing_simplified_vs_full()
    show_form_structure()
    
    print("\n" + "=" * 70)
    print("HOW TO DISCOVER ALL FIELDS")
    print("=" * 70)
    print("""
1. Check OTS_FORM_CONFIG:
   from tenforty.core import OTS_FORM_CONFIG
   form = OTS_FORM_CONFIG[(2024, 'US_1040')]
   for field in form.fields:
       print(field.key)

2. Check OTS documentation/examples:
   The OTS library comes with example files showing field usage

3. Use evaluate_form() with line-level identifiers:
   result = evaluate_form(
       year=2024,
       federal_form_id="US_1040",
       federal_form_values={"L1a": 100000, "Status": "Married/Joint"}
   )

4. Enable debug logging to see raw OTS input/output:
   import os
   os.environ["FILE_LOG_LEVEL"] = "DEBUG"
   # Then run your calculation - check tenforty.log
    """)

