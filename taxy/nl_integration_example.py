#!/usr/bin/env python3
"""
Example: Using natural language interface with the core tax system.
"""

from core import ScenarioStore
from nl_interface import parse_scenario
import json


def example_nl_scenario():
    """Example: Create a scenario from natural language."""
    print("=" * 70)
    print("EXAMPLE: Natural Language Scenario Creation")
    print("=" * 70)
    
    store = ScenarioStore()
    
    # Create scenario from natural language
    scenario_text = """
    Married filing jointly with 2 dependent children.
    Wage income of $200,000.
    Qualifying children under age 17: 2.
    """
    
    print(f"\nCreating scenario from natural language:")
    print(f"{scenario_text}\n")
    
    scenario = store.create_scenario(
        year=2024,
        nl_description=scenario_text
    )
    
    print(f"Created scenario: {scenario.scenario_id}")
    print(f"  Year: {scenario.year}")
    print(f"  Inputs: {len(scenario.inputs)} fields")
    
    # Calculate tax liability
    print("\n" + "=" * 70)
    print("Calculating tax liability...")
    print("=" * 70)
    
    summary = store.calculate_tax_liability(scenario.scenario_id)
    
    print("\nTax Summary:")
    print(f"  AGI: ${summary['federal']['AGI']:,.2f}")
    print(f"  Taxable Income: ${summary['federal']['taxable_income']:,.2f}")
    print(f"  Total Tax: ${summary['federal']['total_tax']:,.2f}")
    print(f"  Child Tax Credit: ${summary['federal']['child_tax_credit']:,.2f}")


def example_nl_modification():
    """Example: Modify a scenario using natural language."""
    print("\n" + "=" * 70)
    print("EXAMPLE: Natural Language Modification")
    print("=" * 70)
    
    store = ScenarioStore()
    
    # Create initial scenario
    initial = store.create_scenario(
        year=2024,
        nl_description="Wage income of $120,000. Schedule C net income of $40,000."
    )
    
    print(f"\nInitial scenario: {initial.scenario_id}")
    print(f"  Inputs: {len(initial.inputs)} fields")
    
    # Modify using natural language
    modification = "Change wage income to $150,000 and remove the schedule C income"
    
    print(f"\nModification: {modification}\n")
    
    store.apply_updates(initial.scenario_id, [], nl_modification=modification)
    
    updated = store.get_scenario(initial.scenario_id)
    
    print(f"Updated scenario: {updated.scenario_id}")
    print(f"  Inputs: {len(updated.inputs)} fields")
    
    # Calculate tax
    print("\n" + "=" * 70)
    print("Calculating tax liability...")
    print("=" * 70)
    
    summary = store.calculate_tax_liability(initial.scenario_id)
    
    print("\nTax Summary:")
    print(f"  AGI: ${summary['federal']['AGI']:,.2f}")
    print(f"  Taxable Income: ${summary['federal']['taxable_income']:,.2f}")
    print(f"  Total Tax: ${summary['federal']['total_tax']:,.2f}")


if __name__ == "__main__":
    try:
        example_nl_scenario()
        example_nl_modification()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

