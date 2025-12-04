#!/usr/bin/env python3
"""
Test wrapper for the tenforty tax calculation library.
This script tests various tax scenarios and validates the library functionality.
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

from tenforty import evaluate_return, evaluate_returns


def test_basic_calculation():
    """Test a basic tax calculation."""
    print("=" * 60)
    print("Test 1: Basic Tax Calculation")
    print("=" * 60)
    
    result = evaluate_return(
        w2_income=100_000,
        state="CA",
        filing_status="Married/Joint",
        num_dependents=2
    )
    
    print(f"Input:")
    print(f"  W2 Income: $100,000")
    print(f"  State: California")
    print(f"  Filing Status: Married/Joint")
    print(f"  Dependents: 2")
    print(f"\nResults:")
    print(f"  Total Tax: ${result.total_tax:,.2f}")
    print(f"  Federal Tax: ${result.federal_total_tax:,.2f}")
    print(f"  State Tax: ${result.state_total_tax:,.2f}")
    print(f"  Federal Effective Tax Rate: {result.federal_effective_tax_rate:.2f}%")
    print(f"  Federal Tax Bracket: {result.federal_tax_bracket:.1f}%")
    print(f"  State Effective Tax Rate: {result.state_effective_tax_rate:.2f}%")
    print(f"  State Tax Bracket: {result.state_tax_bracket:.1f}%")
    print(f"  Federal AGI: ${result.federal_adjusted_gross_income:,.2f}")
    print(f"  Federal Taxable Income: ${result.federal_taxable_income:,.2f}")
    print("✓ Basic calculation test passed\n")
    return True


def test_different_states():
    """Test tax calculations for different states."""
    print("=" * 60)
    print("Test 2: Different States Comparison")
    print("=" * 60)
    
    states = ["CA", "NY", "MA", "TX", None]  # TX has no state tax
    income = 150_000
    
    print(f"Income: ${income:,}")
    print(f"Filing Status: Single\n")
    print(f"{'State':<10} {'Total Tax':<15} {'Federal Tax':<15} {'State Tax':<15} {'Total Rate':<12}")
    print("-" * 70)
    
    for state in states:
        result = evaluate_return(
            w2_income=income,
            state=state,
            filing_status="Single"
        )
        state_name = state if state else "No State"
        total_rate = (result.total_tax / income) * 100
        print(f"{state_name:<10} ${result.total_tax:>12,.2f} ${result.federal_total_tax:>12,.2f} "
              f"${result.state_total_tax:>12,.2f} {total_rate:>10.2f}%")
    
    print("✓ State comparison test passed\n")
    return True


def test_filing_statuses():
    """Test different filing statuses."""
    print("=" * 60)
    print("Test 3: Filing Status Comparison")
    print("=" * 60)
    
    filing_statuses = ["Single", "Married/Joint", "Head_of_House", "Married/Sep"]
    income = 100_000
    
    print(f"Income: ${income:,}")
    print(f"State: California\n")
    print(f"{'Filing Status':<20} {'Total Tax':<15} {'Federal Tax':<15} {'State Tax':<15}")
    print("-" * 70)
    
    for status in filing_statuses:
        result = evaluate_return(
            w2_income=income,
            state="CA",
            filing_status=status
        )
        print(f"{status:<20} ${result.total_tax:>12,.2f} ${result.federal_total_tax:>12,.2f} "
              f"${result.state_total_tax:>12,.2f}")
    
    print("✓ Filing status test passed\n")
    return True


def test_income_levels():
    """Test different income levels."""
    print("=" * 60)
    print("Test 4: Income Level Analysis")
    print("=" * 60)
    
    incomes = [50_000, 100_000, 150_000, 200_000, 250_000]
    
    print(f"State: California")
    print(f"Filing Status: Married/Joint")
    print(f"Dependents: 2\n")
    print(f"{'Income':<15} {'Total Tax':<15} {'Effective Rate':<15} {'Tax Bracket':<15}")
    print("-" * 65)
    
    for income in incomes:
        result = evaluate_return(
            w2_income=income,
            state="CA",
            filing_status="Married/Joint",
            num_dependents=2
        )
        effective_rate = (result.total_tax / income) * 100
        print(f"${income:>12,} ${result.total_tax:>12,.2f} {effective_rate:>13.2f}% "
              f"{result.federal_tax_bracket:>13.1f}%")
    
    print("✓ Income level test passed\n")
    return True


def test_capital_gains():
    """Test capital gains impact."""
    print("=" * 60)
    print("Test 5: Capital Gains Impact")
    print("=" * 60)
    
    w2_income = 75_000
    capital_gains_amounts = [0, 25_000, 50_000, 100_000]
    
    print(f"W2 Income: ${w2_income:,}")
    print(f"State: California")
    print(f"Filing Status: Single\n")
    print(f"{'Capital Gains':<20} {'Total Tax':<15} {'Federal Tax':<15} {'State Tax':<15}")
    print("-" * 70)
    
    for cg in capital_gains_amounts:
        result = evaluate_return(
            w2_income=w2_income,
            long_term_capital_gains=cg,
            state="CA",
            filing_status="Single"
        )
        print(f"${cg:>18,} ${result.total_tax:>12,.2f} ${result.federal_total_tax:>12,.2f} "
              f"${result.state_total_tax:>12,.2f}")
    
    print("✓ Capital gains test passed\n")
    return True


def test_batch_processing():
    """Test batch processing with evaluate_returns."""
    print("=" * 60)
    print("Test 6: Batch Processing (evaluate_returns)")
    print("=" * 60)
    
    df = evaluate_returns(
        w2_income=[75_000, 100_000, 125_000],
        state="CA",
        filing_status=["Single", "Married/Joint"],
        num_dependents=0
    )
    
    print(f"Generated {len(df)} tax scenarios\n")
    print("Sample results:")
    print(df[['w2_income', 'filing_status', 'total_tax', 'federal_total_tax', 
              'state_total_tax', 'federal_effective_tax_rate']].to_string(index=False))
    
    print("✓ Batch processing test passed\n")
    return True


def test_dependents_impact():
    """Test impact of dependents on taxes."""
    print("=" * 60)
    print("Test 7: Dependents Impact")
    print("=" * 60)
    
    income = 100_000
    dependents = [0, 1, 2, 3]
    
    print(f"Income: ${income:,}")
    print(f"State: California")
    print(f"Filing Status: Married/Joint\n")
    print(f"{'Dependents':<15} {'Total Tax':<15} {'Tax Savings':<15}")
    print("-" * 50)
    
    base_tax = None
    for num_deps in dependents:
        result = evaluate_return(
            w2_income=income,
            state="CA",
            filing_status="Married/Joint",
            num_dependents=num_deps
        )
        if base_tax is None:
            base_tax = result.total_tax
            savings = 0
        else:
            savings = base_tax - result.total_tax
        
        print(f"{num_deps:<15} ${result.total_tax:>12,.2f} ${savings:>12,.2f}")
    
    print("✓ Dependents impact test passed\n")
    return True


def test_alternative_minimum_tax():
    """Test Alternative Minimum Tax (AMT) scenario."""
    print("=" * 60)
    print("Test 8: Alternative Minimum Tax (AMT)")
    print("=" * 60)
    
    iso_gains = [0, 25_000, 50_000, 75_000, 100_000]
    
    print(f"W2 Income: $100,000")
    print(f"Filing Status: Single\n")
    print(f"{'ISO Gains':<15} {'Total Tax':<15} {'AMT':<15} {'Regular Tax':<15}")
    print("-" * 65)
    
    for iso in iso_gains:
        result = evaluate_return(
            w2_income=100_000,
            incentive_stock_option_gains=iso,
            filing_status="Single"
        )
        regular_tax = result.federal_total_tax - result.federal_amt
        print(f"${iso:>12,} ${result.federal_total_tax:>12,.2f} "
              f"${result.federal_amt:>12,.2f} ${regular_tax:>12,.2f}")
    
    print("✓ AMT test passed\n")
    return True


def test_error_handling():
    """Test error handling with invalid inputs."""
    print("=" * 60)
    print("Test 9: Error Handling")
    print("=" * 60)
    
    try:
        # Test invalid state
        try:
            evaluate_return(w2_income=100_000, state="INVALID")
            print("✗ Should have raised an error for invalid state")
            return False
        except (ValueError, Exception) as e:
            print(f"✓ Correctly caught error for invalid state: {type(e).__name__}")
        
        # Test invalid filing status
        try:
            evaluate_return(w2_income=100_000, filing_status="Invalid")
            print("✗ Should have raised an error for invalid filing status")
            return False
        except (ValueError, Exception) as e:
            print(f"✓ Correctly caught error for invalid filing status: {type(e).__name__}")
        
        print("✓ Error handling test passed\n")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TENFORTY LIBRARY TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Basic Calculation", test_basic_calculation),
        ("Different States", test_different_states),
        ("Filing Statuses", test_filing_statuses),
        ("Income Levels", test_income_levels),
        ("Capital Gains", test_capital_gains),
        ("Batch Processing", test_batch_processing),
        ("Dependents Impact", test_dependents_impact),
        ("Alternative Minimum Tax", test_alternative_minimum_tax),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} failed with error: {e}\n")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

