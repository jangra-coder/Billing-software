"""
GST Engine — Tax calculation core.

Determines intra-state (CGST+SGST) vs inter-state (IGST) and computes
tax amounts using Decimal arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


@dataclass
class TaxBreakdown:
    """Result of a single tax calculation — all values in Decimal rupees."""
    is_intra_state: bool
    gst_rate: Decimal       # e.g. Decimal('18')
    cgst_rate: Decimal       # 9 or 0
    cgst_amount: Decimal     # rupees
    sgst_rate: Decimal       # 9 or 0
    sgst_amount: Decimal     # rupees
    igst_rate: Decimal       # 18 or 0
    igst_amount: Decimal     # rupees
    total_tax: Decimal       # rupees


def determine_supply_type(
    seller_state_code: str,
    buyer_state_code: str,
) -> bool:
    """Return True if intra-state (same state → CGST+SGST), False for inter-state (IGST).

    Edge cases:
      • If either code is empty/missing → treat as inter-state (safer for GST)
      • Codes compared as stripped strings
    """
    s = (seller_state_code or "").strip()
    b = (buyer_state_code or "").strip()
    if not s or not b:
        return False  # inter-state by default when info is missing
    return s == b


def calculate_tax(
    taxable_amount: Decimal,
    gst_rate: float | Decimal,
    is_intra_state: bool,
) -> TaxBreakdown:
    """Compute CGST/SGST or IGST for a given taxable amount.

    Args:
        taxable_amount: Decimal rupees (already rounded to 2 places).
        gst_rate: Total GST percentage (e.g. 18.0).
        is_intra_state: True → split into CGST+SGST; False → full IGST.

    Returns:
        TaxBreakdown with all amounts rounded to 2 decimal places.
    """
    rate = Decimal(str(gst_rate))

    if is_intra_state:
        half_rate = (rate / 2).quantize(TWO_PLACES, ROUND_HALF_UP)
        cgst = (taxable_amount * half_rate / 100).quantize(TWO_PLACES, ROUND_HALF_UP)
        sgst = (taxable_amount * half_rate / 100).quantize(TWO_PLACES, ROUND_HALF_UP)
        return TaxBreakdown(
            is_intra_state=True,
            gst_rate=rate,
            cgst_rate=half_rate,
            cgst_amount=cgst,
            sgst_rate=half_rate,
            sgst_amount=sgst,
            igst_rate=Decimal("0"),
            igst_amount=Decimal("0"),
            total_tax=cgst + sgst,
        )
    else:
        igst = (taxable_amount * rate / 100).quantize(TWO_PLACES, ROUND_HALF_UP)
        return TaxBreakdown(
            is_intra_state=False,
            gst_rate=rate,
            cgst_rate=Decimal("0"),
            cgst_amount=Decimal("0"),
            sgst_rate=Decimal("0"),
            sgst_amount=Decimal("0"),
            igst_rate=rate,
            igst_amount=igst,
            total_tax=igst,
        )


def extract_state_code_from_gstin(gstin: str) -> str:
    """Extract the 2-digit state code from a GSTIN (first two characters).

    Returns '' if GSTIN is too short or empty.
    """
    gstin = (gstin or "").strip()
    if len(gstin) >= 2 and gstin[:2].isdigit():
        return gstin[:2]
    return ""
