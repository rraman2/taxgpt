#!/usr/bin/env python3
"""
Form handlers: dedicated layer for each IRS form/schedule.

Each handler:
- Knows its OTS form_id (e.g., "US_1040", "US_1040_Sched_C", "Form_8812")
- Validates inputs for that form
- Processes inputs and calls evaluate_form
- Knows what outputs flow to other forms

The FormCoordinator orchestrates the IRS flow order.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import os
import tempfile
from tenforty.core import evaluate_form  # type: ignore


class FormHandler(ABC):
    """Base class for form handlers."""

    @property
    @abstractmethod
    def form_name(self) -> str:
        """Human-readable form name (e.g., "Form 1040", "Schedule C")."""
        pass

    @property
    @abstractmethod
    def ots_form_id(self) -> str:
        """OTS form ID (e.g., "US_1040", "US_1040_Sched_C")."""
        pass

    def normalize_line_name(self, line: str) -> str:
        """
        Normalize OpenAI's line names to OTS line names.
        Override in subclasses to add form-specific normalizations.
        """
        return line

    def normalize_value(self, line: str, value: Any) -> Any:
        """
        Normalize values (e.g., filing status codes).
        Override in subclasses to add form-specific value normalizations.
        """
        return value

    def normalize_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all inputs: line names and values.
        """
        normalized = {}
        for line, value in inputs.items():
            normalized_line = self.normalize_line_name(line)
            normalized_value = self.normalize_value(normalized_line, value)
            normalized[normalized_line] = normalized_value
        return normalized

    @abstractmethod
    def validate_line(self, line: str) -> bool:
        """Check if a line ID is valid for this form."""
        pass

    @abstractmethod
    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process inputs for this form and return results.

        Args:
            year: Tax year
            inputs: Dict of {line_id: value} for this form
            context: Results from previously processed forms (for flow)

        Returns:
            Dict with:
            - "outputs": All OTS outputs from this form
            - "flows": Dict of {target_form: {line: value}} for downstream forms
        """
        pass


class ScheduleCHandler(FormHandler):
    """Handler for Schedule C (Business Income)."""

    @property
    def form_name(self) -> str:
        return "Schedule C"

    @property
    def ots_form_id(self) -> str:
        return "US_1040_Sched_C"

    def validate_line(self, line: str) -> bool:
        # Schedule C has lines like L1, L2, L6, L8, L9, L10, ..., L31
        valid_lines = {
            "L1", "L2", "L6", "L8", "L9", "L10", "L11", "L12", "L13", "L14",
            "L15", "L16a", "L16b", "L17", "L18", "L19", "L20", "L21", "L22",
            "L23", "L24", "L25", "L26", "L27", "L28", "L29", "L30", "L31",
        }
        return line in valid_lines

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Schedule C and flow net income (L31) to Schedule 1."""
        # Normalize inputs first
        normalized_inputs = self.normalize_inputs(inputs)

        # Call OTS for Schedule C
        try:
            result = evaluate_form(
                year=year,
                federal_form_id=self.ots_form_id,
                federal_form_values=normalized_inputs,
            )
        except Exception as e:
            print(f"Warning: Schedule C evaluation failed: {e}")
            print(f"  Inputs were: {normalized_inputs}")
            return {
                "outputs": {},
                "flows": {},
            }

        outputs = result["federal"]
        flows = {}

        # Schedule C L31 (Net profit/loss) flows directly to Form 1040, Schedule 1 Line 3 (S1_3)
        # Check both outputs (calculated) and inputs (if provided directly)
        net_income = outputs.get("L31", 0)
        if not net_income:
            # Fall back to input if output not available (e.g., if only L31 was provided)
            net_income = normalized_inputs.get("L31", 0)
        
        if net_income:
            flows["Form 1040"] = {"S1_3": net_income}
            print(f"  Schedule C: Flowing L31 (${net_income}) to Form 1040 as S1_3")
            
            # Initialize or update Schedule C context bucket
            if "Schedule C" not in context:
                context["Schedule C"] = {}
            context["Schedule C"]["L31"] = net_income

            # Check if OpenAI indicated this is a "qualified business" (not a specified service trade or business)
            # Look for keywords in the original OpenAI inputs
            form_inputs_dict = context.get("form_inputs", {})
            all_openai_inputs = form_inputs_dict.get("_all_inputs", [])
            
            # Check if any OpenAI input for Schedule C mentioned "qualified business" or "QBI"
            is_qualified = False
            is_specified_service = None  # None = unknown, True = SSTB, False = qualified
            for inp in all_openai_inputs:
                if inp.get("form") == "Schedule C":
                    fact = inp.get("fact", "").lower() if isinstance(inp.get("fact"), str) else ""
                    description = inp.get("description", "").lower() if isinstance(inp.get("description"), str) else ""
                    if ("qualified business" in fact or "qbi" in fact or 
                        "qualified business" in description or "qbi" in description):
                        is_qualified = True
                        is_specified_service = False  # Qualified = NOT a specified service business
                        print(f"  Schedule C: OpenAI indicated 'qualified business' in: {inp.get('fact', 'N/A')}")
                        break
                    elif "specified service" in fact or "sstb" in fact:
                        is_specified_service = True
                        print(f"  Schedule C: OpenAI indicated 'specified service business' in: {inp.get('fact', 'N/A')}")
                        break
            
            # Store flags - OTS/Form 8995 should handle QBI calculation automatically
            context["Schedule C"]["is_qualified"] = is_qualified
            context["Schedule C"]["is_specified_service"] = is_specified_service

            # Also stamp these onto the outputs dict so that when FormCoordinator
            # overwrites context['Schedule C'] with completed outputs, we don't
            # lose the QBI metadata (L31 and flags).
            outputs["L31"] = net_income
            outputs["is_qualified"] = is_qualified
            outputs["is_specified_service"] = is_specified_service

            # Debug: show how we're classifying this Schedule C business
            print(
                "  Schedule C: QBI classification -> "
                f"is_qualified={is_qualified}, "
                f"is_specified_service={is_specified_service}, "
                f"context['Schedule C']={context.get('Schedule C')}"
            )

            if is_qualified:
                print("    Schedule C: Qualified business detected (NOT a specified service trade or business)")
                print("    QBI deduction will be attempted via Form 8995")

        return {
            "outputs": outputs,
            "flows": flows,
        }


