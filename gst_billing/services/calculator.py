"""
Calculator — line-item and document totals with Decimal precision.

ALL money flows through this module.  Nothing else in the codebase
should do money arithmetic.

    Inputs  → Decimal
    Outputs → integer paise (for DB storage)
    Display → format_currency()
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from services.gst_engine import TaxBreakdown, calculate_tax

PAISE = Decimal("100")
TWO_PLACES = Decimal("0.01")


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------
@dataclass
class LineResult:
    """Computed values for a single line item — all in integer paise."""
    taxable_amount: int
    cgst_rate: float
    cgst_amount: int
    sgst_rate: float
    sgst_amount: int
    igst_rate: float
    igst_amount: int
    line_total: int


@dataclass
class DocTotals:
    """Aggregate totals for the whole document — integer paise."""
    total_taxable: int
    total_cgst: int
    total_sgst: int
    total_igst: int
    grand_total: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compute_line_item(
    quantity: float,
    rate_paise: int,
    discount_pct: float,
    gst_rate: float,
    is_intra_state: bool,
) -> LineResult:
    """Calculate a single line item's taxable amount and taxes.

    Args:
        quantity: Number of units (float, e.g. 2.5).
        rate_paise: Unit price in paise (integer).
        discount_pct: Discount as fraction 0–1 (e.g. 0.05 = 5%).
        gst_rate: Total GST percentage (e.g. 18.0).
        is_intra_state: True → CGST+SGST; False → IGST.

    Returns:
        LineResult with all money values as integer paise.
    """
    qty = Decimal(str(quantity))
    rate = Decimal(str(rate_paise)) / PAISE          # paise → rupees
    disc = Decimal(str(discount_pct))

    taxable = (qty * rate * (1 - disc)).quantize(TWO_PLACES, ROUND_HALF_UP)

    tb: TaxBreakdown = calculate_tax(taxable, gst_rate, is_intra_state)

    line_total = taxable + tb.total_tax

    return LineResult(
        taxable_amount=int(taxable * PAISE),
        cgst_rate=float(tb.cgst_rate),
        cgst_amount=int(tb.cgst_amount * PAISE),
        sgst_rate=float(tb.sgst_rate),
        sgst_amount=int(tb.sgst_amount * PAISE),
        igst_rate=float(tb.igst_rate),
        igst_amount=int(tb.igst_amount * PAISE),
        line_total=int(line_total * PAISE),
    )


def compute_doc_totals(line_results: Sequence[LineResult]) -> DocTotals:
    """Sum all line items into document-level totals (integer paise)."""
    total_taxable = sum(lr.taxable_amount for lr in line_results)
    total_cgst = sum(lr.cgst_amount for lr in line_results)
    total_sgst = sum(lr.sgst_amount for lr in line_results)
    total_igst = sum(lr.igst_amount for lr in line_results)
    grand_total = total_taxable + total_cgst + total_sgst + total_igst

    return DocTotals(
        total_taxable=total_taxable,
        total_cgst=total_cgst,
        total_sgst=total_sgst,
        total_igst=total_igst,
        grand_total=grand_total,
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def format_currency(paise: int, symbol: str = "₹") -> str:
    """Convert integer paise to Indian-formatted display string.

    1234567 → '₹12,345.67'
    Uses Indian grouping: last 3, then groups of 2.
    """
    negative = paise < 0
    paise = abs(paise)
    rupees = paise // 100
    remaining = paise % 100

    # Indian number formatting
    s = str(rupees)
    if len(s) > 3:
        # Last 3 digits
        last3 = s[-3:]
        rest = s[:-3]
        # Group rest in 2s from right
        groups = []
        while rest:
            groups.append(rest[-2:])
            rest = rest[:-2]
        groups.reverse()
        formatted = ",".join(groups) + "," + last3
    else:
        formatted = s

    sign = "-" if negative else ""
    return f"{sign}{symbol}{formatted}.{remaining:02d}"


def rupees_to_paise(rupees: float | Decimal | str) -> int:
    """Convert a rupee amount to integer paise.  Safe for user input."""
    d = Decimal(str(rupees)).quantize(TWO_PLACES, ROUND_HALF_UP)
    return int(d * PAISE)


def paise_to_rupees(paise: int) -> Decimal:
    """Convert integer paise to Decimal rupees."""
    return (Decimal(str(paise)) / PAISE).quantize(TWO_PLACES)
