
# ✅ **Integrated Requirements Specification (Final Version — OpenAI-Only Mapping, No Regex)**

## **1. Purpose**

Build a system that takes natural-language tax scenarios and maps each fact to the **exact line on the correct 2024 U.S. federal tax form** (Form 1040 and supporting schedules), using a simple symbolic contract:

```json
{
  "form": "Form 1040",
  "line": "L1a",
  "value": 120000
}
```

The system will output **only direct input lines**, not derived totals or roll-ups.

All mapping from natural language → `{form, line, value}` triples must be done by **OpenAI semantic reasoning only**.

---

# **2. Core Behavior Requirements**

### **2.1 OpenAI-Only NL → Line Mapping (Non-Negotiable)**

* The agent MUST use **OpenAI semantic interpretation** to map natural language descriptions to form lines.
* **Regex, substring matching, keyword matching, numerical pattern inference, or heuristics are strictly forbidden.**
* The agent must rely exclusively on:

  * openAI reasoning
  * MCP-provided schema metadata (labels & descriptions)
  * contextual interpretation of natural language

### **2.2 Direct Input Lines Only**

The system returns **only the lines that the user or system directly inputs**, not:

* downstream lines
* totals
* derived calculations
* roll-ups across forms

Those will be handled by your tax engine.

### **2.3 Upstream-Only Rule**

If a fact flows across several forms (e.g., Schedule C → Schedule 1 → 1040), the agent must return ONLY the **earliest upstream form/line** where the value is manually entered or originated.

---

# **3. MCP Server Requirements**

The MCP server wraps the *tenforty* Python library and exposes:

### Required Tools

| Tool                      | Purpose                                                              |
| ------------------------- | -------------------------------------------------------------------- |
| `create_scenario`         | Make a new return                                                    |
| `clone_scenario`          | Copy a return for “what-if” scenarios                                |
| `get_schema`              | Return enriched metadata (form, line number, description, data type) |
| `get_return_fields`       | Read values                                                          |
| `update_return_fields`    | Write values                                                         |
| `calculate_tax_liability` | Compute taxes                                                        |

### Schema Metadata (Required Format)

For every field, MCP must return something like:

```json
{
  "path": "form1040.L1a",
  "label": "Wages, salaries, tips",
  "description": "W-2 income earned by the taxpayer",
  "form": "Form 1040",
  "line_number": "1a",
  "data_type": "number"
}
```

These descriptions are what OpenAI uses to map natural-language facts.

### Update Validation

* `update_return_fields` **must refuse any path not contained in the MCP schema.**
* This prevents the agent from inventing fields.
* BUT it must NOT enforce regex logic or heuristics.

---

# **4. Agent Workflow Requirements**

For each user-provided scenario:

1. Extract atomic tax facts using natural-language understanding.
2. For each fact:

   * Ask MCP for the relevant schema slice.
   * Use **OpenAI semantic reasoning** to choose the correct form + line.
   * Never use pattern-matching, never infer meaning from the line ID.
3. Output only:

   * the fact
   * the selected form
   * the exact line
   * the user’s numeric value
   * the form’s human-readable description
4. NO derived or downstream fields.

---

# **5. System Prompt (FINAL — Insert Into Agent)**

This is the exact system prompt you asked for, now fully aligned with the requirements.

> **System Prompt**
> You are an intelligent tax mapping system. You will be given a tax scenario in natural language. Your job is to map each factual amount in the scenario to the **exact line on the correct U.S. federal tax form for tax year 2024** where that amount should be *directly input*.
>
> For example, if I gave you a wage income of 280,000, you will map it to **Form 1040, line L1a** (Wages, salaries, tips) for 2024.
>
> **RULES:**
>
> 1. You must use **OpenAI semantic reasoning ONLY** to map natural language to the correct form lines.
>
>    * **Do NOT use regex, substring matching, keyword matching, heuristics, or pattern-based inference.**
>    * The tenforty schema may have line IDs like “L1a” that contain no semantic meaning; you must rely entirely on form descriptions.
> 2. Return **only direct input lines**—the places where amounts are originally entered by the taxpayer or system.
>
>    * Do NOT return derived totals, rollups, or downstream form lines.
> 3. If a fact flows through multiple forms (e.g., Schedule C → Schedule 1 → 1040), return **only the earliest upstream form/line** where the value is entered (e.g., Schedule C Line 31).
> 4. Always map to the specific form (e.g., “Form 1040”, “Schedule 1”, “Schedule C”) and exact line identifier (e.g., “L1a”, “L31”).
> 5. For each fact, output the mapping as JSON in this format:
>
> ```json
> {
>   "inputs": [
>     {
>       "fact": "<short description>",
>       "form": "<form name>",
>       "line": "<line id>",
>       "value": <numeric value>,
>       "description": "<form’s human-readable description>"
>     }
>   ]
> }
> ```

---

# **6. Example User Prompt Mapping (for testing)**

> **User prompt:**
> “Wage income of 120K and a schedule C net income of $40K”

Correct output under this requirement:

```json
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
```