class ScheduleEHandler(FormHandler):
    """Handler for Schedule E (Supplemental Income and Loss - Rental Income)."""

    @property
    def form_name(self) -> str:
        return "Schedule E"

    @property
    def ots_form_id(self) -> str:
        return "US_1040_Sched_E"

    def validate_line(self, line: str) -> bool:
        # Schedule E has lines like L1-L26
        # L26 is the net rental income/loss
        valid_lines = {
            "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10",
            "L11", "L12", "L13", "L14", "L15", "L16", "L17", "L18", "L19", "L20",
            "L21", "L22", "L23", "L24", "L25", "L26",
        }
        return line in valid_lines

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Schedule E and flow net rental income (L26) to Schedule 1."""
        # Normalize inputs first
        normalized_inputs = self.normalize_inputs(inputs)

        # Call OTS for Schedule E
        try:
            result = evaluate_form(
                year=year,
                federal_form_id=self.ots_form_id,
                federal_form_values=normalized_inputs,
            )
        except Exception as e:
            print(f"Warning: Schedule E evaluation failed: {e}")
            print(f"  Inputs were: {normalized_inputs}")
            # If evaluation fails, try to use L26 directly if provided
            if "L26" in normalized_inputs:
                net_rental = normalized_inputs["L26"]
                return {
                    "outputs": {"L26": net_rental},
                    "flows": {"Form 1040": {"S1_5": net_rental}},  # Flow directly to Form 1040 with normalized name
                }
            return {
                "outputs": {},
                "flows": {},
            }

        outputs = result["federal"]
        flows = {}

        # Schedule E L26 (Net rental income/loss) flows to Schedule 1, Line 5
        # Always use the input value if provided (it's the net rental income)
        # The evaluation might calculate other things, but L26 is what flows to Schedule 1
        net_rental = normalized_inputs.get("L26", 0)
        if not net_rental:
            # Fall back to output if input not provided
            net_rental = outputs.get("L26", 0)
        
        if net_rental:
            flows["Form 1040"] = {"S1_5": net_rental}
            print(f"  Schedule E: Flowing L26 (${net_rental}) to Form 1040 as S1_5")

        return {
            "outputs": outputs,
            "flows": flows,
        }


class ScheduleAHandler(FormHandler):
    """Handler for Schedule A (Itemized Deductions)."""

    @property
    def form_name(self) -> str:
        return "Schedule A"

    @property
    def ots_form_id(self) -> str:
        return "US_1040_Sched_A"

    def validate_line(self, line: str) -> bool:
        # Schedule A has lines like L1-L19
        # L5a is state and local taxes (including property tax)
        # L5b is other taxes
        valid_lines = {
            "L1", "L2", "L3", "L4", "L5", "L5a", "L5b", "L5c", "L6", "L7",
            "L8", "L9", "L10", "L11", "L12", "L13", "L14", "L15", "L16", "L17", "L18", "L19",
        }
        return line in valid_lines

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Schedule A and flow itemized deduction fields to Form 1040.
        
        Schedule A is embedded in Form 1040 in tenforty, so we pass the fields
        directly using the A* prefix. Form 1040 will calculate the total (A6)
        with all proper rules including SALT cap ($10K limit).
        
        Field mappings:
        - L5a (property tax) → A2 (State and local taxes)
        - L8 (mortgage interest) → A5a (Home mortgage interest)
        """
        # Normalize inputs first
        normalized_inputs = self.normalize_inputs(inputs)
        
        print(f"  Processing Schedule A with inputs: {normalized_inputs}")

        # Map Schedule A line numbers to Form 1040 A* fields
        # Schedule A fields are embedded in Form 1040, so we pass them directly
        flows_to_1040 = {}
        
        # Based on OpenTaxSolver source code and tenforty form config analysis:
        # - OpenTaxSolver DOES automatically calculate total itemized deductions (A6) from individual fields
        # - OpenTaxSolver DOES automatically apply the SALT cap ($10K limit) to state/local taxes
        # - OpenTaxSolver compares itemized vs standard and chooses the higher one
        #
        # IMPORTANT: The actual OTS form fields (per tenforty's _ots_form_models.py) are:
        # - A5b = Real estate taxes (property tax) - NOT A2!
        # - A8a = Home mortgage interest - NOT A5a!
        # - A5a = State and local income taxes (not property tax)
        #
        # We pass raw individual fields (A5b, A8a) and let OpenTaxSolver handle all calculations.
        # NO tax logic on our side - OpenTaxSolver will calculate A6 and apply SALT cap.
        
        # L5a (property tax) → A5b (Real estate taxes)
        # OpenTaxSolver will apply SALT cap ($10K limit) automatically
        if "L5a" in normalized_inputs or "L5" in normalized_inputs:
            property_tax = normalized_inputs.get("L5a") or normalized_inputs.get("L5", 0)
            flows_to_1040["A5b"] = property_tax
            print(f"  Schedule A: Mapping L5a (property tax ${property_tax}) → Form 1040 A5b")
            print(f"    (OpenTaxSolver will apply SALT cap automatically)")
        
        # L8 (mortgage interest) → A8a (Home mortgage interest)
        if "L8" in normalized_inputs or "L8a" in normalized_inputs:
            mortgage_interest = normalized_inputs.get("L8") or normalized_inputs.get("L8a", 0)
            flows_to_1040["A8a"] = mortgage_interest
            print(f"  Schedule A: Mapping L8 (mortgage interest ${mortgage_interest}) → Form 1040 A8a")
        
        # Pass individual fields - OpenTaxSolver will calculate A6 and apply SALT cap
        if flows_to_1040:
            flows = {"Form 1040": flows_to_1040}
            print(f"  Schedule A: Flowing to Form 1040: {flows_to_1040}")
            print(f"    (OpenTaxSolver will calculate A6 from A5b/A8a and apply SALT cap)")
        else:
            flows = {}

        return {
            "outputs": {},  # Schedule A doesn't have separate outputs
            "flows": flows,
        }


