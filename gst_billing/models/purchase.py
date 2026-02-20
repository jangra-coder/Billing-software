"""Purchase dataclass — expense register entry."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Purchase:
    id: int | None = None
    purchase_date: str = ""
    invoice_no: str = ""
    description: str = ""
    amount: int = 0              # Paise
    vendor_name: str = ""
    category: str = ""
    notes: str = ""
    custom_fields: str = "{}"   # JSON dict of custom attributes
    created_at: str = ""
