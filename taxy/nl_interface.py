"""
Natural Language Interface for Tax Scenarios

This module provides functions to:
1. Parse natural language tax scenarios into {form, line, value} triples
2. Handle modifications to existing scenarios
3. Use OpenAI to perform semantic mapping
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from openai import OpenAI


# System prompt from requirements.md
SYSTEM_PROMPT = """You are an intelligent tax mapping system. You will be given a tax scenario in natural language. Your job is to map each factual amount in the scenario to the **exact line on the correct U.S. federal tax form for tax year 2024** where that amount should be *directly input*.

For example, if I gave you a wage income of 280,000, you will map it to **Form 1040, line L1a** (Wages, salaries, tips) for 2024.

**RULES:**

1. You must use **OpenAI semantic reasoning ONLY** to map natural language to the correct form lines.

   * **Do NOT use regex, substring matching, keyword matching, heuristics, or pattern-based inference.**
   * The tenforty schema may have line IDs like "L1a" that contain no semantic meaning; you must rely entirely on form descriptions.

2. Return **only direct input lines**—the places where amounts are originally entered by the taxpayer or system.

   * Do NOT return derived totals, rollups, or downstream form lines.

3. If a fact flows through multiple forms (e.g., Schedule C → Schedule 1 → 1040), return **only the earliest upstream form/line** where the value is entered (e.g., Schedule C Line 31).

4. Always map to the specific form (e.g., "Form 1040", "Schedule 1", "Schedule C") and exact line identifier (e.g., "L1a", "L31").

4a. **Line Format Conventions (CRITICAL - Use these exact formats):**
   - **Schedule 1 lines**: Use "S1_1", "S1_2a", "S1_3", "S1_4", etc. (NOT "Sched1_L1", "L1", or "Schedule1_L1")
     * Schedule 1 Line 1 (taxable interest) → form: "Schedule 1", line: "S1_1"
     * Schedule 1 Line 3 (business income) → form: "Schedule 1", line: "S1_3"
   - **Form 1040 lines**: Use "L1a", "L2b", "L11", "L24", etc.
   - **Schedule C lines**: Use "L1", "L31", etc.
   - **Form 8812 lines**: Use "L4", "L4a", "L11", etc.
   - **Form 1040 special fields**: Use "Status" (not "FilingStatus"), "Dependents" (not "DependentsTable")

5. **Filing Status Mapping:**
   - "Single" → form: "Form 1040", line: "Status", value: "Single" or "S"
   - "Married Filing Jointly" or "MFJ" → form: "Form 1040", line: "Status", value: "Married/Joint" or "MFJ"
   - "Married Filing Separately" or "MFS" → form: "Form 1040", line: "Status", value: "Married/Separate" or "MFS"
   - "Head of Household" or "HOH" → form: "Form 1040", line: "Status", value: "Head of Household" or "HOH"
   - NEVER use numeric values (0, 1, 2) for filing status - always use the string values above.

6. **Dependents and Child Tax Credit (CRITICAL - Age Filtering Required):**
   - "No dependents" or "0 dependents" → form: "Form 1040", line: "Dependents", value: 0 AND form: "Form 8812", line: "L4", value: 0
   - "2 dependent children" → form: "Form 1040", line: "Dependents", value: 2 AND form: "Form 8812", line: "L4", value: 2 (if no ages provided, assume all under 17)
   - **CRITICAL: Child Tax Credit (Form 8812) is ONLY for children under age 17 at the end of the tax year (December 31, 2024)**
   - **You MUST ALWAYS return BOTH Form 1040 Dependents AND Form 8812 L4 when dependents are mentioned**
   - **Form 8812 L4 = number of qualifying children under age 17 (for Child Tax Credit)**
   - **Form 1040 Dependents = total number of dependents (all ages)**
   - Examples:
     * "2 children, ages 5 and 8" → form: "Form 1040", line: "Dependents", value: 2 AND form: "Form 8812", line: "L4", value: 2 (both under 17)
     * "2 children, ages 11 and 13" → form: "Form 1040", line: "Dependents", value: 2 AND form: "Form 8812", line: "L4", value: 2 (both under 17)
     * "2 children, ages 15 and 21" → form: "Form 1040", line: "Dependents", value: 2 AND form: "Form 8812", line: "L4", value: 1 (only the 15-year-old qualifies - 21 is over 17)
     * "2 children, ages 11 and 19" → form: "Form 1040", line: "Dependents", value: 2 AND form: "Form 8812", line: "L4", value: 1 (only the 11-year-old qualifies - 19 is over 17)
   - **If ages are provided, you MUST check if each child is under 17 at the end of 2024 (December 31, 2024) to determine the L4 value for Form 8812**
   - **If no ages are provided but dependents are mentioned, return Form 8812 L4 equal to Dependents (assuming all are under 17)**
   - **MANDATORY: Every time you return Form 1040 Dependents, you MUST also return Form 8812 L4 in the same response**