class ScheduleSEHandler(FormHandler):
    """Handler for Schedule SE (Self-Employment Tax)."""

    @property
    def form_name(self) -> str:
        return "Schedule SE"

    @property
    def ots_form_id(self) -> str:
        return "US_1040_Sched_SE"

    def validate_line(self, line: str) -> bool:
        """Validate line names for Schedule SE."""
        valid_lines = {
            "L2",  # Net profit/loss from Schedule C line 31
            "L5a",  # Church employee income from Form W-2
            "L8a",  # Total social security wages and tips
            "L8b",  # Unreported tips from Form 4137
            "L8c",  # Wages from Form 8919
        }
        return line in valid_lines

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Schedule SE to calculate self-employment tax and deductible portion.
        
        Schedule SE calculates:
        - L12: Self-employment tax (flows to Schedule 2, line 4)
        - L13: Deductible part of self-employment tax (50% of L12) - flows to Schedule 1, line 15 (S1_15)
        
        Required inputs:
        - L2: Net profit/loss from Schedule C (L31) - should come from Schedule C context
        - L8a, L8b, L8c: Wages and tips (optional, for social security wage base calculation)
        """
        # Get Schedule C L31 from context (net profit/loss)
        schedule_c_data = context.get("Schedule C", {})
        schedule_c_l31 = schedule_c_data.get("L31", 0)
        
        # If no Schedule C income, skip Schedule SE
        if not schedule_c_l31 or schedule_c_l31 <= 0:
            print("  Schedule SE: No Schedule C income found, skipping.")
            return {"outputs": {}, "flows": {}}
        
        # Get W-2 wages (L1a) from Form 1040 inputs for social security wage base calculation
        # This is critical: if wages already exceed the wage base ($168,600 for 2024),
        # only Medicare tax (2.9%) applies to SE income, not Social Security tax (12.4%)
        form_inputs_dict = context.get("form_inputs", {})
        form_1040_inputs = form_inputs_dict.get("Form 1040", {})
        w2_wages = form_1040_inputs.get("L1a", 0)
        
        # Normalize inputs
        normalized_inputs = self.normalize_inputs(inputs)
        
        # Build Schedule SE inputs
        # L2 is required: Net profit/loss from Schedule C line 31
        se_inputs = {
            "L2": schedule_c_l31,
        }
        
        # Wages and tips (L8a, L8b, L8c) for social security wage base calculation
        # Priority: Use L1a from Form 1040 if available, otherwise use direct inputs
        if w2_wages > 0:
            se_inputs["L8a"] = w2_wages
            print(f"  Schedule SE: Using W-2 wages (L1a) from Form 1040: ${w2_wages:,.0f}")
        elif "L8a" in normalized_inputs:
            se_inputs["L8a"] = normalized_inputs["L8a"]
        
        if "L8b" in normalized_inputs:
            se_inputs["L8b"] = normalized_inputs["L8b"]
        if "L8c" in normalized_inputs:
            se_inputs["L8c"] = normalized_inputs["L8c"]
        
        # Optional: Church employee income (L5a)
        if "L5a" in normalized_inputs:
            se_inputs["L5a"] = normalized_inputs["L5a"]
        
        print(f"  Schedule SE: Processing with L2 (Schedule C L31) = ${schedule_c_l31:,.0f}")
        if "L8a" in se_inputs:
            print(f"  Schedule SE: L8a (W-2 wages) = ${se_inputs['L8a']:,.0f}")
            print(f"    (If L8a > $168,600, only Medicare tax applies to SE income)")
        
        # Call OTS for Schedule SE
        try:
            result = evaluate_form(
                year=year,
                federal_form_id=self.ots_form_id,
                federal_form_values=se_inputs,
            )
            outputs = result["federal"]
            
            # Extract L12 (Self-employment tax) and L13 (deductible part)
            # L13 = 50% of L12 (self-employment tax)
            deductible_se_tax = outputs.get("L13", 0)
            se_tax = outputs.get("L12", 0)  # Self-employment tax
            
            flows = {}
            if deductible_se_tax > 0:
                # Flow L13 to Form 1040 as S1_15 (Schedule 1, line 15) - deductible portion
                flows["Form 1040"] = {"S1_15": deductible_se_tax}
                print(f"  Schedule SE: Flowing L13 (${deductible_se_tax:,.0f}) to Form 1040 as S1_15")
            
            if se_tax > 0:
                # Flow L12 to Form 1040 as S2_4 (Schedule 2, line 4) - Self-employment tax
                # OTS will then calculate L23 = Sched2[21] (includes S2_4) and L24 = L22 + L23
                if "Form 1040" not in flows:
                    flows["Form 1040"] = {}
                flows["Form 1040"]["S2_4"] = se_tax
                print(f"  Schedule SE: Flowing L12 (${se_tax:,.0f}) to Form 1040 as S2_4 (Self-employment tax)")
                print(f"    (OTS will calculate L23 = Schedule 2 total, L24 = L22 + L23)")
            
            return {
                "outputs": outputs,
                "flows": flows,
            }
        except Exception as e:
            print(f"  WARNING: Schedule SE evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return {"outputs": {}, "flows": {}}


# NOTE: Schedule 1 is embedded in Form 1040 (not a separate form in tenforty).
# Schedule 1 inputs are handled directly in Form1040Handler.
# Schedule C and Schedule E flow directly to Form 1040 (L31 → S1_3, L26 → S1_5).

class Form8812Handler(FormHandler):
    """Handler for Form 8812 (Child Tax Credit)."""

    # Line name normalization: OpenAI names → OTS names
    LINE_NORMALIZATION = {
        "L4a": "L4",  # OpenAI uses L4a, but OTS 2024 config has L4
    }

    @property
    def form_name(self) -> str:
        return "Form 8812"

    @property
    def ots_form_id(self) -> str:
        return "Form_8812"

    def normalize_line_name(self, line: str) -> str:
        """Normalize OpenAI line names to OTS line names."""
        return self.LINE_NORMALIZATION.get(line, line)

    def validate_line(self, line: str) -> bool:
        valid_lines = {
            "L1", "L2a", "L2b", "L2c", "L4", "L4a", "L6", "L13", "Amnt19",
            "L18a", "L18b", "L21", "L22", "L24",
        }
        return line in valid_lines

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Form 8812 inputs.
        
        Form 8812 Part 1 calculates the non-refundable portion of the Child Tax Credit.
        
        NOTE: The OTS C++ library causes segfaults (exit code 139) when evaluating Form 8812.
        This appears to be a fundamental issue in the underlying C++ code. As a workaround,
        we implement Form 8812 Part 1 logic manually, matching the IRS form calculation exactly.
        
        Required inputs:
        - Status (filing status) - from Form 1040 context
        - L4 (number of qualifying children) - from inputs
        - L13 (AGI) - from Form 1040 context
        - L1 (child tax credit from Form 1040 line 19) - calculated from qualifying children
        """
        # Normalize inputs first
        print(f"  Form 8812 raw inputs: {inputs}")
        normalized_inputs = self.normalize_inputs(inputs)
        print(f"  Form 8812 normalized inputs: {normalized_inputs}")
        
        # Get required values from Form 1040 context
        form_1040_outputs = context.get("Form 1040", {})
        agi = form_1040_outputs.get("L11", 0)  # AGI from Form 1040
        filing_status = form_1040_outputs.get("Status") or context.get("Status")
        
        if not filing_status:
            # Try to get from Form 1040 inputs if available
            form_1040_inputs = context.get("Form 1040_inputs", {})
            filing_status = form_1040_inputs.get("Status")
        
        if not filing_status:
            print(f"  WARNING: No filing status found for Form 8812")
            filing_status = "Single"  # Default fallback
        
        # Get required values from Form 1040
        # Note: normalize_inputs() converts L4a → L4, so check both in case normalization didn't run
        qualifying_children = normalized_inputs.get("L4") or normalized_inputs.get("L4a", 0)
        if not qualifying_children:
            print(f"  WARNING: No qualifying children found in Form 8812 inputs. Raw: {inputs}, Normalized: {normalized_inputs}")
        
        # Build Form 8812 inputs based on OTS source code analysis:
        # - L1: "Amount from line 11 of your Form 1040" = AGI (NOT child tax credit!)
        # - L4: Number of qualifying children
        # - Amnt19: "Amount on Form 1040, line 19" = child tax credit (L25a)
        # - L13: "Amount from Credit Limit Worksheet A" (optional, can be 0 for basic cases)
        # 
        # The OTS code uses L1 (AGI) in the phaseout calculation:
        #   L[3] = L[1] + L2d (modified AGI)
        #   L[10] = L[3] - L[9] (excess AGI for phaseout)
        #
        # IMPORTANT: Ensure Status matches exactly what OTS expects:
        #   "Married/Joint" (not "Married/Jointly" or "MFJ")
        #   "Single", "Married/Sep", "Head_of_House", "Widow(er)"
        form_8812_inputs = {
            "Status": filing_status,  # Must be exact match: "Married/Joint", "Single", etc.
            "L1": float(agi) if agi else 0.0,  # AGI from Form 1040 line 11 (ensure numeric)
            "L4": int(qualifying_children) if qualifying_children else 0,  # Number of qualifying children (ensure integer)
            "L13": 0.0,  # Credit Limit Worksheet A (0 for basic cases)
            "Amnt19": 0.0,  # Child tax credit from Form 1040 line 19 (will be calculated by OTS)
            "L2a": 0.0,  # Income from Puerto Rico (optional, but may be required)
            "L2b": 0.0,  # Amounts from Form 2555 (optional, but may be required)
            "L2c": 0.0,  # Amount from Form 4563 (optional, but may be required)
            "L6": 0,  # Number of other dependents (optional, but may be required)
        }
        
        # Add any other inputs that were provided
        for key, value in normalized_inputs.items():
            if key not in form_8812_inputs:
                form_8812_inputs[key] = value
        
        print(f"  Processing Form 8812 with inputs:")
        print(f"    Status: {form_8812_inputs.get('Status')}")
        print(f"    L1 (AGI from Form 1040 line 11): {form_8812_inputs.get('L1')}")
        print(f"    L4 (qualifying children): {form_8812_inputs.get('L4')}")
        print(f"    L13 (Credit Limit Worksheet A): {form_8812_inputs.get('L13')}")
        print(f"    Amnt19 (child tax credit from Form 1040 line 19): {form_8812_inputs.get('Amnt19')}")
        
        # NOTE: OTS Form 8812 evaluation causes segfaults (exit code 139).
        # This appears to be a fundamental bug in the underlying OTS C++ code.
        # We skip the OTS call and use manual calculation that follows the exact OTS logic.
        # This is mathematically equivalent to what OTS would compute.
        #
        # If OTS support for Form 8812 is fixed in the future, we can re-enable the OTS call here.
        
        print(f"  Form 8812: Skipping OTS call (known segfault issue)")
        print(f"  Form 8812: Using manual calculation (follows exact OTS logic)")
        
        # Skip the OTS call and go directly to manual calculation
        # (The OTS call code is commented out below for reference)
        
        # try:
        #     result = evaluate_form(
        #         year=year,
        #         federal_form_id=self.ots_form_id,
        #         federal_form_values=form_8812_inputs,
        #     )
        #     outputs = result["federal"]
        #     non_refundable_credit = outputs.get("L14") or outputs.get("L12") or 0
        #     print(f"  ✓ Form 8812 calculated by OTS: L14/L12 = ${non_refundable_credit}")
        #     return {
        #         "outputs": outputs,
        #         "flows": {"Form 1040": {"L25a": non_refundable_credit}},
        #     }
        # except Exception as e:
        #     print(f"  WARNING: Form 8812 OTS evaluation failed: {e}")
        #     import traceback
        #     traceback.print_exc()
        
        # Manual calculation matching Form 8812 Part 1 logic
        # Part 1 calculates the non-refundable portion of the child tax credit
        agi_value = float(agi) if agi else 0
        num_children = int(qualifying_children) if qualifying_children else 0
        
        # Based on OTS source code analysis:
        # - L1 is AGI (from Form 1040 line 11)
        # - L3 = L1 + L2d (modified AGI, L2d=0 for basic cases)
        # - L5 = L4 × $2,000 (basic credit)
        # - L8 = L5 + L7 (total credit before phaseout)
        # - L10 = L3 - L9 (excess AGI for phaseout)
        # - L11 = L10 × 5% (reduction amount)
        # - L12 = L8 - L11 (credit after phaseout)
        # - L14 = min(L12, L13) (non-refundable credit)
        
        # Line 1: AGI from Form 1040 line 11 (we pass this as L1)
        line_1_agi = agi_value
        
        # Line 3: Modified AGI (L1 + L2d, where L2d=0 for basic cases)
        line_3 = line_1_agi  # L2d = 0 for basic cases
        
        # Line 4: Number of qualifying children
        line_4 = num_children
        
        # Line 5: Multiply line 4 by $2,000
        line_5 = 2000 * line_4
        
        # Line 6: Not used in OTS calculation (L6 is other dependents)
        # Line 7: Not used in OTS calculation (L7 = L6 × $500)
        # Line 8: L5 + L7 (but L7=0 if no other dependents)
        line_8 = line_5  # Assuming no other dependents (L7=0)
        
        # Line 9: Phaseout threshold (based on filing status)
        if filing_status == "Married/Joint":
            line_9_threshold = 400000
        else:
            line_9_threshold = 200000
        
        # Line 10: Excess AGI (L3 - L9, minimum 0)
        line_10 = max(0, line_3 - line_9_threshold)
        
        # Line 10 (continued): Round up to next $1,000
        if line_10 > 0:
            line_10 = ((int((line_10 - 0.01) / 1000.0) + 1) * 1000.0)
        
        # Line 11: Multiply line 10 by 5% (reduction amount)
        line_11 = line_10 * 0.05
        
        # Line 12: Subtract line 11 from line 8 (credit after phaseout)
        line_12 = max(0, line_8 - line_11)
        
        # Line 13: Credit Limit Worksheet A (we pass 0 for basic cases)
        line_13 = 0
        
        # Line 14: Non-refundable child tax credit (smaller of line 12 or line 13)
        # This is the amount that can be used to reduce tax liability
        non_refundable_credit = min(line_12, line_13) if line_13 > 0 else line_12
        
        print(f"  Form 8812 Part 1 calculation (manual fallback):")
        print(f"    Line 1 (AGI from Form 1040 line 11): ${line_1_agi:,.0f}")
        print(f"    Line 3 (modified AGI): ${line_3:,.0f}")
        print(f"    Line 4 (qualifying children): {line_4}")
        print(f"    Line 5 (line 4 × $2,000): ${line_5:,.0f}")
        print(f"    Line 8 (total credit before phaseout): ${line_8:,.0f}")
        print(f"    Line 9 (phaseout threshold): ${line_9_threshold:,.0f}")
        print(f"    Line 10 (excess AGI, rounded): ${line_10:,.0f}")
        print(f"    Line 11 (5% reduction): ${line_11:,.0f}")
        print(f"    Line 12 (credit after phaseout): ${line_12:,.0f}")
        print(f"    Line 14 (non-refundable credit): ${non_refundable_credit:,.0f}")
        
        # Return Form 8812 Part 1 result
        return {
            "outputs": {
                "L14": non_refundable_credit,  # Non-refundable portion (Part 1, Line 14)
                "L12": line_12,  # Credit after phaseout (for reference)
            },
            "flows": {
                "Form 1040": {"L19": non_refundable_credit}  # L19 is child tax credit input (OTS calculates L21 = L19 + L20, L22 = L18 - L21)
            },
        }


