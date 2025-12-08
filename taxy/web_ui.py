#!/usr/bin/env python3
"""
Web UI server for Taxy - Natural Language Tax Scenario Interface

Run with: python3 web_ui.py
Then open http://localhost:5000 in your browser
"""

import json
import sys
from pathlib import Path

try:
    from flask import Flask, render_template, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("Error: Flask not installed. Install with:")
    print("  pip3 install flask flask-cors")
    sys.exit(1)

# Add taxy directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core import ScenarioStore

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Global store (in production, use a database or session storage)
store = ScenarioStore()


@app.route('/')
def index():
    """Serve the main UI page."""
    return render_template('index.html')


@app.route('/api/scenarios', methods=['GET'])
def list_scenarios():
    """List all scenarios."""
    scenarios = []
    scenario_ids = list(store._scenarios.keys())
    
    for idx, scenario_id in enumerate(scenario_ids):
        scenario = store._scenarios[scenario_id]
        scenarios.append({
            'id': scenario_id,
            'year': scenario.year,
            'inputs': {
                f"{form} / {line}": value
                for (form, line), value in scenario.inputs.items()
            },
            'history_count': len(scenario.history),
            'is_baseline': idx == 0,  # First scenario is baseline
            'description': scenario.description,  # Include description text
        })
    return jsonify({'scenarios': scenarios})


