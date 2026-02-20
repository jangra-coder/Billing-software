"""
Validator — input validation for all user-facing fields.

Every function returns (is_valid: bool, error_message: str).
Empty error_message means valid.
"""

from __future__ import annotations

import re
from datetime import datetime, date

# ---------------------------------------------------------------------------
# Pre-compiled regexes
# ---------------------------------------------------------------------------
_GSTIN_RE = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
_MOBILE_RE = re.compile(r"^[6-9][0-9]{9}$")
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
_HSN_RE = re.compile(r"^[0-9]{4}([0-9]{2}([0-9]{2})?)?$")  # 4, 6, or 8 digits
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


# ---------------------------------------------------------------------------
# Public validators — each returns (bool, str)
# ---------------------------------------------------------------------------
def validate_gstin(gstin: str) -> tuple[bool, str]:
    gstin = (gstin or "").strip().upper()
    if not gstin:
        return (True, "")  # Optional field
    if len(gstin) != 15:
        return (False, "GSTIN must be exactly 15 characters")
    if not _GSTIN_RE.match(gstin):
        return (False, "Invalid GSTIN format")
    return (True, "")


def validate_pan(pan: str) -> tuple[bool, str]:
    pan = (pan or "").strip().upper()
    if not pan:
        return (True, "")
    if len(pan) != 10:
        return (False, "PAN must be exactly 10 characters")
    if not _PAN_RE.match(pan):
        return (False, "Invalid PAN format")
    return (True, "")


def validate_mobile(mobile: str) -> tuple[bool, str]:
    mobile = (mobile or "").strip()
    if not mobile:
        return (True, "")
    if not _MOBILE_RE.match(mobile):
        return (False, "Mobile must be 10 digits starting with 6-9")
    return (True, "")


def validate_email(email: str) -> tuple[bool, str]:
    email = (email or "").strip()
    if not email:
        return (True, "")
    if not _EMAIL_RE.match(email):
        return (False, "Invalid email format")
    return (True, "")


def validate_hsn(hsn: str) -> tuple[bool, str]:
    hsn = (hsn or "").strip()
    if not hsn:
        return (False, "HSN/SAC code is required")
    if not _HSN_RE.match(hsn):
        return (False, "HSN must be 4, 6, or 8 digits")
    return (True, "")


def validate_date(
    date_str: str,
    allow_future: bool = False,
    required: bool = True,
) -> tuple[bool, str]:
    """Validate ISO format date string (YYYY-MM-DD)."""
    date_str = (date_str or "").strip()
    if not date_str:
        return (not required, "Date is required" if required else "")
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return (False, "Date must be in YYYY-MM-DD format")
    if not allow_future and d > date.today():
        return (False, "Date cannot be in the future")
    return (True, "")


def validate_amount(
    amount: float | int | str,
    field_name: str = "Amount",
    allow_zero: bool = True,
) -> tuple[bool, str]:
    """Validate a monetary amount (in rupees, before paise conversion)."""
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return (False, f"{field_name} must be a number")
    if val < 0:
        return (False, f"{field_name} cannot be negative")
    if not allow_zero and val == 0:
        return (False, f"{field_name} cannot be zero")
    # Max 2 decimal places
    if round(val, 2) != val:
        return (False, f"{field_name} can have at most 2 decimal places")
    return (True, "")


def validate_quantity(qty: float | str) -> tuple[bool, str]:
    try:
        val = float(qty)
    except (ValueError, TypeError):
        return (False, "Quantity must be a number")
    if val <= 0:
        return (False, "Quantity must be positive")
    return (True, "")


def validate_rate(rate: float | str) -> tuple[bool, str]:
    try:
        val = float(rate)
    except (ValueError, TypeError):
        return (False, "Rate must be a number")
    if val < 0:
        return (False, "Rate cannot be negative")
    return (True, "")


def validate_discount(discount: float | str) -> tuple[bool, str]:
    try:
        val = float(discount)
    except (ValueError, TypeError):
        return (False, "Discount must be a number")
    if val < 0 or val > 1:
        return (False, "Discount must be between 0 and 1 (0%–100%)")
    return (True, "")


def validate_ifsc(ifsc: str) -> tuple[bool, str]:
    ifsc = (ifsc or "").strip().upper()
    if not ifsc:
        return (True, "")
    if not _IFSC_RE.match(ifsc):
        return (False, "Invalid IFSC code format (e.g. UTIB0001081)")
    return (True, "")


def validate_state_code(code: str, valid_codes: set[str] | None = None) -> tuple[bool, str]:
    code = (code or "").strip()
    if not code:
        return (True, "")
    if valid_codes and code not in valid_codes:
        return (False, f"Unknown state code: {code}")
    if not code.isdigit() or len(code) != 2:
        return (False, "State code must be 2 digits")
    return (True, "")


def validate_required(value: str, field_name: str = "Field") -> tuple[bool, str]:
    if not (value or "").strip():
        return (False, f"{field_name} is required")
    return (True, "")


def extract_pan_from_gstin(gstin: str) -> str:
    """Extract the 10-character PAN embedded in a GSTIN (chars 3-12)."""
    gstin = (gstin or "").strip().upper()
    if len(gstin) >= 12:
        return gstin[2:12]
    return ""
