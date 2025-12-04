#!/usr/bin/env python3
"""
Example: Integrating Schedule C with Form 1040 using evaluate_form()

This demonstrates:
1. How to evaluate Schedule C separately
2. How to extract the net profit from Schedule C
3. How to integrate Schedule C results into the main 1040 form
"""

import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent.parent
tenforty_src = project_root / "tenforty" / "src"
tenforty_venv = project_root / "tenforty" / "venv"

if tenforty_venv.exists():
    lib_dir = tenforty_venv / "lib"
    if lib_dir.exists():
        python_dirs = [d for d in lib_dir.iterdir() if d.is_dir() and d.name.startswith("python")]
        if python_dirs:
            venv_site_packages = python_dirs[0] / "site-packages"
            if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
                sys.path.insert(0, str(venv_site_packages))

if tenforty_src.exists() and str(tenforty_src) not in sys.path:
    sys.path.insert(0, str(tenforty_src))

from tenforty.core import evaluate_form


def example_schedule_c_to_1040():
    """Example: Complete flow from Schedule C to 1040."""
    print("=" * 70)
    print("EXAMPLE: Schedule C → Schedule 1 → Form 1040 Integration")
    print("=" * 70)
    print()
    
    # Step 1: Evaluate Schedule C for your business
    print("STEP 1: Evaluate Schedule C")
    print("-" * 70)
    
    schedule_c_input = {
        'BusinessName': 'My Consulting Business',
        'PrincipalBus': 'Consulting',
        'L1': 150000,      # Gross receipts
        'L2': 5000,       # Returns and allowances
        'L6': 145000,     # Gross income (L1 - L2)
        'L8': 5000,       # Advertising
        'L9': 10000,      # Car and truck expenses
        'L10': 2000,      # Contractors
        'L11': 5000,      # Depreciation
        'L12': 3000,      # Insurance
        'L13': 2000,      # Interest
        'L14': 5000,      # Legal and professional
        'L15': 5000,      # Office expense
        'L17': 5000,      # Rent or lease
        'L18': 2000,      # Repairs and maintenance
        'L19': 2000,      # Supplies
        'L21': 5000,      # Taxes and licenses
        'L22': 2000,      # Travel
        'L23': 1000,      # Meals and entertainment
        'L25': 2000,      # Utilities
        'L26': 10000,     # Other expenses
        'L27': 70000,     # Total expenses (sum of above)
        'L31': 75000,     # Net profit (L6 - L27)
    }
    
    print("Schedule C Input:")
    print(f"  Business: {schedule_c_input['BusinessName']}")
    print(f"  Gross Income: ${schedule_c_input['L6']:,}")
    print(f"  Total Expenses: ${schedule_c_input['L27']:,}")
    print(f"  Net Profit: ${schedule_c_input['L31']:,}")
    print()
    
    # Evaluate Schedule C
    sched_c_result = evaluate_form(
        year=2024,
        federal_form_id='US_1040_Sched_C',
        federal_form_values=schedule_c_input
    )
    
    # Extract net profit from Schedule C result
    sched_c_output = sched_c_result['federal']
    net_profit = sched_c_output.get('L31', schedule_c_input['L31'])
    
    print("Schedule C Output:")
    print(f"  Net Profit (L31): ${net_profit:,.2f}")
    print()
    
    # Step 2: Use net profit in Form 1040
    print("STEP 2: Integrate with Form 1040")
    print("-" * 70)
    print()
    print("Schedule C net profit (L31) flows to:")
    print("  → Schedule 1, Line 3 (Business income)")
    print("  → Form 1040, Line 8 (Other income)")
    print()
    
    # Option A: Use simplified API (easiest)
    print("OPTION A: Use simplified API (recommended)")
    print("-" * 70)
    from tenforty import evaluate_return
    
    result_simplified = evaluate_return(
        year=2024,
        w2_income=100000,
        schedule_1_income=net_profit,  # Schedule C net profit goes here
        filing_status='Married/Joint',
        state='CA',
        num_dependents=2
    )
    
    print(f"W2 Income: ${100000:,}")
    print(f"Business Income (from Schedule C): ${net_profit:,.2f}")
    print(f"Total Tax: ${result_simplified.total_tax:,.2f}")
    print(f"Federal AGI: ${result_simplified.federal_adjusted_gross_income:,.2f}")
    print()
    
    # Option B: Use evaluate_form() with line-level fields
    print("OPTION B: Use evaluate_form() with line-level fields")
    print("-" * 70)
    
    form_1040_input = {
        'Status': 'Married/Joint',
        'Dependents': 2,
        'L1a': 100000,        # W2 income
        'S1_3': net_profit,   # Schedule 1, Line 3 (business income from Schedule C)
        # You can add any other 1040 fields here
    }
    
    result_1040 = evaluate_form(
        year=2024,
        federal_form_id='US_1040',
        federal_form_values=form_1040_input
    )
    
    federal_1040 = result_1040['federal']
    print(f"Form 1040 Input:")
    print(f"  W2 Income (L1a): ${form_1040_input['L1a']:,}")
    print(f"  Business Income (S1_3): ${form_1040_input['S1_3']:,.2f}")
    print()
    print(f"Form 1040 Output:")
    print(f"  Total Tax (L24): ${federal_1040.get('L24', 0):,.2f}")
    print(f"  AGI (L11): ${federal_1040.get('L11', 0):,.2f}")
    print(f"  Taxable Income (L15): ${federal_1040.get('L15', 0):,.2f}")
    print()


