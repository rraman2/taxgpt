# OpenTaxSolver (OTS) C Library Limitations and Workarounds

This document outlines the gaps, limitations, and known issues encountered when using the OpenTaxSolver C library through Python via the `tenforty` wrapper, along with the workarounds implemented in the `taxy` application.

## Overview

The `taxy` application uses the `tenforty` Python library, which wraps the OpenTaxSolver (OTS) C++ library for tax calculations. While OTS provides comprehensive tax calculation capabilities, several issues have been encountered that require manual workarounds or alternative implementations.

## Known Issues and Limitations

### 1. Form 8812 (Child Tax Credit) - Segfault

**Issue**: The `evaluate_form` call for Form 8812 consistently causes a segmentation fault when called through the Python wrapper.

**Symptoms**:
- Python process crashes with segmentation fault
- Error: `zsh: segmentation fault python3 taxy/core.py`
- Occurs regardless of input values or field mappings

**Root Cause**: 
- Suspected bug in the underlying OTS C++ library's Form 8812 implementation
- May be related to memory management or field validation in the C code
- Persists even with correct field mappings and valid input values

**Workaround**:
- **Manual calculation implemented** in `Form1040Handler.process()` (in `taxy/forms.py`)
- Calculates non-refundable Child Tax Credit (Part 1 of Form 8812) directly in Python
- Uses the exact OTS logic from `taxsolve_f8812_2024.c`:
  - $2,000 per qualifying child under age 17
  - Phase-out based on AGI thresholds
  - Maximum credit limitation
- The calculated credit is then passed to Form 1040 as `L19` (Child tax credit/credit for other dependents)

**Impact**:
- ✅ Child Tax Credit calculation works correctly
- ❌ Refundable portion (Part 2) of Form 8812 is not implemented
- ❌ Additional Child Tax Credit (ACTC) is not calculated

**Files Affected**:
- `taxy/forms.py`: `Form1040Handler.process()` - manual CTC calculation
- `taxy/FORM_8812_INVESTIGATION.md`: Detailed investigation notes

---

### 2. Form 8995 (Qualified Business Income Deduction) - Hangs/Crashes

**Issue**: The `evaluate_form` call for Form 8995 consistently hangs or crashes when provided with `FileName1040` and/or `FileNameSchC` parameters.

**Symptoms**:
- Python process hangs indefinitely when calling `evaluate_form` for Form 8995
- Semaphore leak warnings: `multiprocessing.resource_tracker` warnings
- Occurs even with correctly formatted synthetic files containing all required fields

**Root Cause**:
- OTS's `ImportReturnData` function (used to read `FileName1040` and `FileNameSchC`) appears to have issues when called through the Python wrapper
- May be related to file path handling, file format parsing, or inter-process communication
- The C code expects specific file formats and field names, which have been verified to be correct

**Workaround**:
- **Manual calculation implemented** in `Form8995Handler.process()` (in `taxy/forms.py`)
- Calculates QBI deduction using the exact OTS logic from `taxsolve_f8995_2024.c` (lines 254-268):
  - Qualified Business Income (QBI) = Schedule C L31 minus certain deductions
  - 20% of QBI (subject to limitations)
  - Taxable income limitation (20% of taxable income before QBI)
  - Final deduction = min(QBI component, taxable income limitation)
- The calculated deduction is then passed to Form 1040 as `L13` (Qualified business income deduction)

**Impact**:
- ✅ Basic QBI deduction calculation works correctly
- ❌ Complex QBI limitations (e.g., specified service trade or business phase-outs, wage/capital limitations) may not be fully implemented
- ❌ Form 8995-A (for more complex scenarios) is not supported

**Files Affected**:
- `taxy/forms.py`: `Form8995Handler.process()` - manual QBI calculation
- Synthetic file creation code (temporarily created but not used due to hang)

**Note**: The user explicitly stated: "The manual calculation will not work. This can be a very slippery slope where we start to implement each of the forms locally. Note that the QBI calc is a lot more complex with nuanced conditions which we might need eventually." However, due to the persistent OTS hang, manual calculation is currently the only viable option.

---

### 3. Schedule E Form ID Mismatch

**Issue**: The OTS form ID for Schedule E is `US_1040_Sched_E_brokerage_royalties`, not `US_1040_Sched_E`.

**Symptoms**:
- `evaluate_form` fails with: `No form available under key: [(2024, 'US_1040_Sched_E')]`
- Schedule E evaluation fails, requiring fallback calculation

**Root Cause**:
- The `tenforty` library uses the form ID `US_1040_Sched_E_brokerage_royalties` for Schedule E
- This is the actual form ID registered in the OTS configuration

**Workaround**:
- Use the correct form ID: `US_1040_Sched_E_brokerage_royalties`
- Implemented fallback calculation in `ScheduleEHandler.process()` that manually sums property-specific income and expenses if OTS evaluation fails

**Impact**:
- ✅ Schedule E processing works with correct form ID
- ⚠️ Fallback calculation is used if OTS evaluation fails for any reason

**Files Affected**:
- `taxy/forms.py`: `ScheduleEHandler.ots_form_id` - corrected to `US_1040_Sched_E_brokerage_royalties`

---

### 4. File-Based Inter-Form Dependencies

**Issue**: Some OTS forms (e.g., Form 8995, state forms) require file paths to output files from other forms (e.g., `FileName1040`, `FileNameSchC`).

**Symptoms**:
- Forms that depend on other forms' outputs cannot be calculated in isolation
- Requires creating synthetic output files with specific formats
- File format must match OTS's expected format exactly

**Root Cause**:
- OTS uses `ImportReturnData` to read values from previously calculated forms
- The file format must match the output format of the source form
- String fields (e.g., `Your1stName:`, `YourLastName:`, `YourSocSec#:`) are required even if not used in calculations

