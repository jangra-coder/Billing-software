"""Customer dataclass — buyer master."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Customer:
    id: int | None = None
    name: str = ""
    company_name: str = ""
    mobile: str = ""
    email: str = ""
    gstin: str = ""
    pan: str = ""
    address_line1: str = ""
    address_line2: str = ""
    address_line3: str = ""
    state_code: str = ""
    vendor_code: str = ""
    is_active: int = 1
    custom_fields: str = "{}"   # JSON dict of custom attributes
    created_at: str = ""
    updated_at: str = ""