def example_multiple_schedule_c():
    """Example: Multiple Schedule C forms, then integrate."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Multiple Schedule C Forms")
    print("=" * 70)
    print()
    
    # Business 1
    business1_input = {
        'BusinessName': 'Consulting Business',
        'L1': 100000,
        'L27': 40000,
        'L31': 60000,
    }
    
    # Business 2
    business2_input = {
        'BusinessName': 'Online Store',
        'L1': 80000,
        'L27': 50000,
        'L31': 30000,
    }
    
    print("Evaluating Schedule C for Business 1...")
    result1 = evaluate_form(
        year=2024,
        federal_form_id='US_1040_Sched_C',
        federal_form_values=business1_input
    )
    net_profit_1 = result1['federal'].get('L31', business1_input['L31'])
    
    print("Evaluating Schedule C for Business 2...")
    result2 = evaluate_form(
        year=2024,
        federal_form_id='US_1040_Sched_C',
        federal_form_values=business2_input
    )
    net_profit_2 = result2['federal'].get('L31', business2_input['L31'])
    
    # Combine net profits
    total_business_income = net_profit_1 + net_profit_2
    
    print()
    print("Results:")
    print(f"  Business 1 Net Profit: ${net_profit_1:,.2f}")
    print(f"  Business 2 Net Profit: ${net_profit_2:,.2f}")
    print(f"  Total Business Income: ${total_business_income:,.2f}")
    print()
    print("Use total in 1040:")
    print(f"  schedule_1_income = ${total_business_income:,.2f}")
    print()
    
    # Use in 1040
    from tenforty import evaluate_return
    result = evaluate_return(
        w2_income=100000,
        schedule_1_income=total_business_income,
        filing_status='Married/Joint',
        state='CA'
    )
    
    print(f"Total Tax: ${result.total_tax:,.2f}")


def example_full_schedule_c_fields():
    """Example: Using all Schedule C fields."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Full Schedule C with All Fields")
    print("=" * 70)
    print()
    
    # Complete Schedule C with many fields
    full_sched_c = {
        'BusinessName': 'My Complete Business',
        'PrincipalBus': 'Professional Services',
        'ActivityCode': '541611',
        'BusinessEIN': '12-3456789',
        'Fmethod': 'Cash',  # Accounting method
        
        # Part I - Income
        'L1': 200000,   # Gross receipts
        'L2': 5000,     # Returns
        'L6': 195000,   # Gross income
        
        # Part II - Expenses (all major categories)
        'L8': 10000,    # Advertising
        'L9': 15000,    # Car and truck
        'L10': 5000,    # Contractors
        'L11': 8000,    # Depreciation
        'L12': 4000,    # Insurance
        'L13': 3000,    # Interest
        'L14': 12000,   # Legal and professional
        'L15': 6000,    # Office expense
        'L16a': 5000,   # Pension plans
        'L16b': 8000,   # Rent - vehicles/equipment
        'L17': 12000,   # Rent - other property
        'L18': 3000,    # Repairs
        'L19': 4000,    # Supplies
        'L20a': 6000,   # Taxes and licenses
        'L20b': 5000,   # Travel
        'L21': 2000,    # Meals and entertainment
        'L22': 4000,    # Utilities
        'L23': 30000,   # Wages
        'L24a': 5000,   # Other expenses
        'L25': 0,       # Reserved
        'L26': 0,       # Reserved
        'L27': 130000,  # Total expenses
        'L31': 65000,   # Net profit
    }
    
    result = evaluate_form(
        year=2024,
        federal_form_id='US_1040_Sched_C',
        federal_form_values=full_sched_c
    )
    
    output = result['federal']
    
    print("Schedule C with Full Field Set:")
    print(f"  Gross Income: ${full_sched_c['L6']:,}")
    print(f"  Total Expenses: ${full_sched_c['L27']:,}")
    print(f"  Net Profit: ${output.get('L31', full_sched_c['L31']):,.2f}")
    print()
    print("Key Output Fields Available:")
    key_fields = ['L1', 'L2', 'L6', 'L27', 'L28', 'L30', 'L31']
    for field in key_fields:
        if field in output:
            print(f"  {field}: {output[field]}")


if __name__ == "__main__":
    example_schedule_c_to_1040()
    example_multiple_schedule_c()
    example_full_schedule_c_fields()
    
    print("\n" + "=" * 70)
    print("KEY POINTS")
    print("=" * 70)
    print("""
1. evaluate_form() with 'US_1040_Sched_C' evaluates Schedule C separately
2. The result is a dict with 'federal' key containing all Schedule C output fields
3. Extract net profit using: result['federal'].get('L31', 0)
4. Net profit (L31) flows to:
   - Schedule 1, Line 3 (S1_3 in 1040 fields)
   - Form 1040, Line 8 (Other income)
5. For multiple businesses:
   - Evaluate each Schedule C separately
   - Sum the L31 values
   - Use combined total in 1040
6. Integration options:
   A. Simplified: Use schedule_1_income parameter (easiest)
   B. Advanced: Use evaluate_form() with S1_3 field (full control)
    """)

