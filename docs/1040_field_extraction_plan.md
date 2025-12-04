## 1040 PDF Field Extraction – Fresh Plan

This file captures the **new, clean plan** for how we will extract fields from 1040 PDFs going forward. Everything described here supersedes prior attempts.

### Overall Goals

- **Work one field at a time**, with human-in-the-loop confirmation.
- Use **OpenAI** plus **pdfplumber coordinates** to:
  - Identify where a value is on the page (its bounding box / coordinates),
  - Confirm the value with you,
  - Refine coordinates if needed,
  - Store final coordinates + page + form name for reuse.

### Step 0 – Form Name / Form ID Detection

- **Input**: A PDF (may contain multiple forms/pages).
- **Process**:
  - On each page, use `pdfplumber` to extract:
    - The top margin text (e.g., first N lines),
    - Any bold/large-font text in the **top-left** and **top-right** regions.
  - Send that text to OpenAI with a prompt:
    - “Identify the form name and form number (e.g., `Form 1040`, `Schedule 1`) and which page of that form this is.”
  - For each page, store:
    - `form_name` (e.g., `"U.S. Individual Income Tax Return"`),
    - `form_id` (e.g., `"Form 1040"`),
    - `page_number_within_form` (1, 2, …).

- **Stored structure (per page)**:
  - `form_id` (string),
  - `form_name` (string),
  - `page_index` (0-based in PDF),
  - `form_page_number` (1-based within that form).

### Step 1 – Per-Field Coordinate Discovery

For **each field** (e.g., `L1a`, `L24`, `Dependents`, etc.):

1. **Initial guess using text search**:
   - Extract all words on the relevant page with `pdfplumber.page.extract_words()`.
   - Group words into “lines” based on `y` proximity.
   - Search each line for the field’s **label** (e.g., `"1a"`, `"Line 24"`, `"Total tax"`).
   - When a label is found:
     - Look **to the right** on the same line (or nearby lines) for a numeric value.
     - Record the word’s bounding box `(x0, y0, x1, y1)` as the **candidate coordinates**.

2. **Region-based backup**:
   - For fields that follow a predictable layout (right-side columns):
     - Define approximate regions as a percentage of page width/height.
     - Collect numeric-looking words within that region.
     - Use the best candidate (highest numeric, or closest to label line) as a fallback coordinate.

3. **AI-assisted backup** (optional, when needed):
   - Build a textual representation of the page structure (lines with approximate `Y` positions).
   - Ask OpenAI:
     - “Given this layout, where is the value for field X (e.g., `L24 Total tax`)? Return approximate `(x0, y0, x1, y1)`.”
   - Use those coordinates to crop the page and re-scan for the numeric value.

### Step 2 – Ask You to Confirm

For each field after we have a **value + coordinates**:

1. Print / log:
   - `field_id` (e.g., `L24`),
   - `form_id` and `form_page_number`,
   - `page_index` in the PDF,
   - `bbox` = `(x0, y0, x1, y1)`,
   - `extracted_value` (e.g., `21000.50`).
2. Ask: **“Is this correct? (yes/no)”**.

### Step 3 – Handle Yes / No Feedback

- If **you say “yes”**:
  - Mark the field as **confirmed**.
  - Store the coordinates and value in a persistent mapping.

- If **you say “no”**:
  1. Ask: **“What is the correct value for this field?”**.
  2. Use that value to:
     - Search nearby text / words on the same page for that exact value (numeric match with tolerance).
     - If found:
       - Update coordinates to the bounding box of the matched word.
       - Mark these as the **final coordinates**.
     - If not found:
       - Expand the search region gradually (larger bbox or whole page) to locate the value.

### Step 4 – Store Final Coordinate Mapping

For each confirmed field, store a record like:

```json
{
  "field_id": "L24",
  "form_id": "Form 1040",
  "form_name": "U.S. Individual Income Tax Return",
  "pdf_page_index": 0,
  "form_page_number": 1,
  "bbox": [x0, y0, x1, y1],
  "value": 21000.50,
  "confidence": "human_confirmed",
  "notes": "Found via label search + user confirmation"
}
```

We can accumulate these in a JSON file, e.g.:

- `mappings/1040_2024_field_coordinates.json`

This will let future runs:

- Skip discovery for already-mapped fields,
- Directly crop at stored coordinates and read values,
- Only fall back to interactive mode when something looks inconsistent.

### Next Steps When You Return

- Implement a **minimal script** that:
  1. Handles **Step 0** (form/page detection) for your `1040.pdf`.
  2. Implements **Step 1 + 2 + 3** for **exactly one field**, e.g. `L1a`:
     - Run extraction,
     - Show coordinates + value,
     - Accept your “yes/no” feedback,
     - If “no”, ask for the correct value and refine coordinates.
  3. Writes the confirmed mapping as a single JSON entry.

- Once `L1a` is stable, we’ll replicate the pattern for:
  - `L2b`, `L3a`, `L3b`, `L11`, `L15`, `L24`, etc.


