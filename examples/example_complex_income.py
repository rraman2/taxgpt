#!/usr/bin/env python3
"""
Example: How to input complex income scenarios with tenforty

This demonstrates how to handle:
- Multiple W2 wages (spouse income)
- Rental income
- Other income sources
- Itemized deductions
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

from tenforty import evaluate_return


def example_married_couple_with_rental():
    """Example: Married couple with combined W2 wages and rental income."""
    print("=" * 70)
    print("EXAMPLE 1: Married Couple with Rental Income")
    print("=" * 70)
    
    # Your scenario:
    your_w2 = 300_000
    spouse_w2 = 280_000
    rental_income = 3_000
    
    # For married filing jointly, combine both W2 wages
    total_w2 = your_w2 + spouse_w2
    
    result = evaluate_return(
        w2_income=total_w2,           # Combined W2 income
        schedule_1_income=rental_income,  # Rental income
        filing_status="Married/Joint",
        state="CA",                    # Change to your state
        num_dependents=0,              # Adjust if you have dependents
        year=2024
    )
    
    print(f"Input:")
    print(f"  Your W2 Income:      ${your_w2:,}")
    print(f"  Spouse W2 Income:    ${spouse_w2:,}")
    print(f"  Combined W2 Income:  ${total_w2:,}")
    print(f"  Rental Income:      ${rental_income:,}")
    print(f"  Filing Status:       Married/Joint")
    print()
    print(f"Results:")
    print(f"  Total Tax:           ${result.total_tax:,.2f}")
    print(f"  Federal Tax:         ${result.federal_total_tax:,.2f}")
    print(f"  State Tax:           ${result.state_total_tax:,.2f}")
    print(f"  Effective Tax Rate:  {result.federal_effective_tax_rate:.2f}%")
    print(f"  Tax Bracket:         {result.federal_tax_bracket:.1f}%")
    print()


def example_with_multiple_income_sources():
    """Example: Multiple income sources including investments."""
    print("=" * 70)
    print("EXAMPLE 2: Multiple Income Sources")
    print("=" * 70)
    
    your_w2 = 200_000
    spouse_w2 = 150_000
    rental_income = 12_000
    taxable_interest = 5_000
    qualified_dividends = 10_000
    long_term_capital_gains = 50_000
    
    result = evaluate_return(
        w2_income=your_w2 + spouse_w2,
        schedule_1_income=rental_income,
        taxable_interest=taxable_interest,
        qualified_dividends=qualified_dividends,
        long_term_capital_gains=long_term_capital_gains,
        filing_status="Married/Joint",
        state="CA",
        num_dependents=2,
        year=2024
    )
    
    print(f"Input:")
    print(f"  Combined W2 Income:        ${your_w2 + spouse_w2:,}")
    print(f"  Rental Income:            ${rental_income:,}")
    print(f"  Taxable Interest:         ${taxable_interest:,}")
    print(f"  Qualified Dividends:      ${qualified_dividends:,}")
    print(f"  Long-Term Capital Gains:   ${long_term_capital_gains:,}")
    print(f"  Dependents:               2")
    print()
    print(f"Results:")
    print(f"  Total Tax:                 ${result.total_tax:,.2f}")
    print(f"  Federal Tax:               ${result.federal_total_tax:,.2f}")
    print(f"  State Tax:                 ${result.state_total_tax:,.2f}")
    print(f"  Federal AGI:               ${result.federal_adjusted_gross_income:,.2f}")
    print()


def example_with_itemized_deductions():
    """Example: Using itemized deductions instead of standard."""
    print("=" * 70)
    print("EXAMPLE 3: Itemized Deductions")
    print("=" * 70)
    
    your_w2 = 300_000
    spouse_w2 = 280_000
    rental_income = 3_000
    itemized_deductions = 35_000  # e.g., mortgage interest, property tax, etc.
    
    # Compare standard vs itemized
    result_standard = evaluate_return(
        w2_income=your_w2 + spouse_w2,
        schedule_1_income=rental_income,
        filing_status="Married/Joint",
        standard_or_itemized="Standard",
        state="CA",
        year=2024
    )
    
    result_itemized = evaluate_return(
        w2_income=your_w2 + spouse_w2,
        schedule_1_income=rental_income,
        filing_status="Married/Joint",
        standard_or_itemized="Itemized",
        itemized_deductions=itemized_deductions,
        state="CA",
        year=2024
    )
    
    savings = result_standard.total_tax - result_itemized.total_tax
    
    print(f"Scenario: ${your_w2 + spouse_w2:,} W2 + ${rental_income:,} rental")
    print(f"Itemized Deductions: ${itemized_deductions:,}")
    print()
    print(f"{'Method':<20} {'Total Tax':<15} {'Taxable Income':<18}")
    print("-" * 55)
    print(f"{'Standard':<20} ${result_standard.total_tax:>12,.2f} ${result_standard.federal_taxable_income:>15,.2f}")
    print(f"{'Itemized':<20} ${result_itemized.total_tax:>12,.2f} ${result_itemized.federal_taxable_income:>15,.2f}")
    print()
    print(f"Tax Savings with Itemized: ${savings:,.2f}")
    print()


def example_single_filer_with_rental():
    """Example: Single filer with rental income."""
    print("=" * 70)
    print("EXAMPLE 4: Single Filer with Rental Income")
    print("=" * 70)
    
    w2_income = 150_000
    rental_income = 25_000
    
    result = evaluate_return(
        w2_income=w2_income,
        schedule_1_income=rental_income,
        filing_status="Single",
        state="CA",
        year=2024
    )
    
    print(f"W2 Income:        ${w2_income:,}")
    print(f"Rental Income:   ${rental_income:,}")
    print()
    print(f"Total Tax:       ${result.total_tax:,.2f}")
    print(f"Federal Tax:     ${result.federal_total_tax:,.2f}")
    print(f"State Tax:       ${result.state_total_tax:,.2f}")
    print()


if __name__ == "__main__":
    example_married_couple_with_rental()
    example_with_multiple_income_sources()
    example_with_itemized_deductions()
    example_single_filer_with_rental()
    
    print("=" * 70)
    print("KEY POINTS:")
    print("=" * 70)
    print("1. For married couples filing jointly: combine both W2 wages")
    print("   w2_income = your_w2 + spouse_w2")
    print()
    print("2. Rental income goes in schedule_1_income parameter")
    print()
    print("3. Other income sources:")
    print("   - taxable_interest: Interest from savings/bonds")
    print("   - qualified_dividends: Qualified dividend income")
    print("   - ordinary_dividends: Non-qualified dividends")
    print("   - short_term_capital_gains: Stocks held < 1 year")
    print("   - long_term_capital_gains: Stocks held > 1 year")
    print("   - schedule_1_income: Rental, business, other income")
    print()
    print("4. Deductions:")
    print("   - standard_or_itemized='Standard': Uses standard deduction")
    print("   - standard_or_itemized='Itemized': Use itemized_deductions parameter")
    print("=" * 70)

