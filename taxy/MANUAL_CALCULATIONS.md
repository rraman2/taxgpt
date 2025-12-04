# Manual Tax Calculations in Taxy

This document describes the tax logic that we've implemented manually in the `taxy` application, rather than relying on the underlying tax calculation libraries.

## Overview

Per the user's requirement: **"I do not like the idea of pulling any tax logic outside the core tax library"**

However, we've had to implement two manual calculations due to limitations in the underlying libraries:

1. **Form 8812 (Child Tax Credit)** - Manual calculation due to OTS library segfaults
2. **Schedule 1 Line Name Normalization** - Field name mapping (not tax logic)

---

## 1. Form 8812 (Child Tax Credit) - Manual Calculation

### Why Manual?

The OpenTaxSolver (OTS) C++ library causes **segfaults (exit code 139)** when evaluating Form 8812. This appears to be a fundamental bug in the underlying C++ code that prevents us from using `evaluate_form()` for Form 8812.

### Implementation

**Location**: `taxy/forms.py` - `Form8812Handler.process()` method (lines 404-537)

**What it calculates**: Form 8812 Part 1 - Non-refundable Child Tax Credit

**Calculation Steps** (matching IRS Form 8812 Part 1 exactly):

1. **Line 4**: Number of qualifying children (from inputs)
2. **Line 5**: Line 4 × $2,000 (basic credit)
3. **Line 6**: AGI from Form 1040 (L11)
4. **Line 7**: Phaseout threshold:
   - Married Filing Jointly: $400,000
   - All other statuses: $200,000
5. **Line 8**: Excess AGI (Line 6 - Line 7, minimum 0)
6. **Line 9**: Line 8 × 5% (reduction amount)
7. **Line 10**: Line 5 - Line 9 (credit after phaseout)
8. **Line 11**: Line 1 (basic credit from Form 1040)
9. **Line 12**: Minimum of Line 10 and Line 11 (non-refundable credit)

**Output**: Flows `L25a` (non-refundable child tax credit) to Form 1040

**Code Reference**:
```python
# Lines 476-537 in taxy/forms.py
# Manual calculation matching Form 8812 Part 1 logic
line_5 = 2000 * line_4  # $2,000 per child
line_8 = max(0, line_6 - line_7_threshold)  # Excess AGI
line_9 = line_8 * 0.05  # 5% reduction
line_10 = max(0, line_5 - line_9)  # Credit after phaseout
non_refundable_credit = min(line_10, line_11)  # Final credit
```

### Notes

- This matches the IRS Form 8812 Part 1 calculation exactly
- We only calculate the **non-refundable** portion (Part 1)
- The **refundable** portion (Part 2) is not implemented (not needed for basic scenarios)
- The result is flowed to Form 1040 as `L25a`

---

## 2. Schedule 1 Line Name Normalization

### Why Manual?

OpenAI might output various formats for Schedule 1 line names:
- `"L1"` (generic line number)
- `"Sched1_L1"` (form-prefixed)
- `"Schedule1_L1"` (full form name)
- `"S1_1"` (tenforty's expected format)

Since Schedule 1 is **embedded in Form 1040** (not a separate form), tenforty expects the `S1_*` format.

### Implementation

**Location**: `taxy/forms.py` - `Schedule1Handler.normalize_line_name()` method (lines 322-338)

**Normalization Rules**:
- `"L1"` → `"S1_1"` (taxable interest)
- `"Sched1_L1"` → `"S1_1"`
- `"L3"` → `"S1_3"` (business income from Schedule C)
- `"L5"` → `"S1_5"` (rental income from Schedule E)
- Already `"S1_*"` format → unchanged

**Code Reference**:
```python
# Lines 303-338 in taxy/forms.py
LINE_NORMALIZATION = {
    "L1": "S1_1",      # Schedule 1 line 1 (taxable interest)
    "Sched1_L1": "S1_1",
    "L3": "S1_3",      # Schedule 1 line 3 (business income)
    "L5": "S1_5",      # Schedule 1 line 5 (rental income)
}
```

### Notes

- This is **field name mapping**, not tax calculation logic
- It ensures OpenAI's output format matches tenforty's expected format
- Similar normalization exists for other forms (Form 1040, Form 8812, etc.)

---

## What We DON'T Calculate Manually

Per user requirements, we **do NOT** calculate:

- ✅ **SALT Cap** - OpenTaxSolver handles this automatically (see `taxy/forms.py` lines 258-282)
- ✅ **Itemized Deductions Total (A6)** - OpenTaxSolver calculates from A5b + A8a automatically
- ✅ **Standard vs Itemized Comparison** - OpenTaxSolver chooses the higher one automatically
- ✅ **Tax Brackets** - tenforty handles this
- ✅ **AGI Calculations** - tenforty handles this
- ✅ **Taxable Income** - tenforty handles this

---

## Future Improvements

1. **Form 8812**: If/when the OTS library fixes the segfault, we should remove the manual calculation and use `evaluate_form()` instead.

2. **Form 8812 Part 2**: Currently we only calculate the non-refundable portion. If refundable credits are needed, Part 2 logic would need to be added.

3. **Line Name Normalization**: This could potentially be handled by OpenAI if we update the system prompt to always use the exact format tenforty expects.

---

## Summary

- **1 manual tax calculation**: Form 8812 (due to library bug)
- **1 field name normalization**: Schedule 1 line names (not tax logic)
- **All other tax logic**: Handled by OpenTaxSolver/tenforty

The manual Form 8812 calculation is a **workaround** for a library bug, not a design choice. All other tax calculations are handled by the tax libraries as required.

