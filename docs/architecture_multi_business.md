# Architecture: Multi-Business Tax Calculation

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────┐
│  User Input Layer                                       │
│  - Business 1: Consulting, $100K gross, $40K expenses  │
│  - Business 2: Online Store, $80K gross, $50K expenses │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Intermediate Data Model (Separate Activities)         │
│  ┌─────────────────┐  ┌─────────────────┐             │
│  │  Business 1      │  │  Business 2     │             │
│  │  - Name          │  │  - Name         │             │
│  │  - Income        │  │  - Income       │             │
│  │  - Expenses      │  │  - Expenses     │             │
│  │  - Net Profit    │  │  - Net Profit   │             │
│  │  - Schedule C    │  │  - Schedule C   │             │
│  │    fields        │  │    fields       │             │
│  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Aggregation Layer                                      │
│  - Sum net profits                                      │
│  - Combine Schedule C data (if needed)                 │
│  - Prepare for tax engine                               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Tax Engine Interface (tenforty)                        │
│  - Single aggregated Schedule C or                      │
│  - schedule_1_income = sum of net profits               │
└─────────────────────────────────────────────────────────┘
```

## Benefits of This Architecture

### 1. **Separation of Concerns**
- Each business is a self-contained entity
- Easier to validate, modify, and track individual businesses
- Clear data ownership

### 2. **Flexibility**
- Add/remove businesses without affecting others
- Different business types can have different validation rules
- Can calculate each business separately for validation

### 3. **Better Data Modeling**
- Matches real-world structure (multiple Schedule C forms)
- Easier to generate per-business reports
- Can handle different accounting methods per business

### 4. **Maintainability**
- Changes to one business don't affect others
- Easier to debug (isolate issues to specific business)
- Better testability (test each business independently)

### 5. **Future Extensibility**
- Easy to add business-specific features
- Can support different tax treatments per business
- Can integrate with business management systems

## Implementation Example

```python
from dataclasses import dataclass
from typing import List, Optional
from tenforty import evaluate_return

@dataclass
class ScheduleCActivity:
    """Represents a single Schedule C business activity."""
    name: str
    principal_business: str
    activity_code: str
    
    # Income
    gross_receipts: float = 0.0
    returns_allowances: float = 0.0
    other_income: float = 0.0
    
    # Expenses
    advertising: float = 0.0
    car_truck: float = 0.0
    contractors: float = 0.0
    depreciation: float = 0.0
    insurance: float = 0.0
    interest: float = 0.0
    legal_professional: float = 0.0
    office_expense: float = 0.0
    rent_lease: float = 0.0
    repairs_maintenance: float = 0.0
    supplies: float = 0.0
    taxes_licenses: float = 0.0
    travel: float = 0.0
    meals_entertainment: float = 0.0
    utilities: float = 0.0
    wages: float = 0.0
    other_expenses: float = 0.0
    
    def calculate_gross_income(self) -> float:
        """Calculate gross income (Part I)."""
        return self.gross_receipts - self.returns_allowances + self.other_income
    
    def calculate_total_expenses(self) -> float:
        """Calculate total expenses (Part II)."""
        return (
            self.advertising + self.car_truck + self.contractors +
            self.depreciation + self.insurance + self.interest +
            self.legal_professional + self.office_expense +
            self.rent_lease + self.repairs_maintenance + self.supplies +
            self.taxes_licenses + self.travel + self.meals_entertainment +
            self.utilities + self.wages + self.other_expenses
        )
    
    def calculate_net_profit(self) -> float:
        """Calculate net profit or loss (Part III)."""
        return self.calculate_gross_income() - self.calculate_total_expenses()
    
    def validate(self) -> List[str]:
        """Validate the business data. Returns list of errors."""
        errors = []
        if not self.name:
            errors.append("Business name is required")
        if self.gross_receipts < 0:
            errors.append("Gross receipts cannot be negative")
        if self.calculate_net_profit() < -1000000:
            errors.append("Net loss seems unusually large")
        return errors


