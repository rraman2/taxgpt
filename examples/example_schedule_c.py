#!/usr/bin/env python3
"""
Example: Using Schedule C (Business Income/Expenses) with tenforty

Schedule C is for reporting profit or loss from a business (sole proprietorship).
This example shows:
1. All Schedule C fields available
2. How to use Schedule C
3. Handling multiple businesses
"""

import sys
from pathlib import Path

# Add tenforty to path if not installed
project_root = Path(__file__).parent.parent
tenforty_src = project_root / "tenforty" / "src"
tenforty_venv = project_root / "tenforty" / "venv"

# Try to use venv site-packages for dependencies (handles any Python version)
if tenforty_venv.exists():
    lib_dir = tenforty_venv / "lib"
    if lib_dir.exists():
        python_dirs = [d for d in lib_dir.iterdir() if d.is_dir() and d.name.startswith("python")]
        if python_dirs:
            venv_site_packages = python_dirs[0] / "site-packages"
            if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
                sys.path.insert(0, str(venv_site_packages))

# Add tenforty src to path
if tenforty_src.exists() and str(tenforty_src) not in sys.path:
    sys.path.insert(0, str(tenforty_src))

from tenforty.core import OTS_FORM_CONFIG, evaluate_form, generate_ots_return
import tenforty.otslib as otslib


def show_schedule_c_fields():
    """Show all Schedule C fields for 2024."""
    print("=" * 70)
    print("2024 SCHEDULE C - ALL FIELDS")
    print("=" * 70)
    
    form = OTS_FORM_CONFIG.get((2024, 'US_1040_Sched_C'))
    if not form:
        print("Schedule C form not found for 2024")
        return
    
    print(f"\nTotal fields: {len(form.fields)}\n")
    
    # Categorize fields
    print("BUSINESS INFORMATION FIELDS:")
    print("-" * 70)
    info_fields = ['Title:', 'YourName:', 'YourSocSec#:', 'PrincipalBus:', 
                   'BusinessName:', 'Number&Street:', 'TownStateZip:', 
                   'ActivityCode:', 'BusinessEIN:', 'Fmethod:', 'GPartic:', 
                   'Hacquired:', 'Ireq1099s:', 'Jfile1099s:']
    for field in form.fields:
        if field.key in info_fields:
            print(f"  {field.key:20s} (default: {field.default})")
    
    print("\nPART I - INCOME:")
    print("-" * 70)
    income_lines = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7']
    for field in form.fields:
        if field.key in income_lines:
            print(f"  {field.key:10s} - Line {field.key[1:]} on Schedule C")
    
    print("\nPART II - EXPENSES:")
    print("-" * 70)
    expense_lines = ['L8', 'L9', 'L10', 'L11', 'L12', 'L13', 'L14', 'L15',
                     'L16a', 'L16b', 'L17', 'L18', 'L19', 'L20a', 'L20b',
                     'L21', 'L22', 'L23', 'L24a', 'L24b', 'L25', 'L26']
    for field in form.fields:
        if field.key in expense_lines:
            print(f"  {field.key:10s} - Line {field.key.replace('a', '').replace('b', '')} on Schedule C")
    
    print("\nPART III - COST OF GOODS SOLD:")
    print("-" * 70)
    cogs_lines = ['L30', 'L32a', 'L33:', 'L34:', 'L35', 'L36', 'L37', 'L38', 'L39']
    for field in form.fields:
        if field.key in cogs_lines:
            print(f"  {field.key:10s}")
    
    print("\nPART IV - INFORMATION ON YOUR VEHICLE:")
    print("-" * 70)
    vehicle_lines = ['L41', 'L43:', 'L44a', 'L44b', 'L44c', 'L45:', 'L46:', 
                     'L47a:', 'L47b:']
    for field in form.fields:
        if field.key in vehicle_lines:
            print(f"  {field.key:10s}")
    
    print("\nPART V - OTHER EXPENSES:")
    print("-" * 70)
    other_expense_fields = [f for f in form.fields if 'L48' in f.key]
    for field in other_expense_fields:
        print(f"  {field.key:20s}")


