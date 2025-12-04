#!/usr/bin/env python3
"""
Taxy core: thin scenario engine around tenforty using `{form, line, value}` inputs.

Design:
- OpenAI maps NL → {form, line, value} triples (e.g. "Form 1040" / "L1a", "Schedule C" / "L31").
- This module:
  - Stores scenarios (year + list of inputs),
  - Translates those triples into tenforty line-level inputs,
  - Calls `evaluate_form` / `evaluate_return` as needed,
  - Respects IRS flow conceptually (Schedule C → Schedule 1 → 1040).

Scope (first iteration):
- Support core 1040 wages (L1a) and Schedule C net income (Schedule C L31 flowing into Schedule 1 → 1040).
- Make it easy to extend to more forms/lines later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path
import itertools
import uuid
import sys

# Wire tenforty into path (reuse the pattern used in examples)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TENFORTY_SRC = PROJECT_ROOT / "tenforty" / "src"
TENFORTY_VENV = PROJECT_ROOT / "tenforty" / "venv"

if TENFORTY_VENV.exists():
    lib_dir = TENFORTY_VENV / "lib"
    if lib_dir.exists():
        python_dirs = [
            d for d in lib_dir.iterdir() if d.is_dir() and d.name.startswith("python")
        ]
        if python_dirs:
            venv_site_packages = python_dirs[0] / "site-packages"
            if venv_site_packages.exists() and str(venv_site_packages) not in sys.path:
                sys.path.insert(0, str(venv_site_packages))

if TENFORTY_SRC.exists() and str(TENFORTY_SRC) not in sys.path:
    sys.path.insert(0, str(TENFORTY_SRC))

from tenforty.core import evaluate_form  # type: ignore  # noqa: E402

# Import forms - handle both package and direct execution
try:
    from taxy.forms import FormCoordinator  # type: ignore  # noqa: E402
except ImportError:
    # When running directly from taxy/ directory
    from forms import FormCoordinator  # type: ignore  # noqa: E402

# Import NL interface - handle both package and direct execution
try:
    from taxy.nl_interface import parse_scenario, parse_modification  # type: ignore  # noqa: E402
except ImportError:
    # When running directly from taxy/ directory
    from nl_interface import parse_scenario, parse_modification  # type: ignore  # noqa: E402


FormLine = Tuple[str, str]  # (form_name, line_id), e.g. ("Form 1040", "L1a")


@dataclass
class Scenario:
    """Represents a single tax scenario."""

    scenario_id: str
    year: int
    # Raw inputs as provided by the agent: (form, line) -> value (number or string)
    inputs: Dict[FormLine, Any] = field(default_factory=dict)
    # History of input states for restoration
    history: List[Dict[FormLine, Any]] = field(default_factory=list)
    # Original natural language description (for display/editing)
    description: str = ""


class ScenarioStore:
    """In-memory store for scenarios."""

    def __init__(self) -> None:
        self._scenarios: Dict[str, Scenario] = {}
        self._coordinator = FormCoordinator()

    # ---- Scenario lifecycle -------------------------------------------------

    def create_scenario(self, year: int, nl_description: Optional[str] = None) -> Scenario:
        """
        Create a new scenario.
        
        Args:
            year: Tax year
            nl_description: Optional natural language description to parse into inputs
        """
        scenario_id = str(uuid.uuid4())
        scenario = Scenario(scenario_id=scenario_id, year=year, description=nl_description or "")
        
        # If natural language description provided, parse it
        if nl_description:
            try:
                parsed = parse_scenario(nl_description)
                
                # Print parsed inputs for debugging
                print("\n" + "=" * 70)
                print("PARSED INPUTS FROM OPENAI:")
                print("=" * 70)
                for inp in parsed.get("inputs", []):
                    print(f"  {inp.get('form')} / {inp.get('line')}: {inp.get('value')} ({inp.get('fact', 'N/A')})")
                print("=" * 70 + "\n")
                
                # Apply parsed inputs to scenario
                # Also store the original OpenAI inputs for QBI detection
                openai_inputs = []
                
                print(f"  DEBUG: Starting to process {len(parsed.get('inputs', []))} parsed inputs")
                
                # First pass: collect all L1a values to sum them
                l1a_values = []
                other_inputs = []
                for inp in parsed.get("inputs", []):
                    form_name = inp.get("form", "")
                    line_id = inp.get("line", "")
                    value = inp.get("value")
                    print(f"  DEBUG: Processing input: {form_name} / {line_id} = {value}")
                    
                    # Collect L1a values separately for summing
                    if form_name == "Form 1040" and line_id == "L1a" and isinstance(value, (int, float)):
                        l1a_values.append(value)
                        print(f"  DEBUG: Found L1a value: ${value:,.0f} (total L1a values so far: {len(l1a_values)})")
                    else:
                        other_inputs.append(inp)
                
                print(f"  DEBUG: Collected {len(l1a_values)} L1a values: {l1a_values}")
                
                # Sum all L1a values
                if l1a_values:
                    total_l1a = sum(l1a_values)
                    print(f"  NOTE: Summing {len(l1a_values)} L1a values: {[f'${v:,.0f}' for v in l1a_values]} = ${total_l1a:,.0f}")
                    scenario.inputs[("Form 1040", "L1a")] = total_l1a
                    print(f"  DEBUG: Set scenario.inputs[('Form 1040', 'L1a')] = ${total_l1a:,.0f}")
                    # Verify it was set
                    verify_value = scenario.inputs.get(("Form 1040", "L1a"))
                    print(f"  DEBUG: Verified scenario.inputs[('Form 1040', 'L1a')] = ${verify_value:,.0f}")
                else:
                    print(f"  DEBUG: No L1a values found to sum")
                
                # Process other inputs
                for inp in other_inputs:
                    form_name = inp["form"]
                    line_id = inp["line"]
                    value = inp["value"]
                    # Skip clearly derived or non-numeric downstream fields that
                    # should be computed by OTS (e.g., QBI deduction on 1040 L13).
                    # OpenAI sometimes returns a symbolic value like "QBI Deduction"
                    # for Form 1040 L13; we must ignore that and let Form 8995/OTS
                    # compute the numeric deduction instead.
                    if (
                        form_name == "Form 1040"
                        and line_id == "L13"
                        and isinstance(value, str)
                    ):
                        print(
                            "  NOTE: Ignoring non-numeric Form 1040 L13 value from OpenAI "
                            f"({value!r}); QBI deduction will be computed via Form 8995/OTS."
                        )
                    else:
                        scenario.inputs[(form_name, line_id)] = value
                    # Store original OpenAI input for QBI detection
                    openai_inputs.append(inp)
                
                # Also add L1a inputs to openai_inputs for tracking
                for inp in parsed.get("inputs", []):
                    if inp["form"] == "Form 1040" and inp["line"] == "L1a":
                        openai_inputs.append(inp)
                # Store OpenAI inputs on the scenario so FormCoordinator/ScheduleCHandler
                # can later inspect facts/descriptions for QBI classification.
                # This is intentionally out-of-model; it's just extra metadata.
                setattr(scenario, "_openai_inputs", openai_inputs)
            except Exception as e:
                raise ValueError(f"Failed to parse natural language description: {e}")
        
        # Store initial state in history
        scenario.history.append(dict(scenario.inputs))
        
        self._scenarios[scenario_id] = scenario
        return scenario

    def clone_scenario(self, source_scenario_id: str) -> Scenario:
        source = self._require_scenario(source_scenario_id)
        scenario_id = str(uuid.uuid4())
        clone = Scenario(
            scenario_id=scenario_id,
            year=source.year,
            inputs=dict(source.inputs),
            history=[dict(source.inputs)],  # Start with current state as history
            description=source.description,  # Copy the description text
        )
        self._scenarios[scenario_id] = clone
        return clone
    
    def restore_scenario(self, scenario_id: str, history_index: int = -1) -> Scenario:
        """
        Restore a scenario to a previous state from history.
        
        Args:
            scenario_id: The scenario to restore
            history_index: Index in history (-1 = previous state, -2 = two states ago, etc.)
        """
        scenario = self._require_scenario(scenario_id)
        
        if not scenario.history:
            raise ValueError("No history available for this scenario")
        
        if abs(history_index) > len(scenario.history):
            raise ValueError(f"History index {history_index} out of range (available: {len(scenario.history)} states)")
        
        # Restore from history
        scenario.inputs = dict(scenario.history[history_index])
        return scenario

    def get_scenario(self, scenario_id: str) -> Scenario:
        return self._require_scenario(scenario_id)

    def _require_scenario(self, scenario_id: str) -> Scenario:
        if scenario_id not in self._scenarios:
            raise KeyError(f"Unknown scenario_id: {scenario_id}")
        return self._scenarios[scenario_id]

    # ---- Updates ------------------------------------------------------------

    def apply_updates(self, scenario_id: str, updates: List[Dict[str, Any]], nl_modification: Optional[str] = None, description: Optional[str] = None) -> None:
        """
        Apply `{form, line, value}` updates to a scenario.

        Each update should look like:
            { "form": "Form 1040", "line": "L1a", "value": 120000 }
        or:
            { "form": "Schedule C", "line": "L31", "value": 40000 }
        
        Args:
            scenario_id: The scenario to update
            updates: List of {form, line, value} dicts
            nl_modification: Optional natural language modification to parse and apply
            description: Optional description text to store (without parsing)
        """
        scenario = self._require_scenario(scenario_id)
        
        # Update description if provided (store as-is, don't parse yet)
        if description is not None:
            scenario.description = description
        
        # If natural language modification provided, parse it first
        if nl_modification:
            try:
                # Get current scenario as dict for context
                # Include more descriptive facts for better context
                current_scenario = {
                    "inputs": [
                        {
                            "fact": self._format_fact(form, line, value),
                            "form": form,
                            "line": line,
                            "value": value,
                        }
                        for (form, line), value in scenario.inputs.items()
                    ]
                }
                
                parsed_mod = parse_modification(nl_modification, current_scenario)
                
                # Convert parsed modification to updates format
                for inp in parsed_mod.get("inputs", []):
                    updates.append({
                        "form": inp["form"],
                        "line": inp["line"],
                        "value": inp["value"],
                    })
            except Exception as e:
                raise ValueError(f"Failed to parse natural language modification: {e}")

        # Store current state in history before applying updates
        scenario.history.append(dict(scenario.inputs))
        
        for upd in updates:
            form = upd.get("form")
            line = upd.get("line")
            value = upd.get("value")

            if not isinstance(form, str) or not isinstance(line, str):
                raise ValueError(f"Invalid update (form/line must be strings): {upd}")

            # Allow numbers and strings (e.g., filing_status, state codes)
            if not isinstance(value, (int, float, str)):
                raise ValueError(
                    f"Invalid update value (must be number or string): {upd}"
                )

            # Skip clearly derived or non-numeric downstream fields that
            # should be computed by OTS (e.g., QBI deduction on 1040 L13).
            # OpenAI sometimes returns a symbolic value like "QBI Deduction"
            # for Form 1040 L13; we must ignore that and let Form 8995/OTS
            # compute the numeric deduction instead.
            if (
                form == "Form 1040"
                and line == "L13"
                and isinstance(value, str)
            ):
                print(
                    "  NOTE: Ignoring non-numeric Form 1040 L13 value from OpenAI "
                    f"({value!r}); QBI deduction will be computed via Form 8995/OTS."
                )
                continue

            key: FormLine = (form.strip(), line.strip())
            
            # Special handling: Sum L1a values when multiple are provided
            # (e.g., regular wages + S-Corp wages)
            if form == "Form 1040" and line == "L1a":
                existing_value = scenario.inputs.get(key, 0)
                if isinstance(existing_value, (int, float)) and isinstance(value, (int, float)):
                    scenario.inputs[key] = existing_value + value
                    print(f"  NOTE: Summing L1a values: ${existing_value:,.0f} + ${value:,.0f} = ${existing_value + value:,.0f}")
                else:
                    # If value is explicitly None or empty string for removal, delete the key
                    if value is None or (isinstance(value, str) and value.lower() in ['none', 'null', 'remove', 'delete', '']):
                        scenario.inputs.pop(key, None)
                    else:
                        scenario.inputs[key] = value
            else:
                # If value is explicitly None or empty string for removal, delete the key
                if value is None or (isinstance(value, str) and value.lower() in ['none', 'null', 'remove', 'delete', '']):
                    scenario.inputs.pop(key, None)
                else:
                    scenario.inputs[key] = value
    
    def _format_fact(self, form: str, line: str, value: Any) -> str:
        """Format a fact description for context in modifications."""
        # Create human-readable descriptions
        if form == "Form 1040":
            if line in ["FilingStatus", "Status"]:
                return f"Filing status: {value}"
            elif line in ["DependentsTable", "Dependents"]:
                return f"Dependents: {value}"
            elif line == "L1a":
                if isinstance(value, (int, float)):
                    return f"Wage income: ${value:,.0f}"
                else:
                    return f"Wage income: {value}"
            else:
                return f"{form} {line}: {value}"
        elif form == "Schedule C":
            if line == "L31":
                if isinstance(value, (int, float)):
                    return f"Schedule C net income: ${value:,.0f}"
                else:
                    return f"Schedule C net income: {value}"
            else:
                return f"{form} {line}: {value}"
        elif form == "Schedule E":
            if line == "L26":
                if isinstance(value, (int, float)):
                    return f"Schedule E net rental income: ${value:,.0f}"
                else:
                    return f"Schedule E net rental income: {value}"
            else:
                return f"{form} {line}: {value}"
        elif form == "Schedule A":
            if line in ["L5a", "L5"]:
                if isinstance(value, (int, float)):
                    return f"Schedule A property tax: ${value:,.0f}"
                else:
                    return f"Schedule A property tax: {value}"
            elif line in ["L8", "L8a"]:
                if isinstance(value, (int, float)):
                    return f"Schedule A mortgage interest: ${value:,.0f}"
                else:
                    return f"Schedule A mortgage interest: {value}"
            elif line == "L19":
                if isinstance(value, (int, float)):
                    return f"Schedule A total itemized deductions: ${value:,.0f}"
                else:
                    return f"Schedule A total itemized deductions: {value}"
            else:
                return f"{form} {line}: {value}"
        elif form == "Form 8812":
            if line in ["L4", "L4a"]:
                return f"Qualifying children under 17: {value}"
            else:
                return f"{form} {line}: {value}"
        else:
            return f"{form} {line}: {value}"

    # ---- Calculation --------------------------------------------------------

    def calculate_tax_liability(self, scenario_id: str) -> Dict[str, Any]:
        """
        Calculate taxes for a scenario using tenforty.

        First iteration:
        - Supports:
          - Form 1040, Line L1a (wages)
          - Schedule C, Line L31 (net profit/loss)
        - Treats Schedule C L31 as business income flowing into Schedule 1, then 1040.
          (We reflect this as S1_3 on the US_1040 form, which tenforty understands.)
        """
        scenario = self._require_scenario(scenario_id)
        year = scenario.year

        # Group inputs by form name
        form_inputs: Dict[str, Dict[str, Any]] = {}

        # Debug: Show all scenario.inputs before grouping
        print(f"  DEBUG: scenario.inputs contains {len(scenario.inputs)} entries")
        for (form_name, line_id), value in list(scenario.inputs.items())[:5]:  # Show first 5
            print(f"    {form_name} / {line_id} = {value}")

        for (form_name, line_id), value in scenario.inputs.items():
            if form_name not in form_inputs:
                form_inputs[form_name] = {}
            # Debug: Check if L1a is being set correctly
            if form_name == "Form 1040" and line_id == "L1a":
                print(f"  DEBUG: Grouping L1a from scenario.inputs: ${value:,.0f}")
            form_inputs[form_name][line_id] = value
        
        # Debug: Show final form_inputs for Form 1040
        if "Form 1040" in form_inputs and "L1a" in form_inputs["Form 1040"]:
            print(f"  DEBUG: Final form_inputs['Form 1040']['L1a'] = ${form_inputs['Form 1040']['L1a']:,.0f}")

        # Ensure Form 8995 is present so its handler runs even if there are
        # no direct user inputs for that form. It relies on context
        # (Schedule C + Form 1040 outputs) to compute QBI.
        if "Form 8995" not in form_inputs:
            form_inputs["Form 8995"] = {}

        # Pass OpenAI inputs to FormCoordinator for QBI detection
        # Get OpenAI inputs from scenario if available
        openai_inputs = getattr(scenario, '_openai_inputs', [])
        if openai_inputs:
            form_inputs["_all_inputs"] = openai_inputs

        # Use FormCoordinator to process all forms in IRS flow order
        coordinator_result = self._coordinator.process_scenario(year, form_inputs)

        final_outputs = coordinator_result["final"]

        # Get Self Employment Tax from Schedule SE or Form 1040 Schedule 2 (for display only)
        # OTS calculates L24 = L22 + L23, where L23 includes Schedule 2 (S2_4 = SE tax)
        se_tax = 0
        schedule_se_results = coordinator_result["results"].get("Schedule SE", {})
        if schedule_se_results:
            se_tax = schedule_se_results.get("outputs", {}).get("L12", 0)
        
        # If not found in Schedule SE, try Form 1040 Schedule 2 (S2_4)
        if se_tax == 0:
            se_tax = final_outputs.get("S2_4", 0)
        
        # Get regular tax (L22) - OTS calculates this as L18 - L21 (tax after credits)
        regular_tax = final_outputs.get("L22", 0)
        
        # Total Tax (L24) - OTS calculates this as L22 + L23
        # According to OTS: L22 = L18 - L21 (tax after credits), L24 = L22 + L23
        # So L24 already has credits applied to the regular tax portion
        # We trust OTS to calculate this correctly - it should already include credits
        total_tax = final_outputs.get("L24", 0)
        
        # Build summary from coordinator results
        summary = {
            "year": year,
            "inputs": {
                form_name: form_inputs.get(form_name, {})
                for form_name in form_inputs.keys()
            },
            "federal": {
                "AGI": final_outputs.get("L11"),
                "taxable_income": final_outputs.get("L15"),
                "tax": regular_tax,  # Regular tax (L22 or L24 - S2_4)
                "self_employment_tax": se_tax,  # Self Employment Tax (Schedule SE L12 or S2_4)
                "total_tax": final_outputs.get("L24"),  # Total Tax (L24, includes SE tax, credits already applied via L22)
                "child_tax_credit": final_outputs.get("L19") or coordinator_result["results"].get("Form 1040", {}).get("outputs", {}).get("L19", 0),  # L19 is the child tax credit (check both final_outputs and Form 1040 results)
                "total_payments": final_outputs.get("L33", 0),  # Line 33: Total Payments (calculated by OTS)
                "tax_due": final_outputs.get("L37", 0),  # Line 37: Tax Due (calculated by OTS when L33 < L24)
                "estimated_tax_penalty": final_outputs.get("L38", 0),  # Line 38: Estimated Tax Underpayment Penalty
            },
            "federal_raw": final_outputs,
            "form_results": coordinator_result["results"],
        }

        return summary


# ---- Convenience function for direct use ------------------------------------

def run_example() -> None:
    """
    Test with OpenAI JSON output format.
    This simulates the real scenario where OpenAI produces this JSON structure.
    """
    import json

    # OpenAI output format (exactly as it would come from the API)
    openai_output = {
        "inputs": [
            {
                "fact": "Wage income 120000",
                "form": "Form 1040",
                "line": "L1a",
                "value": 200000,
                "description": "Wages, salaries, tips"
            },
            {
                "fact": "Married Filing Jointly",
                "form": "Form 1040",
                "line": "FilingStatus",
                "value": "MFJ",
                "description": "Filing status: Married filing jointly"
            },
            {
                "fact": "Dependent child count",
                "form": "Form 1040",
                "line": "DependentsTable",
                "value": 2,
                "description": "Number of dependents entered on Form 1040 dependent section"
            },
            {
                "fact": "Qualifying children under age 17",
                "form": "Form 8812",
                "line": "L4a",
                "value": 2,
                "description": "Number of qualifying children under age 17 for the Child Tax Credit"
            },
            {
                "fact": "Taxable interest income",
                "form": "Schedule 1",
                "line": "S1_1",
                "value": 1000,
                "description": "Taxable interest income"
            },
            {
                "fact": "Rental income",
                "form": "Schedule E",
                "line": "L26",
                "value": 4000,
                "description": "Net rental income"
            },
            {
                "fact": "Property tax",
                "form": "Schedule A",
                "line": "L5a",
                "value": 22000,
                "description": "State and local property taxes"
            },
            {
                "fact": "Mortgage interest",
                "form": "Schedule A",
                "line": "L8",
                "value": 32000,
                "description": "Home mortgage interest"
            }
        ]
    }

    print("=" * 70)
    print("TAXY - OPENAI OUTPUT TEST")
    print("=" * 70)
    print("\nOpenAI Output (JSON):")
    print(json.dumps(openai_output, indent=2))

    # Create scenario and apply updates
    store = ScenarioStore()
    scenario = store.create_scenario(year=2024)

    # Extract updates from OpenAI format: convert to our internal format
    updates = []
    for input_item in openai_output["inputs"]:
        updates.append({
            "form": input_item["form"],
            "line": input_item["line"],
            "value": input_item["value"],
        })

    print("\n" + "-" * 70)
    print("Applying updates...")
    print("-" * 70)
    for update in updates:
        print(f"  {update['form']} / {update['line']} = {update['value']}")

    store.apply_updates(scenario.scenario_id, updates)

    print("\n" + "-" * 70)
    print("Calculating tax liability...")
    print("-" * 70)

    try:
        summary = store.calculate_tax_liability(scenario.scenario_id)
    except Exception as e:
        print(f"\nERROR during tax calculation: {e}")
        import traceback
        traceback.print_exc()
        return

    # Show which forms were processed
    print("\nForms Processed (in IRS flow order):")
    form_results = summary.get('form_results', {})
    for form_name in ["Schedule C", "Schedule 1", "Form 1040", "Form 8812"]:
        if form_name in form_results:
            print(f"  ✓ {form_name}")
        elif form_name in summary.get('inputs', {}):
            print(f"  ✓ {form_name} (inputs only, no separate processing)")

    print("\n" + "=" * 70)
    print("INPUTS (after normalization):")
    print("=" * 70)
    for form_name, form_inputs in summary['inputs'].items():
        print(f"\n{form_name}:")
        for line, value in sorted(form_inputs.items()):
            print(f"  {line}: {value}")

    print("\n" + "=" * 70)
    print("OUTPUTS (Federal):")
    print("=" * 70)
    federal = summary['federal']
    print(f"  AGI (L11):                   {federal.get('AGI', 'N/A')}")
    print(f"  Taxable income (L15):        {federal.get('taxable_income', 'N/A')}")
    print(f"  Total tax (L24):             {federal.get('total_tax', 'N/A')}")
    if federal.get('child_tax_credit'):
        print(f"  Child tax credit (L25a):      {federal.get('child_tax_credit', 0)}")

    print("\n" + "=" * 70)
    print("READY FOR PROCONNECT COMPARISON")
    print("=" * 70)
    print(f"\nCompare these values with ProConnect:")
    print(f"  Total Tax (L24): {federal.get('total_tax', 'N/A')}")
    if federal.get('child_tax_credit'):
        print(f"  Child Tax Credit (L25a): {federal.get('child_tax_credit', 0)}")


if __name__ == "__main__":
    run_example()