@app.route('/api/scenarios', methods=['POST'])
def create_scenario():
    """Create a new scenario from natural language."""
    data = request.json
    nl_description = data.get('description', '')
    year = data.get('year', 2024)
    clone_from = data.get('clone_from', None)  # ID of scenario to clone from
    
    try:
        # If this is the first scenario, create it as baseline
        is_first = len(store._scenarios) == 0
        
        # If clone_from is specified, clone that scenario first
        if clone_from:
            try:
                source = store.get_scenario(clone_from)
                scenario = store.clone_scenario(clone_from)
                
                # If there's a modification description, update the description text
                # (but don't parse it yet - parsing happens on Calculate)
                if nl_description:
                    scenario.description = nl_description
                # If no description provided, keep the cloned description
            except KeyError:
                return jsonify({
                    'success': False,
                    'error': f'Source scenario {clone_from} not found'
                }), 404
        elif is_first:
            # First scenario - create as baseline
            if not nl_description:
                return jsonify({
                    'success': False,
                    'error': 'Description is required for baseline scenario'
                }), 400
            scenario = store.create_scenario(year=year, nl_description=nl_description)
        else:
            # Not first scenario and no clone_from - clone the baseline (first scenario)
            baseline_id = list(store._scenarios.keys())[0]  # First scenario is baseline
            scenario = store.clone_scenario(baseline_id)
            
            # If there's a modification description, update it
            # If empty, keep the cloned baseline description
            if nl_description and nl_description.strip():
                scenario.description = nl_description
            # Otherwise, keep the cloned baseline description
        
        return jsonify({
            'success': True,
            'scenario': {
                'id': scenario.scenario_id,
                'year': scenario.year,
                'inputs': {
                    f"{form} / {line}": value
                    for (form, line), value in scenario.inputs.items()
                },
                'description': scenario.description,
            },
            'is_baseline': is_first
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/scenarios/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    """Get a specific scenario."""
    try:
        scenario = store.get_scenario(scenario_id)
        return jsonify({
            'id': scenario.scenario_id,
            'year': scenario.year,
            'inputs': {
                f"{form} / {line}": value
                for (form, line), value in scenario.inputs.items()
            },
            'history_count': len(scenario.history),
            'description': scenario.description,
        })
    except KeyError:
        return jsonify({'error': 'Scenario not found'}), 404


@app.route('/api/scenarios/<scenario_id>', methods=['PUT'])
def update_scenario(scenario_id):
    """Update a scenario with natural language modification."""
    data = request.json
    nl_modification = data.get('modification', '')
    
    try:
        if not nl_modification:
            return jsonify({
                'success': False,
                'error': 'Modification description is required'
            }), 400
        
        store.apply_updates(scenario_id, [], nl_modification=nl_modification)
        scenario = store.get_scenario(scenario_id)
        
        return jsonify({
            'success': True,
            'scenario': {
                'id': scenario.scenario_id,
                'year': scenario.year,
                'inputs': {
                    f"{form} / {line}": value
                    for (form, line), value in scenario.inputs.items()
                },
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/scenarios/<scenario_id>/calculate', methods=['POST'])
def calculate_tax(scenario_id):
    """Calculate tax liability for a scenario."""
    data = request.json or {}
    description = data.get('description', '')
    
    try:
        scenario = store.get_scenario(scenario_id)
        
        # If description provided, parse and apply it first
        if description and description.strip():
            # Store the description
            scenario.description = description
            
            # Parse and apply the description
            try:
                from nl_interface import parse_scenario
                parsed = parse_scenario(description)
                
                # Clear existing inputs and apply new ones
                scenario.inputs.clear()
                
                # First pass: collect all L1a values and Schedule E L26 values to sum them
                l1a_values = []
                schedule_e_l26_values = []
                other_inputs = []
                for inp in parsed.get("inputs", []):
                    form_name = inp["form"]
                    line_id = inp["line"]
                    value = inp["value"]
                    # Collect L1a values separately for summing
                    if form_name == "Form 1040" and line_id == "L1a" and isinstance(value, (int, float)):
                        l1a_values.append(value)
                        print(f"  DEBUG: Found L1a value in calculate_tax: ${value:,.0f}")
                    # Collect Schedule E L26 values separately for summing
                    elif form_name == "Schedule E" and line_id == "L26" and isinstance(value, (int, float)):
                        schedule_e_l26_values.append(value)
                        print(f"  DEBUG: Found Schedule E L26 value in calculate_tax: ${value:,.0f}")
                    else:
                        other_inputs.append(inp)
                
                # Sum all L1a values
                if l1a_values:
                    total_l1a = sum(l1a_values)
                    print(f"  NOTE: Summing {len(l1a_values)} L1a values in calculate_tax: {[f'${v:,.0f}' for v in l1a_values]} = ${total_l1a:,.0f}")
                    scenario.inputs[("Form 1040", "L1a")] = total_l1a
                    print(f"  DEBUG: Set scenario.inputs[('Form 1040', 'L1a')] = ${total_l1a:,.0f}")
                
                # Sum all Schedule E L26 values
                if schedule_e_l26_values:
                    total_l26 = sum(schedule_e_l26_values)
                    print(f"  NOTE: Summing {len(schedule_e_l26_values)} Schedule E L26 values in calculate_tax: {[f'${v:,.0f}' for v in schedule_e_l26_values]} = ${total_l26:,.0f}")
                    scenario.inputs[("Schedule E", "L26")] = total_l26
                    print(f"  DEBUG: Set scenario.inputs[('Schedule E', 'L26')] = ${total_l26:,.0f}")
                
                # Process other inputs (skip L1a and Schedule E L26 since we already handled them)
                openai_inputs = []  # Store all OpenAI inputs for QBI detection
                for inp in other_inputs:
                    form_name = inp["form"]
                    line_id = inp["line"]
                    value = inp["value"]
                    # Skip L1a (already summed above)
                    if form_name == "Form 1040" and line_id == "L1a":
                        continue
                    # Skip Schedule E L26 (already summed above)
                    if form_name == "Schedule E" and line_id == "L26":
                        continue
                    scenario.inputs[(form_name, line_id)] = value
                    openai_inputs.append(inp)
                
                # Also add L1a and Schedule E L26 inputs to openai_inputs for QBI detection
                for inp in parsed.get("inputs", []):
                    if (inp.get("form") == "Form 1040" and inp.get("line") == "L1a") or \
                       (inp.get("form") == "Schedule E" and inp.get("line") == "L26"):
                        openai_inputs.append(inp)
                
                # Store OpenAI inputs for QBI detection (same as core.py)
                setattr(scenario, "_openai_inputs", openai_inputs)
                
                # Store in history
                scenario.history.append(dict(scenario.inputs))
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Failed to parse description: {str(e)}'
                }), 400
        
        # Calculate tax
        summary = store.calculate_tax_liability(scenario_id)
        
        # Get updated scenario
        scenario = store.get_scenario(scenario_id)
        
        return jsonify({
            'success': True,
            'summary': {
                'year': summary['year'],
                'federal': summary['federal'],
                'inputs': summary['inputs'],
            },
            'scenario': {
                'id': scenario.scenario_id,
                'inputs': {
                    f"{form} / {line}": value
                    for (form, line), value in scenario.inputs.items()
                },
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/scenarios/<scenario_id>/restore', methods=['POST'])
def restore_scenario(scenario_id):
    """Restore a scenario to a previous state."""
    data = request.json
    history_index = data.get('history_index', -1)
    
    try:
        store.restore_scenario(scenario_id, history_index)
        scenario = store.get_scenario(scenario_id)
        
        return jsonify({
            'success': True,
            'scenario': {
                'id': scenario.scenario_id,
                'year': scenario.year,
                'inputs': {
                    f"{form} / {line}": value
                    for (form, line), value in scenario.inputs.items()
                },
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/scenarios/<scenario_id>', methods=['DELETE'])
def delete_scenario(scenario_id):
    """Delete a scenario."""
    try:
        if scenario_id in store._scenarios:
            del store._scenarios[scenario_id]
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Scenario not found'}), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


if __name__ == '__main__':
    import os
    
    # Use port from environment or default to 5001 (5000 is often used by AirPlay on macOS)
    port = int(os.getenv('PORT', 5001))
    
    print("=" * 70)
    print("TAXY Web UI Server")
    print("=" * 70)
    print(f"\nStarting server on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    print(f"\nNote: If port {port} is in use, set PORT environment variable:")
    print(f"  export PORT=8080")
    print(f"  python3 web_ui.py\n")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=port)
    except OSError as e:
        if 'Address already in use' in str(e):
            print(f"\nError: Port {port} is already in use.")
            print(f"Try a different port:")
            print(f"  PORT=8080 python3 web_ui.py")
            sys.exit(1)
        raise