**Workaround**:
- Create temporary synthetic files with required fields
- Format must match OTS output format:
  - Numeric fields: `L11 = 266142.99` (equals sign, 2 decimal places, no semicolon)
  - String fields: `Your1stName: Taxpayer` (colon, no semicolon)
- Use absolute file paths
- Clean up temporary files after use

**Impact**:
- ⚠️ Complex file format requirements
- ⚠️ File creation and cleanup overhead
- ❌ Form 8995 still hangs even with correctly formatted files (see Issue #2)

**Files Affected**:
- `taxy/forms.py`: `Form8995Handler.process()` - synthetic file creation (currently unused due to hang)

---

### 5. Limited Error Reporting

**Issue**: OTS errors are not always clearly reported through the Python wrapper.

**Symptoms**:
- Segfaults provide no error messages
- Hangs provide no indication of what went wrong
- Some validation errors are not surfaced to Python

**Root Cause**:
- C++ exceptions/errors may not be properly caught and translated by the Python wrapper
- Memory errors (segfaults) bypass Python exception handling

**Workaround**:
- Extensive debug logging in Python code
- Try-except blocks around OTS calls
- Fallback calculations when OTS calls fail
- Manual verification of inputs before calling OTS

**Impact**:
- ⚠️ Difficult to debug OTS issues
- ⚠️ Requires extensive logging and error handling

---

### 6. Form Processing Order Dependencies

**Issue**: Some forms must be processed in a specific order because they depend on outputs from other forms.

**Symptoms**:
- Form 8995 requires Form 1040 outputs (AGI, deductions)
- Form 8812 requires Form 1040 outputs (AGI)
- Schedule SE requires Schedule C outputs (L31)

**Root Cause**:
- Tax forms have inherent dependencies (e.g., AGI must be calculated before credits that phase out based on AGI)

**Workaround**:
- Implemented `FormCoordinator` with explicit flow order:
  1. Schedule C
  2. Schedule D
  3. Schedule SE
  4. Schedule E
  5. Schedule A
  6. Form 1040 (first pass)
  7. Form 8995 (QBI deduction)
  8. Form 1040 (final pass with QBI and credits)
  9. Form 2210 (optional)
- Store form outputs in context for subsequent forms to access

**Impact**:
- ✅ Correct processing order ensures accurate calculations
- ⚠️ Multiple passes of Form 1040 may be required (performance consideration)

**Files Affected**:
- `taxy/forms.py`: `FormCoordinator.flow_order` and `process_scenario()`

---

### 7. Field Name Normalization Requirements

**Issue**: OpenAI's output field names don't always match OTS's expected field names exactly.

**Symptoms**:
- OpenAI may return `"FilingStatus"` but OTS expects `"Status"`
- OpenAI may return `"Sched1_L1"` but OTS expects `"S1_1"`
- OpenAI may return `"MFJ"` but OTS expects `"Married/Joint"`

**Root Cause**:
- OpenAI uses natural language understanding, which may produce variations
- OTS has strict field name requirements

**Workaround**:
- Implemented normalization in each `FormHandler`:
  - `normalize_line_name()`: Converts line names to OTS format
  - `normalize_value()`: Converts values to OTS format
- Updated OpenAI prompt to use exact OTS field names

**Impact**:
- ✅ Field names are correctly normalized
- ⚠️ Requires maintenance if OTS field names change

**Files Affected**:
- `taxy/forms.py`: All `FormHandler` subclasses have normalization methods
- `taxy/nl_interface.py`: `SYSTEM_PROMPT` includes exact field name conventions

---

## Summary of Manual Calculations

The following tax calculations are currently implemented manually in Python due to OTS limitations:

1. **Form 8812 Part 1 (Non-refundable Child Tax Credit)**
   - Location: `Form1040Handler.process()`
   - Reason: Segfault in OTS
   - Status: ✅ Working

2. **Form 8995 (Qualified Business Income Deduction)**
   - Location: `Form8995Handler.process()`
   - Reason: Hangs when using `FileName1040`/`FileNameSchC`
   - Status: ✅ Basic calculation working, complex limitations may be incomplete

3. **Schedule E Net Rental Income/Loss (Fallback)**
   - Location: `ScheduleEHandler.process()`
   - Reason: OTS evaluation may fail
   - Status: ✅ Fallback calculation works

## Recommendations

1. **For Form 8812**: Consider implementing the refundable portion (Part 2) if needed for future tax years.

2. **For Form 8995**: 
   - Investigate the root cause of the hang in OTS's `ImportReturnData` function
   - Consider contributing a fix to the OTS project if possible
   - Expand manual calculation to handle all QBI limitations if OTS cannot be fixed

3. **For File-Based Dependencies**: 
   - Document the exact file format requirements for each form
   - Create utility functions for generating synthetic files
   - Consider caching generated files for debugging

4. **For Error Handling**: 
   - Improve error reporting from OTS to Python
   - Add timeout mechanisms for OTS calls that may hang
   - Implement retry logic for transient failures

5. **For Testing**: 
   - Create comprehensive test cases for each workaround
   - Compare manual calculations with OTS outputs (when OTS works)
   - Document expected vs. actual behavior for each limitation

## Related Documentation

- `taxy/FORM_8812_INVESTIGATION.md`: Detailed investigation of Form 8812 segfault
- `taxy/MANUAL_CALCULATIONS.md`: Documentation of manual calculation implementations
- `taxy/requirements.md`: Overall system requirements and architecture

## Version Information

- **OTS Version**: OpenTaxSolver2024_22.07_MacOSx
- **Tax Year**: 2024
- **Python Wrapper**: `tenforty` library
- **Last Updated**: December 2024

