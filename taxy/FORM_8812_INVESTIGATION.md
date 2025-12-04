# Form 8812 Segfault Investigation

## Issue
Form 8812 causes segfaults (exit code 139) when evaluated using `evaluate_form()` in the OTS C++ library.

## Root Cause Analysis

### Field Mapping Issue (FIXED)

**Problem**: We were passing incorrect field values to Form 8812:

**What we were passing (WRONG):**
- `L1`: Child tax credit (calculated as $2,000 × children)
- `L13`: AGI from Form 1040

**What Form 8812 actually expects (per OTS source code):**
- `L1`: **AGI** from Form 1040 line 11 (NOT child tax credit!)
- `L13`: Amount from Credit Limit Worksheet A (NOT AGI!)
- `Amnt19`: Child tax credit from Form 1040 line 19 (optional)

### OTS Source Code Analysis

From `OpenTaxSolver2024_22.07_MacOSx/src/taxsolve_f8812_2024.c`:

```c
GetLineF( "L1", &L[1] );  // Amount from line 11 of your Form 1040 (AGI!)
GetLine( "L4", &L[4] );    // Number of qualifying children
GetLine( "L13", &L[13] );  // Amount from Credit Limit Worksheet A
GetLine( "Amnt19", &L[19] ); // Amount on Form 1040, line 19 (child tax credit)

// Calculation flow:
L[3] = L[1] + L2d;  // Modified AGI (L1 is AGI!)
L[5] = L[4] * 2000.0;  // Basic credit
L[8] = L[5] + L[7];  // Total credit
L[10] = L[3] - L[9];  // Excess AGI for phaseout (uses L3 which comes from L1/AGI)
L[11] = L[10] * 0.05;  // Reduction
L[12] = L[8] - L[11];  // Credit after phaseout
L[14] = SmallerOf(L[12], L[13]);  // Non-refundable credit
```

### Fix Applied

Updated `Form8812Handler.process()` to pass:
- `L1`: AGI (from Form 1040 L11) ✅
- `L4`: Number of qualifying children ✅
- `L13`: 0 (Credit Limit Worksheet A - not needed for basic cases) ✅
- `Amnt19`: 0 (OTS will calculate this) ✅

### Testing

The code now:
1. **First tries** to use OTS library with correct field mapping
2. **Falls back** to manual calculation if OTS segfaults

### Next Steps

1. Test if the segfault is resolved with correct field mapping
2. If segfault persists, investigate:
   - Missing required fields?
   - Data type issues (string vs numeric)?
   - Status format mismatch?
   - Other required fields we're not passing?

### Current Status

- ✅ Fixed field mapping (L1 = AGI, not child tax credit)
- ✅ Added try/except to attempt OTS first, fallback to manual
- ⚠️  Still testing if segfault is resolved