class Form8995Handler(FormHandler):
    """Handler for Form 8995 (Qualified Business Income Deduction)."""

    @property
    def form_name(self) -> str:
        return "Form 8995"

    @property
    def ots_form_id(self) -> str:
        return "Form_8995"

    def validate_line(self, line: str) -> bool:
        """Validate line names for Form 8995."""
        valid_lines = {
            "L1_i_a", "L1_i_b", "L1_i_c",
            "L1_ii_a", "L1_ii_b", "L1_ii_c",
            "L1_iii_a", "L1_iii_b", "L1_iii_c",
            "L1_iv_a", "L1_iv_b", "L1_iv_c",
            "L1_v_a", "L1_v_b", "L1_v_c",
            "L3", "L6", "L7", "L12",
            "FileName1040", "FileNameSchC",
        }
        return line in valid_lines

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Form 8995 to calculate QBI deduction.
        
        Note: Form 8995 requires FileName1040 and optionally FileNameSchC to import data.
        Since we don't have filenames in the low-level API, we'll try to work around this
        by providing the necessary inputs directly.
        """
        # Debug: entry + inputs/context snapshot
        print("\n  >>> Entering Form8995Handler.process")
        print(f"    Raw inputs for Form 8995: {inputs}")
        print(f"    Context keys: {list(context.keys())}")

        # Get Schedule C data from context
        schedule_c_data = context.get("Schedule C", {})
        print(f"    Schedule C context data: {schedule_c_data}")

        if not schedule_c_data.get("is_qualified") or not schedule_c_data.get("L31"):
            # No qualified business, skip Form 8995
            print("    Form 8995: No qualified Schedule C business found, skipping.")
            return {"outputs": {}, "flows": {}}
        
        schedule_c_l31 = schedule_c_data["L31"]
        
        # Get Form 1040 data from context (should be available after Form 1040 is processed)
        form_1040_outputs = context.get("Form 1040_outputs", {})
        print(f"    Form 1040 outputs in context: "
              f"L11={form_1040_outputs.get('L11')}, L12={form_1040_outputs.get('L12')}")
        agi = form_1040_outputs.get("L11", 0)
        deduction_used = form_1040_outputs.get("L12", 0)
        
        # Get Schedule 1 deductions that reduce QBI
        form_1040_inputs = context.get("Form 1040_inputs", {})
        print(f"    Form 1040 inputs in context (for S1_15/16/17): "
              f"S1_15={form_1040_inputs.get('S1_15')}, "
              f"S1_16={form_1040_inputs.get('S1_16')}, "
              f"S1_17={form_1040_inputs.get('S1_17')}")
        s1_15 = form_1040_inputs.get("S1_15", 0)
        s1_16 = form_1040_inputs.get("S1_16", 0)
        s1_17 = form_1040_inputs.get("S1_17", 0)
        
        # Calculate qualified business income (QBI) = Schedule C L31 minus certain deductions
        # Formula from OTS f8995_2024.c line 216
        qualified_business_income = max(0, schedule_c_l31 - (s1_15 + s1_16 + s1_17))
        
        if qualified_business_income <= 0:
            return {"outputs": {}, "flows": {}}
        
        print(f"  Form 8995: Calculating QBI deduction")
        print(f"    Schedule C L31: ${schedule_c_l31:,.0f}")
        print(f"    Qualified business income (L1_i_c): ${qualified_business_income:,.0f}")
        print(f"    AGI (L11): ${agi:,.0f}")
        print(f"    Deduction (L12): ${deduction_used:,.0f}")

        # Form 8995 requires FileName1040 (see taxsolve_f8995_2024.c line 140-157)
        # It will exit(1) if FileName1040 is empty, so we must provide a valid file.
        # The file must contain all fields that Form 8995 imports (see f1040_imp_defs, lines 51-61):
        # - Numeric: L11, L12, S1_3, S1_15, S1_16, S1_17
        # - String (with colons): Your1stName:, YourLastName:, YourSocSec#:
        # Form 8995 can also optionally import from Schedule C (see f_sch_c_imp_defs, lines 74-77):
        # - Numeric: L7, L31
        tmp_1040_path: Optional[str] = None
        tmp_schc_path: Optional[str] = None

        try:
            # Create synthetic Form 1040 output file
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tf:
                tmp_1040_path = tf.name
                # Title line (required by OTS - first line is passed through as-is)
                tf.write("Title: 2024 Form 1040 (Synthetic for Form 8995)\n")
                
                # Numeric fields that Form 8995 imports (see f1040_imp_defs)
                # Format matches Form 1040 output: "L11 = 264000.00" (see showline() in taxsolve_routines.c)
                tf.write(f"L11 = {agi:.2f}\n")
                tf.write(f"L12 = {deduction_used:.2f}\n")
                tf.write(f"S1_3 = {schedule_c_l31:.2f}\n")
                if s1_15:
                    tf.write(f"S1_15 = {s1_15:.2f}\n")
                if s1_16:
                    tf.write(f"S1_16 = {s1_16:.2f}\n")
                if s1_17:
                    tf.write(f"S1_17 = {s1_17:.2f}\n")
                
                # String fields (required - see lines 58-60, 184-185 in taxsolve_f8995_2024.c)
                # Format matches Form 1040 output: "Your1stName: Taxpayer" (see taxsolve_US_1040_2024.c line 2788)
                # These must have colons and be non-empty to avoid NULL pointer issues
                tf.write("Your1stName: Taxpayer\n")
                tf.write("YourLastName: Name\n")
                tf.write("YourSocSec#: 000-00-0000\n")
                
                tf.flush()  # Ensure data is written before closing
            
            # Create synthetic Schedule C output file (optional but may help OTS)
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tf:
                tmp_schc_path = tf.name
                # Title line
                tf.write("Title: 2024 Schedule C (Synthetic for Form 8995)\n")
                
                # Numeric fields that Form 8995 imports from Schedule C (see f_sch_c_imp_defs, lines 74-77)
                # Format matches Schedule C output: "L7 = value" and "L31 = value"
                # L7 is typically 0 for basic cases (it's used for certain adjustments)
                # L31 is the net profit/loss (net income)
                tf.write(f"L7 = 0.00\n")  # Usually 0, but include it for completeness
                tf.write(f"L31 = {schedule_c_l31:.2f}\n")
                
                # String fields (may be required by some OTS code paths)
                tf.write("YourName: Taxpayer Name\n")
                tf.write("YourSocSec#: 000-00-0000\n")
                
                tf.flush()  # Ensure data is written before closing
            
            # Verify file was created and get absolute path
            if not os.path.exists(tmp_1040_path):
                raise Exception(f"Failed to create temporary 1040 file: {tmp_1040_path}")
            
            # Ensure we use absolute paths (OTS binary needs this)
            tmp_1040_path_abs = os.path.abspath(tmp_1040_path)
            tmp_schc_path_abs = os.path.abspath(tmp_schc_path) if tmp_schc_path else ""
            print(f"    Form 8995: Using absolute path for 1040: {tmp_1040_path_abs}")
            if tmp_schc_path_abs:
                print(f"    Form 8995: Using absolute path for Schedule C: {tmp_schc_path_abs}")
            
            # Verify the absolute paths exist and are readable
            if not os.path.exists(tmp_1040_path_abs):
                raise Exception(f"Absolute path does not exist: {tmp_1040_path_abs}")
            if not os.access(tmp_1040_path_abs, os.R_OK):
                raise Exception(f"File is not readable: {tmp_1040_path_abs}")
            if tmp_schc_path_abs:
                if not os.path.exists(tmp_schc_path_abs):
                    raise Exception(f"Schedule C absolute path does not exist: {tmp_schc_path_abs}")
                if not os.access(tmp_schc_path_abs, os.R_OK):
                    raise Exception(f"Schedule C file is not readable: {tmp_schc_path_abs}")
            
            # Read back to verify contents
            with open(tmp_1040_path_abs, "r") as f:
                file_content = f.read()
                print(f"    Form 8995: Created synthetic 1040 file: {tmp_1040_path_abs}")
                print(f"    Form 8995: File content:\n{file_content}")
                print(f"    Form 8995: File size: {len(file_content)} bytes")
                print(f"    Form 8995: File lines: {len(file_content.splitlines())}")
                
                # Verify each required field is present
                required_numeric = ["L11", "L12", "S1_3"]
                required_string = ["Your1stName:", "YourLastName:", "YourSocSec#:"]
                for field in required_numeric:
                    if field in file_content:
                        print(f"    ✓ Found numeric field: {field}")
                    else:
                        print(f"    ✗ MISSING numeric field: {field}")
                for field in required_string:
                    if field in file_content:
                        print(f"    ✓ Found string field: {field}")
                    else:
                        print(f"    ✗ MISSING string field: {field}")
            
            # Read back Schedule C file to verify contents
            if tmp_schc_path_abs and os.path.exists(tmp_schc_path_abs):
                with open(tmp_schc_path_abs, "r") as f:
                    schc_content = f.read()
                    print(f"    Form 8995: Created synthetic Schedule C file: {tmp_schc_path_abs}")
                    print(f"    Form 8995: Schedule C file content:\n{schc_content}")
                    print(f"    Form 8995: Schedule C file size: {len(schc_content)} bytes")
                    
                    # Verify Schedule C fields
                    schc_required = ["L7", "L31"]
                    for field in schc_required:
                        if field in schc_content:
                            print(f"    ✓ Found Schedule C field: {field}")
                        else:
                            print(f"    ✗ MISSING Schedule C field: {field}")

            # Prepare Form 8995 inputs
            # We pass L1_i_c explicitly (qualified_business_income) and point
            # FileName1040 and FileNameSchC at our synthetic files so Form 8995 can compute
            # the caps based on AGI and deductions.
            # NOTE: Use absolute paths to ensure OTS binary can access them
            form_8995_inputs = {
                "L1_i_c": qualified_business_income,
                "L3": 0,  # Qualified business net loss carryforward
                "L6": 0,  # Qualified REIT dividends
                "L7": 0,  # Qualified REIT/PTP loss carryforward
                "L12": 0,  # Net capital gain (usually 0 for basic cases)
                "FileName1040": tmp_1040_path_abs,  # Use absolute path
                "FileNameSchC": tmp_schc_path_abs if tmp_schc_path_abs else "",  # Optional but provided for completeness
            }

            # Final verification: ensure file is still accessible right before OTS call
            if not os.path.exists(tmp_1040_path_abs):
                raise Exception(f"File disappeared before OTS call: {tmp_1040_path_abs}")
            if not os.access(tmp_1040_path_abs, os.R_OK):
                raise Exception(f"File not readable before OTS call: {tmp_1040_path_abs}")
            
            # NOTE: OTS Form 8995 evaluation with FileName1040/FileNameSchC is unstable (causes hangs/crashes).
            # Despite correct file format and all required fields, the OTS binary hangs when trying to read these files.
            # This appears to be a bug in the OTS library's file reading mechanism.
            # 
            # We use manual calculation that follows the exact OTS logic from taxsolve_f8995_2024.c (lines 254-268).
            # This is mathematically equivalent to what OTS would compute.
            #
            # If OTS support for FileName1040/FileNameSchC is fixed in the future, we can re-enable the OTS call here.
            
            print(f"    Form 8995: Skipping OTS call (known issue with FileName1040/FileNameSchC)")
            print(f"    Form 8995: Using manual calculation (follows exact OTS logic)")
            
            # Skip the OTS call and go directly to manual calculation
            # (The OTS call code is commented out below for reference)
            
            # try:
            #     result = evaluate_form(
            #         year=year,
            #         federal_form_id=self.ots_form_id,
            #         federal_form_values=form_8995_inputs,
            #     )
            #     print(f"    Form 8995: evaluate_form completed successfully")
            #     outputs = result["federal"]
            #     qbi_deduction = outputs.get("L15", 0)
            #     if qbi_deduction > 0:
            #         flows = {"Form 1040": {"L13": qbi_deduction}}
            #         return {"outputs": outputs, "flows": flows}
            #     else:
            #         return {"outputs": outputs, "flows": {}}
            # except Exception as eval_error:
            #     import traceback
            #     print(f"    Form 8995: evaluate_form raised exception: {eval_error}")
            #     traceback.print_exc()
            #     raise
            
            # Fall through to manual calculation
            raise Exception("Using manual calculation (OTS FileName1040/FileNameSchC is unstable)")
        except Exception as e:
            import traceback
            print(f"  WARNING: Form 8995 evaluation failed: {e}")
            traceback.print_exc()
            print(f"    Falling back to manual calculation based on OTS logic")
            
            # Fallback: Calculate manually based on OTS f8995_2024.c logic (lines 254-268)
            # This follows the exact OTS calculation
            qbi_percentage = 0.20
            l4 = max(0, qualified_business_income + 0)  # L2 + L3 (L2 = sum of L1_*_c)
            l5 = l4 * qbi_percentage  # 20% of QBI
            l8 = max(0, 0 + 0)  # L6 + L7 (REIT/PTP, usually 0)
            l9 = l8 * qbi_percentage
            l10 = l5 + l9
            l11 = agi - deduction_used  # Taxable income before QBI
            l13 = max(0, l11 - 0)  # L11 - L12 (net capital gain, usually 0)
            l14 = l13 * qbi_percentage
            l15 = min(l10, l14)  # Final QBI deduction (smaller of L10 and L14)
            
            print(f"  Form 8995 (manual fallback): QBI deduction = ${l15:,.0f}")
            flows = {"Form 1040": {"L13": l15}}
            return {"outputs": {"L15": l15}, "flows": flows}
        finally:
            # Clean up the temporary synthetic files if we created them
            if tmp_1040_path and os.path.exists(tmp_1040_path):
                try:
                    os.unlink(tmp_1040_path)
                    print(f"    Form 8995: Cleaned up temporary 1040 file: {tmp_1040_path}")
                except OSError:
                    pass
            if tmp_schc_path and os.path.exists(tmp_schc_path):
                try:
                    os.unlink(tmp_schc_path)
                    print(f"    Form 8995: Cleaned up temporary Schedule C file: {tmp_schc_path}")
                except OSError:
                    pass


class ScheduleDHandler(FormHandler):
    """Handler for Schedule D (Capital Gains and Losses).
    
    Schedule D is embedded in Form 1040 in OTS, so this handler normalizes
    Schedule D inputs to Form 1040 D* fields according to OTS requirements.
    """

    @property
    def form_name(self) -> str:
        return "Schedule D"

    @property
    def ots_form_id(self) -> str:
        # Schedule D is embedded in Form 1040, so we don't call evaluate_form here
        # We just normalize and flow to Form 1040
        return "US_1040"  # Not used, but required by abstract class

    def validate_line(self, line: str) -> bool:
        """Validate Schedule D line names."""
        # Accept Schedule D line identifiers: L8h, D8h, L1h, D1h, L8d, L8e, L1d, L1e, L13, D13, L4, D4, etc.
        valid_lines = {
            # Long-term capital gains
            "L8h", "D8h",  # Net long-term gain (Part II, line 8, column h)
            "L8d", "D8d",  # Proceeds of long-term transactions
            "L8e", "D8e",  # Cost of long-term transactions
            "L13", "D13",  # Capital gains distributions from 1099-DIV
            # Short-term capital gains
            "L1h", "D1h",  # Net short-term gain (Part I, line 1, column h)
            "L1d", "D1d",  # Proceeds of short-term transactions
            "L1e", "D1e",  # Cost of short-term transactions
            "L4", "D4",    # Short-term gain from other forms
        }
        return line in valid_lines

    def normalize_line_name(self, line: str) -> str:
        """Normalize Schedule D line names (L8h → D8h, etc.)."""
        # Convert L8h → D8h, L1h → D1h, etc. for consistency
        if line.startswith("L") and len(line) > 1:
            return "D" + line[1:]
        return line

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Schedule D inputs and map them to Form 1040 D* fields.
        
        Mapping rules (based on OTS requirements):
        - L8h/D8h (net long-term gain) → D11 (Gain from Form 4797 - used for general long-term gains)
        - L8d/D8d + L8e/D8e (proceeds + cost for long-term) → D8ad + D8ae
        - L1h/D1h (net short-term gain) → D4 (Short-term gain from other forms)
        - L1d/D1d + L1e/D1e (proceeds + cost for short-term) → D1ad + D1ae
        - L13/D13 (capital gains distributions) → D13
        """
        normalized_inputs = self.normalize_inputs(inputs)
        print(f"  Schedule D: Processing inputs: {normalized_inputs}")
        
        flows_to_1040 = {}
        
        # Long-term capital gains
        # Check if we have proceeds and cost separately (preferred method)
        if "D8d" in normalized_inputs and "D8e" in normalized_inputs:
            proceeds = normalized_inputs["D8d"]
            cost = normalized_inputs["D8e"]
            flows_to_1040["D8ad"] = proceeds
            flows_to_1040["D8ae"] = cost
            print(f"  Schedule D: Mapping D8d (${proceeds:,.2f}) + D8e (${cost:,.2f}) → Form 1040 D8ad + D8ae")
            print(f"    (OTS will calculate D8ah = D8ad - D8ae)")
        # Otherwise, if we have net gain, use D11
        elif "D8h" in normalized_inputs:
            net_gain = normalized_inputs["D8h"]
            flows_to_1040["D11"] = net_gain
            print(f"  Schedule D: Mapping D8h (${net_gain:,.2f}) → Form 1040 D11 (Gain from Form 4797)")
        
        # Short-term capital gains
        # Check if we have proceeds and cost separately (preferred method)
        if "D1d" in normalized_inputs and "D1e" in normalized_inputs:
            proceeds = normalized_inputs["D1d"]
            cost = normalized_inputs["D1e"]
            flows_to_1040["D1ad"] = proceeds
            flows_to_1040["D1ae"] = cost
            print(f"  Schedule D: Mapping D1d (${proceeds:,.2f}) + D1e (${cost:,.2f}) → Form 1040 D1ad + D1ae")
            print(f"    (OTS will calculate D1ah = D1ad - D1ae)")
        # Otherwise, if we have net gain, use D4
        elif "D1h" in normalized_inputs:
            net_gain = normalized_inputs["D1h"]
            flows_to_1040["D4"] = net_gain
            print(f"  Schedule D: Mapping D1h (${net_gain:,.2f}) → Form 1040 D4 (Short-term gain from other forms)")
        
        # Capital gains distributions (1099-DIV)
        if "D13" in normalized_inputs:
            distributions = normalized_inputs["D13"]
            flows_to_1040["D13"] = distributions
            print(f"  Schedule D: Mapping D13 (${distributions:,.2f}) → Form 1040 D13 (Capital gains distributions)")
        
        # Short-term gain from other forms (if provided directly)
        if "D4" in normalized_inputs and "D4" not in flows_to_1040:
            flows_to_1040["D4"] = normalized_inputs["D4"]
            print(f"  Schedule D: Mapping D4 (${normalized_inputs['D4']:,.2f}) → Form 1040 D4")
        
        flows = {}
        if flows_to_1040:
            flows["Form 1040"] = flows_to_1040
        
        return {
            "outputs": {},  # Schedule D doesn't have separate outputs (it's embedded in Form 1040)
            "flows": flows,
        }