7. **Common Income Types:**
   - "Wage income", "W2 income", "salary" → form: "Form 1040", line: "L1a"
   - **CRITICAL - Filer/Spouse Attribution for Wage Income:**
     * If the input explicitly states "Filer has a wage income" or "Spouse has a wage income", you MUST preserve this information in the "fact" field
     * Example: "Filer has a wage income of $120K" → form: "Form 1040", line: "L1a", value: 120000, fact: "Filer has a wage income of $120,000" (preserve "Filer" in fact)
     * Example: "Spouse has a wage income of $180K" → form: "Form 1040", line: "L1a", value: 180000, fact: "Spouse has a wage income of $180,000" (preserve "Spouse" in fact)
     * This information is critical for accurate self-employment tax calculations
   - **S-Corp wages**: "S-Corp wage", "S Corp wage", "Scorp wage", "wage from S-Corp", "wage from S Corp", "wage from Scorp" → form: "Form 1040", line: "L1a" (S-Corp wages are W-2 wages and should be added to L1a)
   - "Taxable interest income", "interest income" → form: "Schedule 1", line: "S1_1"
   - "Business income", "Schedule C income", "self-employment income" → form: "Schedule C", line: "L31" (if net profit) or individual Schedule C lines
   - **CRITICAL - Filer/Spouse Attribution for Schedule C:**
     * If the input explicitly states "Filer has a Schedule C" or "Spouse has a Schedule C", you MUST preserve this information in the "fact" field
     * Example: "Spouse has a Schedule C net income of $64,000" → form: "Schedule C", line: "L31", value: 64000, fact: "Spouse's Schedule C net income of $64,000" (preserve "Spouse" in fact)
     * Example: "Filer has a Schedule C net income of $50,000" → form: "Schedule C", line: "L31", value: 50000, fact: "Filer's Schedule C net income of $50,000" (preserve "Filer" in fact)
     * This information is critical for accurate self-employment tax calculations (which spouse's W-2 wages to use for wage base calculation)
   - "Qualified business income", "QBI", "qualified business", "is a qualified business" → form: "Schedule C", line: "L31" 
   - **IMPORTANT**: If a business is qualified for QBI deduction, the QBI deduction (typically 20% of qualified business income) should be calculated and entered on Form 1040, line: "L13"
   - Note: QBI deduction calculation is complex and may require Form 8995. For now, if "qualified business" is mentioned, map Schedule C L31 and note that QBI deduction may apply.
   - **Rental income**: "rental income", "net rental income", "rental property income" → form: "Schedule E", line: "4_A" or "L4_A" (rents received for property A - the first rental property). Schedule E supports multiple properties (A, B, C), so use "4_A" for the first rental property, "4_B" for the second, etc.
   - **Rental depreciation**: "rental depreciation", "depreciation on rental property", "rental property depreciation", "depreciation expense for rental" → form: "Schedule E", line: "18_A" or "L18_A" (depreciation for property A - the first rental property). Use "18_B" for the second property, "18_C" for the third.
   - **S-Corp distributions**: "S-Corp distribution", "S Corp distribution", "Scorp distribution", "distribution from S-Corp", "distribution from S Corp", "distribution from Scorp" → form: "Schedule E", line: "4_B" or "L4_B" (royalties/rents for property B - S-Corp distributions are typically reported as royalties/rents on Schedule E). If there's already a rental property on property A, use property B for S-Corp distributions to preserve them separately.
   - **Note**: Schedule E has property-specific lines (4_A, 4_B, 4_C for income; 18_A, 18_B, 18_C for depreciation). OTS will automatically calculate L26 (total net income/loss) from all properties. Use different property columns (A, B, C) to preserve separate income sources for advanced planning.
   - "Dividend income" → form: "Schedule 1", line: "S1_2a" or "S1_2b" (depending on qualified vs ordinary)
   - **Capital Gains (Schedule D - separate schedule on the tax return):**
     * Schedule D is a separate schedule on the tax return. Map capital gains to "Schedule D" with appropriate line identifiers:
       - **Long-term capital gains:**
         * "Long term capital gain", "long-term capital gain", "LTCG" → form: "Schedule D", line: "L8h" or "D8h" (Part II, line 8, column h - net long-term gain)
         * If proceeds and cost are provided: form: "Schedule D", lines: "L8d" (proceeds) and "L8e" (cost) - net gain = proceeds - cost
         * "Capital gains distributions from 1099-DIV" → form: "Schedule D", line: "L13" or "D13"
       - **Short-term capital gains:**
         * "Short term capital gain", "short-term capital gain", "STCG" → form: "Schedule D", line: "L1h" or "D1h" (Part I, line 1, column h - net short-term gain)
         * If proceeds and cost are provided: form: "Schedule D", lines: "L1d" (proceeds) and "L1e" (cost) - net gain = proceeds - cost
         * "Short-term gain from other forms" → form: "Schedule D", line: "L4" or "D4"
     * **Note**: The calling code will map Schedule D fields to Form 1040 D* fields according to OTS requirements. You should map to Schedule D using standard Schedule D line identifiers (L8h, L1h, L13, L4, etc. or D8h, D1h, D13, D4, etc.)

8. **Common Deduction Types:**
   - "Property tax", "property tax paid", "real estate tax" → form: "Schedule A", line: "L5a"
   - "State and local taxes", "SALT" → form: "Schedule A", line: "L5a"
   - "Mortgage interest", "home mortgage interest", "mortgage on home" → form: "Schedule A", line: "L8"
   - "Itemized deductions" → form: "Schedule A", line: "L19" (total)

9. **Payments and Withholding:**
   - "Federal income tax withheld", "tax withheld from W-2", "withholding from Form W-2", "federal tax withheld" → form: "Form 1040", line: "L25a"
   - "Estimated tax payments", "estimated tax paid" → form: "Form 1040", line: "L26"
   - **CRITICAL**: Federal income tax withheld goes to L25a (NOT L16, L25, or any other line)

10. For each fact, output the mapping as JSON in this format:

```json
{
  "inputs": [
    {
      "fact": "<short description>",
      "form": "<form name>",
      "line": "<line id>",
      "value": <numeric value or string>,
      "description": "<form's human-readable description>"
    }
  ]
}
```"""


def load_api_key() -> str:
    """Load OpenAI API key from environment or file."""
    # Try environment variable first
    api_key = os.getenv("OPENAI_API_KEY")
    
    # If not in environment, try to load from a local config file
    if not api_key:
        # Try multiple possible locations
        possible_paths = [
            Path(__file__).parent.parent / "mcp_server" / "mcp_server" / "api_key.txt",
            Path(__file__).parent / "api_key.txt",
            Path.home() / ".openai" / "api_key.txt",
        ]
        
        for config_file in possible_paths:
            if config_file.exists():
                try:
                    api_key = config_file.read_text().strip()
                    break
                except Exception as e:
                    print(f"Warning: Could not read {config_file}: {e}")
    
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found. Set it with:\n"
            "  export OPENAI_API_KEY='your-key'\n"
            "Or create a file with your key in one of the expected locations"
        )
    
    return api_key


# Global OpenAI client (lazy initialization)
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = load_api_key()
        _client = OpenAI(api_key=api_key)
    return _client


def parse_scenario(
    scenario_text: str,
    model: Optional[str] = None,
    temperature: float = 0.0,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse a natural language tax scenario into {form, line, value} triples.
    
    Args:
        scenario_text: Natural language description of the tax scenario
        model: OpenAI model to use (default: gpt-4o)
        temperature: Temperature for generation (default: 0.0 for deterministic)
    
    Returns:
        Dict with "inputs" key containing list of {form, line, value} mappings
        
    Example:
        >>> parse_scenario("Wage income of 120K and schedule C net income of $40K")
        {
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
    """
    client = get_client()
    
    # Try multiple models in order of preference
    if model is None:
        models_to_try = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
    else:
        models_to_try = [model]
    
    user_prompt = f"""Map the following tax scenario to the correct form lines for tax year 2024:

{scenario_text}

Output only the JSON mapping as specified in the system prompt."""
    
    last_error = None
    for model_to_use in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                response_format={"type": "json_object"},  # Force JSON output
            )
            break  # Success, exit loop
        except Exception as e:
            last_error = e
            if model is not None:
                # User specified a model, don't try others
                raise
            # Try next model
            continue
    else:
        # All models failed
        raise RuntimeError(f"All models failed. Last error: {last_error}")
    
    # Process successful response
    try:
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Print OpenAI's raw output for debugging
        print("\n" + "=" * 70)
        print("OPENAI RAW OUTPUT:")
        print("=" * 70)
        print(content)
        print("=" * 70 + "\n")
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate structure
        if "inputs" not in result:
            raise ValueError("Response missing 'inputs' key")
        
        if not isinstance(result["inputs"], list):
            raise ValueError("'inputs' must be a list")
        
        # Validate each input
        for inp in result["inputs"]:
            required_keys = ["fact", "form", "line", "value"]
            for key in required_keys:
                if key not in inp:
                    raise ValueError(f"Input missing required key: {key}")
        
        return result
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}")
    except Exception as e:
        raise RuntimeError(f"Error processing response: {e}")


