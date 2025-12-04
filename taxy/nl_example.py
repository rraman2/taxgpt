#!/usr/bin/env python3
"""
Example usage of the natural language interface.
"""

from nl_interface import parse_scenario, parse_modification, apply_modification
import json


def example_basic_scenario():
    """Example: Parse a basic tax scenario."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Tax Scenario")
    print("=" * 70)
    
    scenario = "Wage income of 120K and a schedule C net income of $40K"
    
    print(f"\nInput: {scenario}\n")
    
    result = parse_scenario(scenario)
    
    print("Output:")
    print(json.dumps(result, indent=2))
    print()


def example_complex_scenario():
    """Example: Parse a more complex scenario."""
    print("=" * 70)
    print("EXAMPLE 2: Complex Tax Scenario")
    print("=" * 70)
    
    scenario = """
    Married filing jointly with 2 dependent children.
    Wage income of $200,000.
    Qualifying children under age 17: 2.
    """
    
    print(f"\nInput: {scenario}\n")
    
    result = parse_scenario(scenario)
    
    print("Output:")
    print(json.dumps(result, indent=2))
    print()


def example_modification():
    """Example: Modify an existing scenario."""
    print("=" * 70)
    print("EXAMPLE 3: Scenario Modification")
    print("=" * 70)
    
    # Start with a base scenario
    base_scenario = {
        "inputs": [
            {
                "fact": "Wage income 120000",
                "form": "Form 1040",
                "line": "L1a",
                "value": 120000,
                "description": "Wages, salaries, tips"
            },
            {
                "fact": "Schedule C net income 40000",
                "form": "Schedule C",
                "line": "L31",
                "value": 40000,
                "description": "Net profit or (loss)"
            }
        ]
    }
    
    print("\nBase Scenario:")
    print(json.dumps(base_scenario, indent=2))
    
    # Modify it
    modification_text = "Change wage income to 150K and remove the schedule C income"
    
    print(f"\nModification: {modification_text}\n")
    
    modification = parse_modification(modification_text, base_scenario)
    
    print("Modification Output:")
    print(json.dumps(modification, indent=2))
    
    # Apply modification
    updated = apply_modification(base_scenario, modification)
    
    print("\nUpdated Scenario:")
    print(json.dumps(updated, indent=2))
    print()


if __name__ == "__main__":
    try:
        example_basic_scenario()
        print("\n")
        example_complex_scenario()
        print("\n")
        example_modification()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

