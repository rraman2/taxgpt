"""Debug test for Form 8812 to identify why L4 (qualifying children) is 0."""
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tenforty" / "src"))

from core import ScenarioStore
from forms import Form8812Handler

def test_form8812_inputs():
    """Test Form 8812 with inputs to see what's happening."""
    print("=" * 60)
    print("Test 1: Form 8812 Input Flow")
    print("=" * 60)
    
    store = ScenarioStore()
    scenario = store.create_scenario(year=2024)
    
    # Apply updates exactly as in run_example
    updates = [
        {'form': 'Form 1040', 'line': 'L1a', 'value': 200000},
        {'form': 'Form 1040', 'line': 'FilingStatus', 'value': 'MFJ'},
        {'form': 'Form 1040', 'line': 'DependentsTable', 'value': 2},
        {'form': 'Form 8812', 'line': 'L4a', 'value': 2},
        {'form': 'Schedule 1', 'line': 'S1_1', 'value': 1000},
        {'form': 'Schedule E', 'line': 'L26', 'value': 4000},
        {'form': 'Schedule A', 'line': 'L5a', 'value': 22000},
        {'form': 'Schedule A', 'line': 'L8', 'value': 32000},
    ]
    
    print("\n1. Applying updates to scenario...")
    store.apply_updates(scenario.scenario_id, updates)
    
    print("\n2. Checking scenario inputs:")
    for (form, line), value in scenario.inputs.items():
        if form == 'Form 8812':
            print(f"   {form} / {line} = {value}")
    
    print("\n3. Grouping inputs by form (as calculate_tax_liability does):")
    form_inputs = {}
    for (form_name, line_id), value in scenario.inputs.items():
        if form_name not in form_inputs:
            form_inputs[form_name] = {}
        form_inputs[form_name][line_id] = value
    
    print(f"   Form 8812 in form_inputs: {'Form 8812' in form_inputs}")
    if 'Form 8812' in form_inputs:
        print(f"   Form 8812 inputs: {form_inputs['Form 8812']}")
    
    print("\n4. Testing Form8812Handler directly:")
    handler = Form8812Handler()
    
    # Simulate what FormCoordinator does
    test_inputs = form_inputs.get('Form 8812', {})
    print(f"   Test inputs: {test_inputs}")
    
    # Test normalization
    normalized = handler.normalize_inputs(test_inputs)
    print(f"   Normalized inputs: {normalized}")
    
    # Test with context (simulating after Form 1040 is processed)
    context = {
        'Form 1040': {
            'L11': 205000,  # AGI
            'Status': 'Married/Joint'
        },
        'Status': 'Married/Joint'
    }
    
    print(f"\n5. Testing handler normalization and value extraction:")
    print(f"   Context Form 1040 outputs: {context.get('Form 1040', {})}")
    
    # Test normalization and value extraction without calling process (which segfaults)
    agi = context.get('Form 1040', {}).get('L11', 0)
    filing_status = context.get('Form 1040', {}).get('Status') or context.get('Status')
    
    print(f"\n   Extracted values:")
    print(f"     AGI: {agi}")
    print(f"     Filing status: {filing_status}")
    print(f"     Qualifying children (from normalized): {normalized.get('L4') or normalized.get('L4a', 0)}")
    
    # Test what form_8812_inputs would look like
    qualifying_children = normalized.get("L4") or normalized.get("L4a", 0)
    form_8812_inputs = {
        "Status": filing_status,
        "L1": float(agi) if agi else 0.0,
        "L4": int(qualifying_children) if qualifying_children else 0,
        "L13": 0.0,
        "Amnt19": 0.0,
        "L2a": 0.0,
        "L2b": 0.0,
        "L2c": 0.0,
        "L6": 0,
    }
    
    print(f"\n   Form 8812 inputs that would be passed to OTS:")
    for key, value in form_8812_inputs.items():
        print(f"     {key}: {value} (type: {type(value).__name__})")
    
    print(f"\n   ⚠ NOTE: OTS evaluation causes segfault, so manual calculation is used")
    print(f"   Manual calculation would use:")
    print(f"     - AGI: ${agi:,.0f}")
    print(f"     - Qualifying children: {qualifying_children}")
    print(f"     - Expected credit: ${qualifying_children * 2000:,.0f} (before phaseout)")


def test_form8812_normalization():
    """Test Form 8812 normalization specifically."""
    print("\n" + "=" * 60)
    print("Test 2: Form 8812 Normalization")
    print("=" * 60)
    
    handler = Form8812Handler()
    
    test_cases = [
        {"L4a": 2},
        {"L4": 2},
        {"L4a": 2, "L1": 100000},
    ]
    
    for i, inputs in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {inputs}")
        normalized = handler.normalize_inputs(inputs)
        print(f"  Normalized: {normalized}")
        l4_value = normalized.get("L4") or normalized.get("L4a", 0)
        print(f"  L4 value: {l4_value}")


def test_form8812_coordinator_paths():
    """Test which path Form 8812 takes in FormCoordinator."""
    print("\n" + "=" * 60)
    print("Test 3: Form 8812 Coordinator Paths")
    print("=" * 60)
    
    from forms import FormCoordinator
    
    coordinator = FormCoordinator()
    
    # Test case 1: Form 8812 IN form_inputs (should go through normal path)
    print("\nTest 3a: Form 8812 IN form_inputs (normal path)")
    form_inputs_with_8812 = {
        'Form 1040': {
            'Status': 'MFJ',
            'L1a': 200000,
            'Dependents': 2,
        },
        'Form 8812': {
            'L4a': 2,  # This is what comes from OpenAI
        },
    }
    
    print(f"  form_inputs keys: {list(form_inputs_with_8812.keys())}")
    print(f"  'Form 8812' in form_inputs: {'Form 8812' in form_inputs_with_8812}")
    print(f"  Form 8812 inputs: {form_inputs_with_8812.get('Form 8812', {})}")
    print(f"  → Should go through NORMAL path (line 914)")
    
    # Test case 2: Form 8812 NOT in form_inputs (should go through special handling)
    print("\nTest 3b: Form 8812 NOT in form_inputs (special handling path)")
    form_inputs_without_8812 = {
        'Form 1040': {
            'Status': 'MFJ',
            'L1a': 200000,
            'Dependents': 2,
        },
        # No Form 8812 here
    }
    
    print(f"  form_inputs keys: {list(form_inputs_without_8812.keys())}")
    print(f"  'Form 8812' in form_inputs: {'Form 8812' in form_inputs_without_8812}")
    print(f"  → Should go through SPECIAL HANDLING path (line 868)")
    empty_dict = {}
    print(f"  → Would get inputs from form_inputs.get('Form 8812', <empty>) = {empty_dict}")
    print(f"  → This would result in L4 = 0!")
    
    print("\n⚠ KEY INSIGHT:")
    print("  If Form 8812 is NOT in form_inputs, it goes through special handling")
    print("  and gets empty inputs {}, resulting in L4 = 0")
    print("  The special handling should only be used when Form 8812 needs to be")
    print("  calculated from context alone (without direct inputs)")


if __name__ == "__main__":
    print("Form 8812 Debug Tests")
    print("=" * 60)
    
    test_form8812_inputs()
    test_form8812_normalization()
    test_form8812_coordinator_paths()
    
    print("\n" + "=" * 60)
    print("Tests Complete")
    print("=" * 60)

