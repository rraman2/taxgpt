# Taxy - Natural Language Tax Scenario Interface

A system that maps natural language tax scenarios to IRS tax forms and calculates tax liability.

## Quick Start

### 1. Basic Usage (Command Line)

```bash
cd taxy
python3 run_nl.py "Wage income of $200K, married filing jointly, 2 dependent children"
```

### 2. Interactive Mode

```bash
python3 run_nl.py --interactive
```

Then type scenarios like:
```
Tax scenario> Wage income of $120K and schedule C net income of $40K
Tax scenario> modify Change wage income to $150K
```

### 3. Python API

```python
from core import ScenarioStore

store = ScenarioStore()

# Create scenario from natural language
scenario = store.create_scenario(
    year=2024,
    nl_description="Married filing jointly, wage income $200K, 2 dependent children"
)

# Calculate tax
summary = store.calculate_tax_liability(scenario.scenario_id)
print(f"Total Tax: ${summary['federal']['total_tax']:,.2f}")
```

## Examples

### Example 1: Basic Scenario
```bash
python3 run_nl.py "Wage income of $120K and schedule C net income of $40K"
```

### Example 2: Complex Scenario
```bash
python3 run_nl.py "Married filing jointly with 2 dependent children. Wage income $200K. Qualifying children under 17: 2."
```

### Example 3: Run Examples
```bash
python3 nl_example.py              # Standalone NL parsing examples
python3 nl_integration_example.py  # Integration with tax calculation
```

## Architecture

- **`nl_interface.py`**: Natural language parsing using OpenAI
- **`core.py`**: Scenario management and tax calculation
- **`forms.py`**: Form handlers for IRS forms (1040, Schedule C, Schedule 1, Form 8812)
- **`run_nl.py`**: Command-line interface

## Requirements

- Python 3.9+
- OpenAI API key (set `OPENAI_API_KEY` environment variable or place in `mcp_server/mcp_server/api_key.txt`)
- `tenforty` library (for tax calculations)

## How It Works

1. **Natural Language Input**: You describe a tax scenario in plain English
2. **OpenAI Mapping**: The system uses OpenAI to map your description to `{form, line, value}` triples
3. **Form Processing**: Forms are processed in IRS flow order (Schedule C → Schedule 1 → 1040 → Form 8812)
4. **Tax Calculation**: The `tenforty` library calculates tax liability
5. **Results**: You get AGI, taxable income, total tax, and credits

## Supported Forms

- **Form 1040**: Main tax return
- **Schedule C**: Business income
- **Schedule 1**: Additional income
- **Form 8812**: Child Tax Credit (calculated manually due to OTS library limitations)

## Notes

- Form 8812 is calculated manually (the OTS C++ library causes segfaults)
- The system uses OpenAI semantic reasoning only (no regex or pattern matching)
- Only direct input lines are returned (not derived totals)