def example_single_business():
    """Example: Single business using Schedule C."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Single Business Schedule C")
    print("=" * 70)
    
    # Schedule C values for one business
    sched_c_values = {
        'BusinessName': 'My Consulting Business',
        'PrincipalBus': 'Consulting',
        'ActivityCode': '541611',  # NAICS code
        'Fmethod': 'Cash',  # Accounting method
        
        # Part I - Income
        'L1': 150000,  # Gross receipts or sales
        'L2': 5000,    # Returns and allowances
        'L6': 145000,  # Gross income (L1 - L2)
        
        # Part II - Expenses
        'L8': 5000,    # Advertising
        'L9': 10000,   # Car and truck expenses
        'L10': 2000,   # Contractors
        'L11': 5000,   # Depreciation
        'L12': 3000,   # Insurance
        'L13': 2000,   # Interest (mortgage)
        'L14': 5000,   # Legal and professional services
        'L15': 10000,  # Office expense
        'L17': 5000,   # Rent or lease
        'L18': 2000,   # Repairs and maintenance
        'L19': 3000,   # Supplies
        'L21': 5000,   # Taxes and licenses
        'L22': 2000,   # Travel
        'L23': 1000,   # Meals and entertainment
        'L25': 5000,   # Utilities
        'L26': 10000,  # Other expenses
        'L27': 70000,  # Total expenses (sum of above)
        
        # Part III - Net profit or loss
        'L31': 75000,  # Net profit (L6 - L27)
    }
    
    print("\nBusiness Details:")
    print(f"  Business Name: {sched_c_values['BusinessName']}")
    print(f"  Gross Income: ${sched_c_values['L6']:,}")
    print(f"  Total Expenses: ${sched_c_values['L27']:,}")
    print(f"  Net Profit: ${sched_c_values['L31']:,}")
    
    print("\nNote: Schedule C net profit (L31) flows to Schedule 1, Line 3")
    print("      which then flows to Form 1040, Line 8")


def example_multiple_businesses():
    """Example: Handling multiple businesses."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Multiple Businesses")
    print("=" * 70)
    
    print("""
IMPORTANT: The IRS allows multiple Schedule C forms, but OTS/tenforty
typically processes ONE Schedule C at a time. For multiple businesses:

OPTION 1: Combine all businesses into one Schedule C
  - Add all gross receipts together
  - Add all expenses together
  - Report as single business
  
OPTION 2: Process each Schedule C separately, then combine results
  - Calculate each business separately
  - Sum the net profits (L31) from each
  - Use the combined net profit in your 1040
  
OPTION 3: Use Schedule C fields in the main 1040
  - Some Schedule C data can be entered directly in 1040 fields
  - Check if 1040 has Schedule C summary fields
""")
    
    # Business 1
    business1 = {
        'BusinessName': 'Consulting Business',
        'L1': 100000,  # Gross receipts
        'L27': 40000,  # Total expenses
        'L31': 60000,  # Net profit
    }
    
    # Business 2
    business2 = {
        'BusinessName': 'Online Store',
        'L1': 80000,   # Gross receipts
        'L27': 50000,  # Total expenses
        'L31': 30000,  # Net profit
    }
    
    print("Business 1:")
    print(f"  Name: {business1['BusinessName']}")
    print(f"  Net Profit: ${business1['L31']:,}")
    
    print("\nBusiness 2:")
    print(f"  Name: {business2['BusinessName']}")
    print(f"  Net Profit: ${business2['L31']:,}")
    
    total_net_profit = business1['L31'] + business2['L31']
    print(f"\nCombined Net Profit: ${total_net_profit:,}")
    print("This would go on Schedule 1, Line 3, then to 1040, Line 8")