def parse_modification(
    modification_text: str,
    existing_scenario: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse a modification to an existing scenario.
    
    Args:
        modification_text: Natural language description of the modification
        existing_scenario: Optional existing scenario to modify (if None, treats as new scenario)
        model: OpenAI model to use
        temperature: Temperature for generation
    
    Returns:
        Dict with "inputs" key containing list of {form, line, value} mappings
        
    Example:
        >>> parse_modification("Change wage income to 150K", existing_scenario)
        {
          "inputs": [
            {
              "fact": "Wage income 150000",
              "form": "Form 1040",
              "line": "L1a",
              "value": 150000,
              "description": "Wages, salaries, tips"
            }
          ]
        }
    """
    client = get_client()
    
    # Build context about existing scenario if provided
    context = ""
    if existing_scenario:
        context = "\n\nCurrent scenario:\n"
        for inp in existing_scenario.get("inputs", []):
            context += f"- {inp.get('fact', 'Unknown')}: {inp.get('form', 'Unknown')} {inp.get('line', 'Unknown')} = {inp.get('value', 'Unknown')}\n"
    
    user_prompt = f"""Map the following modification to the tax scenario{context}:

{modification_text}

Output only the JSON mapping as specified in the system prompt. Include only the fields that are being modified or added."""
    
    # Try multiple models in order of preference
    if model is None:
        models_to_try = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
    else:
        models_to_try = [model]
    
    last_error = None
    for model_to_use in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                response_format={"type": "json_object"},  # Force JSON output
            )
            break  # Success, exit loop
        except Exception as e:
            last_error = e
            if model is not None:
                # User specified a model, don't try others
                raise
            # Try next model
            continue
    else:
        # All models failed
        raise RuntimeError(f"All models failed. Last error: {last_error}")
    
    # Process successful response
    try:
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate structure
        if "inputs" not in result:
            raise ValueError("Response missing 'inputs' key")
        
        if not isinstance(result["inputs"], list):
            raise ValueError("'inputs' must be a list")
        
        # Validate each input
        for inp in result["inputs"]:
            required_keys = ["fact", "form", "line", "value"]
            for key in required_keys:
                if key not in inp:
                    raise ValueError(f"Input missing required key: {key}")
        
        return result
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}")
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")


def apply_modification(
    base_scenario: Dict[str, List[Dict[str, Any]]],
    modification: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply a modification to a base scenario.
    
    Modifications are applied by form+line: if a modification has the same
    form+line as an existing input, it replaces it. Otherwise, it's added.
    
    Args:
        base_scenario: The base scenario to modify
        modification: The modification to apply
        
    Returns:
        Updated scenario with modifications applied
    """
    # Create a map of (form, line) -> input for base scenario
    base_map = {}
    for inp in base_scenario.get("inputs", []):
        key = (inp["form"], inp["line"])
        base_map[key] = inp
    
    # Apply modifications
    for inp in modification.get("inputs", []):
        key = (inp["form"], inp["line"])
        base_map[key] = inp  # Replace or add
    
    # Convert back to list
    updated_inputs = list(base_map.values())
    
    return {"inputs": updated_inputs}