class TaxReturnBuilder:
    """Builds tax return from separate business activities."""
    
    def __init__(self):
        self.businesses: List[ScheduleCActivity] = []
        self.w2_income: float = 0.0
        self.other_income: float = 0.0
        self.filing_status: str = "Single"
        self.state: Optional[str] = None
        self.year: int = 2024
    
    def add_business(self, business: ScheduleCActivity):
        """Add a business activity."""
        errors = business.validate()
        if errors:
            raise ValueError(f"Business validation failed: {errors}")
        self.businesses.append(business)
    
    def calculate_total_business_income(self) -> float:
        """Aggregate net profit from all businesses."""
        return sum(business.calculate_net_profit() for business in self.businesses)
    
    def get_business_summary(self) -> dict:
        """Get summary of all businesses."""
        return {
            business.name: {
                'gross_income': business.calculate_gross_income(),
                'total_expenses': business.calculate_total_expenses(),
                'net_profit': business.calculate_net_profit()
            }
            for business in self.businesses
        }
    
    def calculate_tax(self):
        """Calculate tax using aggregated business income."""
        # Aggregate all business net profits
        total_business_income = self.calculate_total_business_income()
        
        # Pass to tax engine
        return evaluate_return(
            year=self.year,
            w2_income=self.w2_income,
            schedule_1_income=total_business_income + self.other_income,
            filing_status=self.filing_status,
            state=self.state
        )


# Usage Example
if __name__ == "__main__":
    # Create separate business activities
    business1 = ScheduleCActivity(
        name="Consulting Business",
        principal_business="Consulting",
        activity_code="541611",
        gross_receipts=100000,
        returns_allowances=0,
        advertising=5000,
        car_truck=10000,
        office_expense=5000,
        total_expenses=40000  # Simplified
    )
    
    business2 = ScheduleCActivity(
        name="Online Store",
        principal_business="Retail",
        activity_code="454110",
        gross_receipts=80000,
        returns_allowances=2000,
        advertising=3000,
        supplies=5000,
        total_expenses=50000  # Simplified
    )
    
    # Build tax return
    tax_return = TaxReturnBuilder()
    tax_return.w2_income = 100000
    tax_return.filing_status = "Married/Joint"
    tax_return.state = "CA"
    
    # Add businesses separately
    tax_return.add_business(business1)
    tax_return.add_business(business2)
    
    # Get business summary (before aggregation)
    print("Business Summary:")
    for name, details in tax_return.get_business_summary().items():
        print(f"  {name}: Net Profit = ${details['net_profit']:,.2f}")
    
    # Calculate tax (aggregation happens here)
    result = tax_return.calculate_tax()
    print(f"\nTotal Tax: ${result.total_tax:,.2f}")
```

## Advanced: Full Schedule C Support

For full Schedule C field support, you can map to OTS fields:

```python
def to_ots_schedule_c_fields(self) -> dict:
    """Convert to OTS Schedule C field format."""
    return {
        'BusinessName': self.name,
        'PrincipalBus': self.principal_business,
        'ActivityCode': self.activity_code,
        'L1': self.gross_receipts,
        'L2': self.returns_allowances,
        'L6': self.calculate_gross_income(),
        'L8': self.advertising,
        'L9': self.car_truck,
        'L10': self.contractors,
        'L11': self.depreciation,
        'L12': self.insurance,
        'L13': self.interest,
        'L14': self.legal_professional,
        'L15': self.office_expense,
        'L17': self.rent_lease,
        'L18': self.repairs_maintenance,
        'L19': self.supplies,
        'L21': self.taxes_licenses,
        'L22': self.travel,
        'L23': self.meals_entertainment,
        'L25': self.utilities,
        'L26': self.other_expenses,
        'L27': self.calculate_total_expenses(),
        'L31': self.calculate_net_profit(),
    }
```

## Aggregation Strategies

### Strategy 1: Sum Net Profits (Recommended)
```python
# Simple and clean
total_net = sum(business.calculate_net_profit() for business in businesses)
result = evaluate_return(schedule_1_income=total_net)
```

### Strategy 2: Combine Full Schedule C Data
```python
# If you need full Schedule C details in OTS
combined_sched_c = {
    'L1': sum(b.gross_receipts for b in businesses),
    'L27': sum(b.calculate_total_expenses() for b in businesses),
    # ... combine other fields
}
```

### Strategy 3: Multiple Schedule C Forms (Future)
```python
# If OTS supports multiple Schedule C forms
# Evaluate each separately, then combine results
```

## Recommendations

1. **Keep activities separate** in your data model ✅
2. **Aggregate at the boundary** when calling tax engine ✅
3. **Validate each business** before aggregation
4. **Calculate net profit per business** for reporting
5. **Use Strategy 1** (sum net profits) for simplicity
6. **Store full Schedule C data** if you need detailed reporting

This architecture gives you:
- Clean separation of concerns
- Easy to extend and maintain
- Better data integrity
- Flexible reporting
- Matches real-world tax structure