def example_using_schedule_c_with_1040():
    """Example: How Schedule C integrates with 1040."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Schedule C Integration with 1040")
    print("=" * 70)
    
    print("""
Schedule C flow:
  1. Complete Schedule C for your business
  2. Net profit (L31) goes to Schedule 1, Line 3
  3. Schedule 1 total goes to 1040, Line 8 (Other income)
  4. This becomes part of your Adjusted Gross Income (AGI)

In tenforty, you can:
  
  A. Use the simplified API with schedule_1_income:
     from tenforty import evaluate_return
     result = evaluate_return(
         w2_income=100000,
         schedule_1_income=75000  # Net profit from Schedule C
     )
  
  B. Use evaluate_form() with Schedule C directly:
     # First evaluate Schedule C
     sched_c_result = evaluate_form(
         year=2024,
         federal_form_id='US_1040_Sched_C',
         federal_form_values={...}
     )
     
     # Then use the net profit in 1040
     # (This requires manual integration)
  
  C. Use line-level fields in 1040:
     # Some 1040 fields may accept Schedule C data directly
     result = evaluate_form(
         year=2024,
         federal_form_id='US_1040',
         federal_form_values={
             'L1a': 100000,  # W2 income
             'S1_3': 75000,  # Schedule 1, Line 3 (business income)
             # ... other fields
         }
     )
""")


def show_schedule_c_line_reference():
    """Show what each Schedule C line represents."""
    print("\n" + "=" * 70)
    print("SCHEDULE C LINE REFERENCE (2024)")
    print("=" * 70)
    
    line_descriptions = {
        'L1': 'Gross receipts or sales',
        'L2': 'Returns and allowances',
        'L3': 'Cost of goods sold (if applicable)',
        'L4': 'Gross profit (L1 - L2 - L3)',
        'L5': 'Other income',
        'L6': 'Gross income (L4 + L5)',
        'L7': 'Gross income (if no COGS, L1 - L2 + L5)',
        
        # Expenses
        'L8': 'Advertising',
        'L9': 'Car and truck expenses',
        'L10': 'Contractors',
        'L11': 'Depreciation and section 179 expense',
        'L12': 'Insurance',
        'L13': 'Interest (mortgage and other)',
        'L14': 'Legal and professional services',
        'L15': 'Office expense',
        'L16a': 'Pension and profit-sharing plans',
        'L16b': 'Rent or lease - vehicles, machinery, equipment',
        'L17': 'Rent or lease - other business property',
        'L18': 'Repairs and maintenance',
        'L19': 'Supplies',
        'L20a': 'Taxes and licenses',
        'L20b': 'Travel',
        'L21': 'Meals and entertainment',
        'L22': 'Utilities',
        'L23': 'Wages',
        'L24a': 'Other expenses (with descriptions)',
        'L25': 'Reserved',
        'L26': 'Reserved',
        'L27': 'Total expenses',
        'L28': 'Tentative profit (L6 - L27)',
        'L29': 'Reserved',
        'L30': 'Net profit or (loss) (L28 - L29)',
        'L31': 'Net profit or (loss) - final',
    }
    
    print("\nKey Lines:")
    for line, desc in line_descriptions.items():
        print(f"  {line:6s} - {desc}")


if __name__ == "__main__":
    show_schedule_c_fields()
    example_single_business()
    example_multiple_businesses()
    example_using_schedule_c_with_1040()
    show_schedule_c_line_reference()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
1. Schedule C has 75 fields covering all business income and expenses
2. Each Schedule C represents ONE business
3. For multiple businesses:
   - Combine into one Schedule C, OR
   - Calculate each separately and sum the net profits
4. Schedule C net profit (L31) flows to Schedule 1, Line 3
5. Use schedule_1_income in evaluate_return() for simple cases
6. Use evaluate_form() with 'US_1040_Sched_C' for full control
    """)

