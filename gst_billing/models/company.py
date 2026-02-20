"""CompanyProfile dataclass — singleton seller identity."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class CompanyProfile:
    id: int = 1
    name: str = ""
    address_line1: str = ""
    address_line2: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    gstin: str = ""
    pan: str = ""
    cin: str = ""
    state_name: str = ""
    state_code: str = ""
    bank_name: str = ""
    bank_branch: str = ""
    account_no: str = ""
    account_type: str = "Current"
    ifsc_code: str = ""
    logo_path: str = ""
    stamp_path: str = ""
    signature_label: str = "Authorised Signatory"
    currency_symbol: str = "₹"
    financial_year_start: int = 4
    is_setup_complete: int = 0
    updated_at: str = ""
