#!/usr/bin/env python3
"""
Simple CLI for natural language tax scenario interface.

Usage:
    python3 run_nl.py "Wage income of $120K and schedule C net income of $40K"
    python3 run_nl.py --interactive
"""

import sys
import json
from core import ScenarioStore
from nl_interface import parse_scenario


def print_summary(summary):
    """Print a formatted tax summary."""
    print("\n" + "=" * 70)
    print("TAX CALCULATION SUMMARY")
    print("=" * 70)
    print(f"\nYear: {summary['year']}")
    print(f"\nInputs Applied:")
    for form_name, inputs in summary['inputs'].items():
        print(f"  {form_name}:")
        for line, value in inputs.items():
            print(f"    {line}: {value}")
    
    print(f"\nFederal Tax Results:")
    federal = summary['federal']
    print(f"  AGI (Adjusted Gross Income): ${federal.get('AGI', 0):,.2f}")
    print(f"  Taxable Income: ${federal.get('taxable_income', 0):,.2f}")
    print(f"  Total Tax: ${federal.get('total_tax', 0):,.2f}")
    print(f"  Child Tax Credit: ${federal.get('child_tax_credit', 0):,.2f}")
    print()


def run_interactive():
    """Run in interactive mode."""
    print("=" * 70)
    print("TAXY - Natural Language Tax Scenario Interface")
    print("=" * 70)
    print("\nEnter tax scenarios in natural language.")
    print("Commands:")
    print("  'quit' or 'exit' - Exit")
    print("  'modify <description>' or 'change <description>' - Modify current scenario")
    print("  'restore' or 'undo' - Restore to previous state")
    print("  'show' - Show current scenario inputs")
    print()
    
    store = ScenarioStore()
    current_scenario = None
    original_scenario_state = None  # Store original state for restoration
    
    while True:
        try:
            user_input = input("Tax scenario> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if user_input.lower() in ['restore', 'undo', 'reset']:
                if current_scenario is None:
                    print("Error: No scenario to restore.")
                    continue
                
                try:
                    store.restore_scenario(current_scenario.scenario_id, -1)
                    current_scenario = store.get_scenario(current_scenario.scenario_id)
                    print(f"✓ Scenario restored to previous state: {current_scenario.scenario_id}")
                    
                    # Recalculate
                    summary = store.calculate_tax_liability(current_scenario.scenario_id)
                    print_summary(summary)
                except ValueError as e:
                    print(f"Error: {e}")
                continue
            
            if user_input.lower() in ['show', 'display', 'list']:
                if current_scenario is None:
                    print("Error: No scenario to show.")
                    continue
                
                print(f"\nCurrent scenario: {current_scenario.scenario_id}")
                print(f"  Year: {current_scenario.year}")
                print(f"  History states: {len(current_scenario.history)}")
                print(f"  Current inputs:")
                for (form, line), value in current_scenario.inputs.items():
                    print(f"    {form} / {line} = {value}")
                print()
                continue
            
            # Check if this looks like a modification (starts with "change", "modify", "update", "set", etc.)
            is_modification = (
                user_input.lower().startswith('modify ') or
                user_input.lower().startswith('change ') or
                user_input.lower().startswith('update ') or
                user_input.lower().startswith('set ') or
                user_input.lower().startswith('remove ') or
                user_input.lower().startswith('add ')
            )
            
            if is_modification:
                if current_scenario is None:
                    print("Error: No scenario to modify. Create one first.")
                    continue
                
                # Extract modification text
                if user_input.lower().startswith('modify '):
                    modification_text = user_input[7:].strip()
                elif user_input.lower().startswith('change '):
                    modification_text = user_input[7:].strip()
                elif user_input.lower().startswith('update '):
                    modification_text = user_input[7:].strip()
                elif user_input.lower().startswith('set '):
                    modification_text = user_input[4:].strip()
                elif user_input.lower().startswith('remove '):
                    modification_text = f"Remove {user_input[7:].strip()}"
                elif user_input.lower().startswith('add '):
                    modification_text = f"Add {user_input[4:].strip()}"
                else:
                    modification_text = user_input
                
                print(f"\nModifying scenario: {modification_text}")
                
                store.apply_updates(
                    current_scenario.scenario_id,
                    [],
                    nl_modification=modification_text
                )
                
                current_scenario = store.get_scenario(current_scenario.scenario_id)
                print(f"✓ Scenario updated: {current_scenario.scenario_id}")
                
                # Recalculate
                summary = store.calculate_tax_liability(current_scenario.scenario_id)
                print_summary(summary)
                continue
            
            # Parse new scenario
            print(f"\nParsing scenario: {user_input}")
            
            scenario = store.create_scenario(
                year=2024,
                nl_description=user_input
            )
            
            current_scenario = scenario
            # Store original state for potential restoration
            original_scenario_state = dict(scenario.inputs)
            
            print(f"✓ Scenario created: {scenario.scenario_id}")
            print(f"  Parsed {len(scenario.inputs)} input fields")
            
            # Show parsed inputs
            print("\nParsed inputs:")
            for (form, line), value in scenario.inputs.items():
                print(f"  {form} / {line} = {value}")
            
            # Calculate tax
            print("\nCalculating tax liability...")
            summary = store.calculate_tax_liability(scenario.scenario_id)
            print_summary(summary)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            print()


def run_single(scenario_text):
    """Run with a single scenario text."""
    print("=" * 70)
    print("TAXY - Natural Language Tax Scenario")
    print("=" * 70)
    print(f"\nScenario: {scenario_text}\n")
    
    store = ScenarioStore()
    
    # Create scenario
    scenario = store.create_scenario(
        year=2024,
        nl_description=scenario_text
    )
    
    print(f"✓ Scenario created: {scenario.scenario_id}")
    print(f"  Parsed {len(scenario.inputs)} input fields\n")
    
    # Show parsed inputs
    print("Parsed inputs:")
    for (form, line), value in scenario.inputs.items():
        print(f"  {form} / {line} = {value}")
    
    # Calculate tax
    print("\nCalculating tax liability...")
    summary = store.calculate_tax_liability(scenario.scenario_id)
    print_summary(summary)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--interactive', '-i']:
            run_interactive()
        elif sys.argv[1] in ['--help', '-h']:
            print(__doc__)
        else:
            # Single scenario from command line
            scenario_text = " ".join(sys.argv[1:])
            run_single(scenario_text)
    else:
        # No arguments - run interactive
        run_interactive()


if __name__ == "__main__":
    main()

