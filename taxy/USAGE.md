# How to Run Taxy

## Quick Start

### Option 0: Web UI (Recommended)

```bash
cd taxy

# Install Flask if not already installed
pip3 install flask flask-cors

# Start the web server
python3 web_ui.py
```

Then open http://localhost:5000 in your browser.

**Features:**
- Create scenarios with "Add New Scenario" button
- Each scenario is displayed as a card
- Modify any card directly by editing its description
- Calculate tax for each scenario independently
- Restore previous states
- Delete scenarios

### Option 1: Command Line (Single Scenario)

```bash
cd taxy
python3 run_nl.py "Wage income of $200K, married filing jointly, 2 dependent children"
```

### Option 2: Interactive Mode

```bash
cd taxy
python3 run_nl.py --interactive
```

Then type scenarios:
```
Tax scenario> Wage income of $120K and schedule C net income of $40K
Tax scenario> modify Change wage income to $150K
Tax scenario> quit
```

### Option 3: Python Script

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, 'taxy')

from core import ScenarioStore

store = ScenarioStore()

# Create scenario
scenario = store.create_scenario(
    year=2024,
    nl_description="Wage income of $200K, married filing jointly, 2 dependent children"
)

# Calculate tax
summary = store.calculate_tax_liability(scenario.scenario_id)

print(f"Total Tax: ${summary['federal']['total_tax']:,.2f}")
print(f"Child Tax Credit: ${summary['federal']['child_tax_credit']:,.2f}")
```

### Option 4: Run Examples

```bash
cd taxy

# Standalone NL parsing examples
python3 nl_example.py

# Integration examples with tax calculation
python3 nl_integration_example.py
```

## Setup

1. **Set OpenAI API Key**:
   ```bash
   export OPENAI_API_KEY='your-key-here'
   ```
   Or place it in `mcp_server/mcp_server/api_key.txt`

2. **Make sure you're in the right directory**:
   ```bash
   cd /Users/ramesh/Documents/Projects/taxgpt/taxy
   ```

## Example Scenarios

### Basic Income
```
"Wage income of $120K"
```

### With Business Income
```
"Wage income of $120K and schedule C net income of $40K"
```

### With Dependents
```
"Married filing jointly with 2 dependent children. Wage income $200K. Qualifying children under 17: 2."
```

### Modifications
```
modify Change wage income to $150K
modify Remove schedule C income
modify Add 1 more dependent child
```

## Troubleshooting

- **Import errors**: Make sure you're running from the `taxy/` directory
- **API key errors**: Check that `OPENAI_API_KEY` is set or the key file exists
- **Model errors**: The system will try multiple models (gpt-4o → gpt-4-turbo → gpt-3.5-turbo)