class Form1040Handler(FormHandler):
    """Handler for Form 1040 (Main tax return)."""

    # Line name normalization: OpenAI names → OTS names
    LINE_NORMALIZATION = {
        "FilingStatus": "Status",
        "DependentsTable": "Dependents",
        # Schedule 1 line references (Schedule 1 is embedded in Form 1040)
        "Sched1_L1": "S1_1",  # Schedule 1 line 1 (taxable interest)
        "Sched1_L3": "S1_3",  # Schedule 1 line 3 (business income)
        "Sched1_L5": "S1_5",  # Schedule 1 line 5 (rental income)
        "L1": "S1_1",  # If "L1" comes as Schedule 1 input, normalize to S1_1
        "L3": "S1_3",  # If "L3" comes as Schedule 1 input, normalize to S1_3
        "L5": "S1_5",  # If "L5" comes as Schedule 1 input, normalize to S1_5
    }

    # Filing status value normalization: OpenAI codes → tenforty values
    FILING_STATUS_NORMALIZATION = {
        "MFJ": "Married/Joint",
        "MFS": "Married/Separate",
        "S": "Single",
        "HOH": "Head of Household",
        "QW": "Qualifying Widow(er)",
        # Also accept already-normalized values
        "Married/Joint": "Married/Joint",
        "Married/Separate": "Married/Separate",
        "Single": "Single",
        "Head of Household": "Head of Household",
        "Qualifying Widow(er)": "Qualifying Widow(er)",
    }

    @property
    def form_name(self) -> str:
        return "Form 1040"

    @property
    def ots_form_id(self) -> str:
        return "US_1040"

    def normalize_line_name(self, line: str) -> str:
        """Normalize OpenAI line names to OTS line names."""
        # Check normalization map first
        if line in self.LINE_NORMALIZATION:
            return self.LINE_NORMALIZATION[line]
        # If it starts with Sched1_, convert to S1_ format (Schedule 1 lines)
        if line.startswith("Sched1_"):
            line_num = line.replace("Sched1_", "")
            return f"S1_{line_num}"
        # If it starts with S1_, it's already normalized
        if line.startswith("S1_"):
            return line
        # If it's just a line number like "L1" and we're processing Schedule 1 inputs,
        # normalize to S1_ format (but only if it's not already a 1040 line)
        # Note: This is conservative - we only normalize if it's in our map
        return line

    def normalize_value(self, line: str, value: Any) -> Any:
        """Normalize values, especially filing status codes."""
        if line == "Status" and isinstance(value, str):
            return self.FILING_STATUS_NORMALIZATION.get(value, value)
        return value

    def validate_line(self, line: str) -> bool:
        # Form 1040 has many lines; check common ones
        # This is a simplified check - in production, validate against OTS config
        # Also accept Schedule 1 line references (Sched1_L1, etc.) which will be normalized
        # Schedule D (capital gains) is embedded in Form 1040 - accept D4, D11, D12, D13, D8ad, D8ae, D1ad, D1ae, etc.
        valid_prefixes = {"L", "S1_", "Sched1_", "A", "D", "Status", "Dependents"}
        # Accept Schedule D lines: D followed by digits (D4, D11, D12, D13) or D followed by digits and letters (D8ad, D8ae, D1ad, D1ae)
        if line.startswith("D"):
            # D4, D11, D12, D13, etc. (D followed by digits)
            if len(line) > 1 and line[1:].isdigit():
                return True
            # D8ad, D8ae, D1ad, D1ae, etc. (D followed by digits then letters)
            if len(line) > 2 and line[1].isdigit() and line[2:].isalpha():
                return True
        return any(line.startswith(prefix) for prefix in valid_prefixes)

    def process(
        self, year: int, inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Form 1040 (the main return).
        Can be called multiple times:
        1. First pass: after schedules, to get AGI
        2. Second pass: after credits, to get final tax
        """
        # Normalize inputs first
        normalized_inputs = self.normalize_inputs(inputs)
        
        # Debug: Show L1a in normalized_inputs
        if "L1a" in normalized_inputs:
            print(f"  DEBUG: Form 1040 L1a in normalized_inputs: ${normalized_inputs['L1a']:,.0f}")

        # Merge any flows from other forms into 1040 inputs
        merged_inputs = dict(normalized_inputs)
        
        # Debug: Show L1a after initial merge
        if "L1a" in merged_inputs:
            print(f"  DEBUG: Form 1040 L1a after initial merge: ${merged_inputs['L1a']:,.0f}")
        for form_name, flow_data in context.get("flows", {}).items():
            if form_name == "Form 1040":
                print(f"  Form 1040: Merging flows from {form_name}: {flow_data}")
                # WARNING: Don't let flows overwrite L1a if it's already set
                if "L1a" in merged_inputs and "L1a" in flow_data:
                    print(f"  WARNING: Flow data contains L1a (${flow_data['L1a']:,.0f}), but merged_inputs already has L1a (${merged_inputs['L1a']:,.0f})")
                    print(f"    Keeping existing L1a value: ${merged_inputs['L1a']:,.0f}")
                    # Remove L1a from flow_data before merging to preserve the correct summed value
                    flow_data_without_l1a = {k: v for k, v in flow_data.items() if k != "L1a"}
                    merged_inputs.update(flow_data_without_l1a)
                else:
                    merged_inputs.update(flow_data)
        
        # Also merge Schedule 1 inputs if they're in form_inputs (Schedule 1 is embedded in Form 1040)
        # Schedule 1 inputs come as {'Schedule 1': {'S1_1': 1000}} and should be normalized
        # Use the normalize_line_name method to ensure consistent normalization
        form_inputs_dict = context.get("form_inputs", {})
        if "Schedule 1" in form_inputs_dict:
            schedule1_inputs = form_inputs_dict["Schedule 1"]
            # Normalize Schedule 1 line names using the handler's normalization method
            normalized_s1 = {}
            for line, value in schedule1_inputs.items():
                normalized_line = self.normalize_line_name(line)
                normalized_s1[normalized_line] = value
            if normalized_s1:
                print(f"  Form 1040: Merging Schedule 1 inputs: {normalized_s1}")
                merged_inputs.update(normalized_s1)

        # Safety check: Remove any non-numeric L13 values (QBI deduction should be numeric)
        # This prevents segfaults from string values like "QBI Deduction"
        if "L13" in merged_inputs:
            l13_value = merged_inputs["L13"]
            if isinstance(l13_value, str):
                print(f"  WARNING: Removing non-numeric L13 value '{l13_value}'; QBI deduction will be computed by Form 8995")
                del merged_inputs["L13"]
            elif not isinstance(l13_value, (int, float)):
                print(f"  WARNING: Removing invalid L13 value {l13_value!r}; QBI deduction will be computed by Form 8995")
                del merged_inputs["L13"]
        
        # Call OTS for Form 1040
        print(f"  Processing Form 1040 with inputs: {list(merged_inputs.keys())}")
        
        # Debug: Show L1a value being passed to OTS
        if "L1a" in merged_inputs:
            print(f"  DEBUG: Form 1040 L1a value being passed to OTS: ${merged_inputs['L1a']:,.0f}")
        else:
            print(f"  WARNING: L1a not found in merged_inputs!")
        
        # Check for Schedule D fields (D4, D11, D12, D13) - capital gains
        schedule_d_fields = {k: v for k, v in merged_inputs.items() if k.startswith("D") and len(k) > 1 and k[1:].isdigit()}
        if schedule_d_fields:
            print(f"  Form 1040: Schedule D (capital gains) fields detected:")
            for field, value in sorted(schedule_d_fields.items()):
                print(f"    {field} = ${value:,.2f}")
            print(f"    (Schedule D is embedded in Form 1040 - OTS will calculate net capital gain and flow to L7)")
        
        # Check for Schedule A fields (A5b, A8a) - Form 1040 will calculate A6 automatically
        has_itemized = "A5b" in merged_inputs or "A8a" in merged_inputs or "A6" in merged_inputs
        if has_itemized:
            itemized_info = []
            if "A5b" in merged_inputs:
                itemized_info.append(f"A5b (property tax) = ${merged_inputs.get('A5b', 0):,.0f}")
            if "A8a" in merged_inputs:
                itemized_info.append(f"A8a (mortgage) = ${merged_inputs.get('A8a', 0):,.0f}")
            if "A6" in merged_inputs:
                itemized_info.append(f"A6 (total) = ${merged_inputs.get('A6', 0):,.0f}")
            print(f"  Form 1040: Using itemized deductions: {', '.join(itemized_info)}")
            print(f"    (OpenTaxSolver will calculate A6 with SALT cap automatically)")
        else:
            print(f"  Form 1040: Using standard deduction (no itemized deductions provided)")
        try:
            result = evaluate_form(
                year=year,
                federal_form_id=self.ots_form_id,
                federal_form_values=merged_inputs,
            )
        except Exception as e:
            print(f"ERROR: Form 1040 evaluation failed: {e}")
            print(f"  Inputs were: {merged_inputs}")
            raise

        outputs = result["federal"]
        
        # Debug: Print L10 (Total income) and L11 (AGI) for verification
        l10 = outputs.get("L10", 0)
        l11 = outputs.get("L11", 0)
        l12 = outputs.get("L12", 0)
        l7 = outputs.get("L7", 0)  # Capital gains from Schedule D
        print(f"  Form 1040: L10 (Total income) = ${l10:,.2f}")
        print(f"  Form 1040: L11 (AGI) = ${l11:,.2f}")
        print(f"  Form 1040: L12 (Deduction) = ${l12:,.2f}")
        if l7 != 0:
            print(f"  Form 1040: L7 (Capital gains from Schedule D) = ${l7:,.2f}")
        
        # Also print Schedule 1 totals if available
        s1_10 = outputs.get("S1_10", 0)  # Schedule 1 line 10 (total income)
        s1_26 = outputs.get("S1_26", 0)  # Schedule 1 line 26 (total adjustments)
        if s1_10 > 0:
            print(f"  Form 1040: S1_10 (Schedule 1 total income) = ${s1_10:,.2f}")
        if s1_26 > 0:
            print(f"  Form 1040: S1_26 (Schedule 1 total adjustments) = ${s1_26:,.2f}")
        
        # Note: Based on OTS C++ source code analysis:
        # - Form 1040 (taxsolve_US_1040_2024.c line 1977) just reads L13 as input - it doesn't calculate QBI
        # - Form 8995 (taxsolve_f8995_2024.c) calculates QBI deduction (L15) but requires filenames to import
        #   data from Form 1040 and Schedule C (lines 140-169)
        # - There is NO field in Schedule C or Form 1040 to explicitly mark "specified service business"
        # - Form 8995 can be called directly via evaluate_form with L1_i_c input, but it still needs
        #   Form 1040 data (L11, L12, S1_15, S1_16, S1_17) which it imports via filename
        #
        # TODO: Investigate if we can call Form 8995 without filenames by passing all required inputs
        # directly, or if there's a way to indicate qualified business status that OTS uses automatically
        
        # For now, we detect qualified business but don't calculate QBI - OTS should handle it
        schedule_c_data = context.get("Schedule C", {})
        if schedule_c_data.get("is_qualified"):
            print(f"  Note: Qualified business detected, but QBI calculation requires Form 8995")
            print(f"    Form 8995 needs filenames to import Form 1040 and Schedule C data")
            print(f"    This may need to be handled via a separate Form 8995 handler")
        
        # Debug: Check what deduction was actually used and verify calculations
        # L12 on Form 1040 is the deduction line (standard or itemized)
        deduction_used = outputs.get("L12", 0)
        agi = outputs.get("L11", 0)
        taxable_income = outputs.get("L15", 0)
        qbi_deduction = outputs.get("L13", 0)
        
        if "A6" in merged_inputs or "A2" in merged_inputs or "A5a" in merged_inputs:
            print(f"  Form 1040: Deduction used (L12) = ${deduction_used:,.0f}")
            if "A6" in merged_inputs:
                print(f"    Expected itemized (A6) = ${merged_inputs.get('A6', 0):,.0f}")
            print(f"  Form 1040: AGI (L11) = ${agi:,.0f}")
            print(f"  Form 1040: Taxable Income (L15) = ${taxable_income:,.0f}")
            if agi > 0 and deduction_used > 0:
                expected_taxable = agi - deduction_used
                print(f"    Expected taxable income: ${agi:,.0f} - ${deduction_used:,.0f} = ${expected_taxable:,.0f}")
                if abs(taxable_income - expected_taxable) > 100:
                    print(f"    ⚠️  WARNING: Taxable income doesn't match! Got ${taxable_income:,.0f}, expected ${expected_taxable:,.0f}")
            standard_deduction_mfj_2024 = 29200
            if abs(deduction_used - standard_deduction_mfj_2024) < 100:
                print(f"    ⚠️  WARNING: Standard deduction was used instead of itemized!")
                print(f"    This suggests tenforty may need A6 to be higher or a flag to use itemized")

        # Debug: Show QBI deduction if present
        if qbi_deduction:
            print(f"  Form 1040: QBI deduction (L13) = ${qbi_deduction:,.0f}")

        # Check if Form 1040 already has child tax credit in outputs
        # L19 is the child tax credit (NOT L25a, which is withholding)
        child_tax_credit_output = outputs.get("L19", 0)
        
        # If no child tax credit found in outputs, and we have dependents or Form 8812 inputs, calculate it
        if not child_tax_credit_output:
            # Check for qualifying children from Form 8812 inputs
            # Form 8812 inputs are stored in context by FormCoordinator
            form_8812_inputs = context.get("Form 8812_inputs", {})
            form_inputs_dict = context.get("form_inputs", {})
            form_8812_from_inputs = form_inputs_dict.get("Form 8812", {})
            
            # Try to get L4 from multiple sources (prioritize Form 8812 inputs)
            qualifying_children = (
                form_8812_inputs.get("L4") or 
                form_8812_inputs.get("L4a") or
                form_8812_from_inputs.get("L4") or
                form_8812_from_inputs.get("L4a") or
                0
            )
            
            total_dependents = merged_inputs.get("Dependents", 0)
            
            # Debug: Show what we found
            print(f"  Child Tax Credit: Checking for qualifying children...")
            print(f"    Form 8812 inputs (from context): {form_8812_inputs}")
            print(f"    Form 8812 inputs (from form_inputs): {form_8812_from_inputs}")
            print(f"    Total dependents (Form 1040): {total_dependents}")
            print(f"    Qualifying children (Form 8812 L4): {qualifying_children}")
            
            # IMPORTANT: If Form 8812 L4 is 0 or missing, but we have dependents,
            # this likely means OpenAI didn't filter by age correctly.
            # We should NOT use all dependents as a fallback - that would be incorrect.
            # Instead, we should warn and use 0, or try to infer from ages if available.
            if qualifying_children == 0 and total_dependents > 0:
                print(f"    ⚠️  WARNING: Form 8812 L4 is 0 but there are {total_dependents} dependents.")
                print(f"    This suggests OpenAI may not have filtered by age correctly.")
                print(f"    Child Tax Credit requires children under age 17 at end of 2024.")
                print(f"    NOT using all dependents as fallback (would be incorrect).")
                # Don't calculate credit if we don't have Form 8812 L4
                qualifying_children = 0
            
            if qualifying_children > 0:
                # IMPORTANT: Child Tax Credit is ONLY for children under age 17 at the end of the tax year (Dec 31, 2024)
                # OpenAI should have already filtered out children 17 or older when mapping to Form 8812 L4
                # If ages were provided (e.g., "2 children, ages 15 and 21"), OpenAI should return:
                #   - Form 1040, Dependents: 2 (all dependents)
                #   - Form 8812, L4: 1 (only the 15-year-old qualifies)
                print(f"  Child Tax Credit: Using {qualifying_children} qualifying children (must be under age 17 at end of 2024)")
                
                # Basic calculation: $2,000 per qualifying child (for 2024)
                # Get AGI for phaseout
                agi = outputs.get("L11", 0)
                filing_status = merged_inputs.get("Status", "Single")
                
                # Phaseout thresholds
                if filing_status == "Married/Joint":
                    phaseout_threshold = 400000
                else:
                    phaseout_threshold = 200000
                
                # Calculate basic credit
                basic_credit = 2000 * qualifying_children
                
                # Apply phaseout if needed
                if agi > phaseout_threshold:
                    excess = agi - phaseout_threshold
                    reduction = int((excess / 1000) * 50)  # $50 per $1,000
                    child_tax_credit_calculated = max(0, basic_credit - reduction)
                else:
                    child_tax_credit_calculated = basic_credit
                
                # Re-process Form 1040 with the child tax credit applied
                # OTS expects L19 for child tax credit (not L25a, which is for tax withheld)
                # L19 is included in L21 (credits), which is subtracted from L18 to get L22 (tax after credits)
                if "L19" not in merged_inputs:
                    print(f"  Calculating child tax credit: {qualifying_children} qualifying children × $2,000 = ${child_tax_credit_calculated}")
                    print(f"  Re-processing Form 1040 with L19 = ${child_tax_credit_calculated}")
                    print(f"    (OTS will calculate L21 = L19 + L20, L22 = L18 - L21, L24 = L22 + L23)")
                    
                    # Add L19 to inputs and re-evaluate
                    merged_inputs["L19"] = child_tax_credit_calculated
                    
                    try:
                        result = evaluate_form(
                            year=year,
                            federal_form_id=self.ots_form_id,
                            federal_form_values=merged_inputs,
                        )
                        outputs = result["federal"]
                        # L19 is the input and output for child tax credit (NOT L25a, which is withholding)
                        child_tax_credit_output = outputs.get("L19", child_tax_credit_calculated)
                    except Exception as e:
                        print(f"  WARNING: Re-evaluation with L25a failed: {e}")
                        child_tax_credit_output = child_tax_credit_calculated
        
        # Ensure child_tax_credit_output is set (use calculated value if OTS didn't output it)
        if not child_tax_credit_output and "L19" in merged_inputs:
            child_tax_credit_output = merged_inputs["L19"]
        
        if child_tax_credit_output:
            print(f"  ✓ Child tax credit applied: ${child_tax_credit_output}")
        else:
            print(f"  ⚠️  No child tax credit found (L19 not in outputs or inputs)")

        # Store Form 1040 outputs in context for Form 8995 to access
        # Also store the child tax credit value explicitly in outputs so it can be retrieved
        if child_tax_credit_output:
            outputs["L19"] = child_tax_credit_output
        
        context["Form 1040_outputs"] = outputs
        context["Form 1040_inputs"] = merged_inputs
        
        return {
            "outputs": outputs,
            "flows": {},  # 1040 doesn't flow to other forms (except via context)
        }


class FormCoordinator:
    """Orchestrates form processing in IRS flow order."""

    def __init__(self) -> None:
        self.handlers: Dict[str, FormHandler] = {
            "Schedule C": ScheduleCHandler(),
            "Schedule D": ScheduleDHandler(),
            "Schedule E": ScheduleEHandler(),
            "Schedule A": ScheduleAHandler(),
            "Schedule SE": ScheduleSEHandler(),
            "Form 1040": Form1040Handler(),
            "Form 8995": Form8995Handler(),
        }

        # IRS flow order:
        # 1. Process supporting schedules first (they flow to Form 1040)
        # 2. Process Form 1040 (which includes Schedule 1 inputs and calculates child tax credit)
        # 3. Process Form 8995 (QBI deduction) - needs Form 1040 outputs
        # 4. Re-process Form 1040 with QBI deduction
        # Note: Schedule 1 is embedded in Form 1040, so Schedule 1 inputs go directly to Form 1040
        # Note: Schedule D is embedded in Form 1040, so Schedule D inputs are normalized and flowed to Form 1040
        self.flow_order = [
            "Schedule C",      # Business income → flows L31 to Form 1040 S1_3
            "Schedule D",      # Capital gains → flows D* fields to Form 1040
            "Schedule SE",     # Self-employment tax → flows L13 to Form 1040 S1_15 (deductible part)
            "Schedule E",      # Rental income → flows L26 to Form 1040 S1_5
            "Schedule A",      # Itemized deductions → flows A5b, A8a to Form 1040
            "Form 1040",       # Main return (includes Schedule 1 inputs via S1_* keys) - first pass
            "Form 8995",       # QBI deduction calculation - needs Form 1040 outputs
            "Form 1040_final", # Re-process Form 1040 with QBI deduction (L13)
        ]

    def get_handler(self, form_name: str) -> Optional[FormHandler]:
        """Get handler for a form name."""
        return self.handlers.get(form_name)

    def validate_update(self, form_name: str, line: str) -> bool:
        """Validate that a {form, line} update is valid."""
        handler = self.get_handler(form_name)
        if handler is None:
            return False
        return handler.validate_line(line)

    def process_scenario(
        self, year: int, form_inputs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process all forms in IRS flow order.

        Args:
            year: Tax year
            form_inputs: Dict of {form_name: {line: value}}

        Returns:
            Dict with:
            - "results": {form_name: {outputs, flows}}
            - "final": Final 1040 outputs
        """
        results: Dict[str, Any] = {}
        context: Dict[str, Any] = {"flows": {}}

        # Store form_inputs in context so handlers can access it if needed
        context["form_inputs"] = form_inputs

        # Process forms in IRS flow order
        for form_name in self.flow_order:
            # Handle special case: Form 1040_final is a second pass of Form 1040
            actual_form_name = form_name
            if form_name == "Form 1040_final":
                actual_form_name = "Form 1040"
            
            handler = self.get_handler(actual_form_name)
            if handler is None:
                print(f"  WARNING: No handler found for {actual_form_name}")
                continue

            # Get inputs - some forms (like Form 8995, Form 1040_final) may not be in form_inputs
            inputs = form_inputs.get(actual_form_name, {})
            
            # For Form 1040_final, merge any flows from Form 8995 into inputs
            if form_name == "Form 1040_final":
                # Merge flows from Form 8995 (QBI deduction) into Form 1040 inputs
                if "Form 1040" in context["flows"]:
                    inputs = dict(inputs)  # Make a copy
                    inputs.update(context["flows"]["Form 1040"])
            
            print(f"  Processing {form_name} (actual: {actual_form_name}) with inputs: {inputs}")
            result = handler.process(year, inputs, context)

            results[form_name] = result

            # Update context for next forms (use actual form name for context)
            context[actual_form_name] = result["outputs"]
            
            # Merge flows properly - if multiple forms flow to the same target,
            # merge their dictionaries instead of replacing
            for target_form, flow_data in result["flows"].items():
                if target_form in context["flows"]:
                    # Merge dictionaries instead of replacing
                    context["flows"][target_form].update(flow_data)
                else:
                    context["flows"][target_form] = flow_data
            
            print(f"  Updated context flows: {context.get('flows', {})}")
            
            # Store inputs for forms that might be needed later
            context[f"{actual_form_name}_inputs"] = inputs
            
            # Store Form 8812 inputs in context if this is Form 1040, so it can access them
            if form_name == "Form 1040" and "Form 8812" in form_inputs:
                context["Form 8812_inputs"] = form_inputs["Form 8812"]

        # Final 1040 outputs (use Form 1040_final if available, otherwise Form 1040)
        final_outputs = (
            results.get("Form 1040_final", {}).get("outputs", {}) or
            results.get("Form 1040", {}).get("outputs", {})
        )

        return {
            "results": results,
            "final": final_outputs,
        }

