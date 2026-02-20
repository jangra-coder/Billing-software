"""Document and DocumentItem dataclasses."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Document:
    id: int | None = None

    # Identity
    document_number: str = ""
    document_type: str = ""       # 'IN', 'QT', 'PI', 'DC', 'PO'

    # Dates
    document_date: str = ""       # ISO: 2026-01-23
    supply_date: str = ""

    # Customer snapshot
    customer_id: int | None = None
    customer_name: str = ""
    customer_gstin: str = ""
    buyer_address1: str = ""
    buyer_address2: str = ""
    buyer_address3: str = ""
    buyer_state_code: str = ""
    buyer_state_name: str = ""
    buyer_pan: str = ""

    # Logistics
    vehicle_no: str = ""
    gr_lr_no: str = ""
    place_of_supply: str = ""
    po_no_date: str = ""
    vendor_code: str = ""
    dsr_number: str = ""

    # Totals — INTEGER paise
    total_taxable: int = 0
    total_cgst: int = 0
    total_sgst: int = 0
    total_igst: int = 0
    grand_total: int = 0
    amount_in_words: str = ""

    copy_type: str = "ORIGINAL FOR RECIPIENT"

    # Metadata
    remarks: str = ""
    status: str = "draft"         # draft | saved | exported | cancelled
    created_at: str = ""
    updated_at: str = ""

    # Transient — not persisted directly in documents table
    items: list[DocumentItem] = field(default_factory=list)


@dataclass
class DocumentItem:
    id: int | None = None
    document_id: int | None = None
    serial_no: int = 0

    # Product snapshot
    category_name: str = ""
    item_name: str = ""
    hsn_code: str = ""

    # Pricing — money in paise, rates/qty stay float/real
    quantity: float = 1.0
    rate: int = 0                 # Paise
    discount_pct: float = 0.0    # 0.05 = 5%
    taxable_amount: int = 0      # Paise

    # Tax
    cgst_rate: float = 0.0
    cgst_amount: int = 0         # Paise
    sgst_rate: float = 0.0
    sgst_amount: int = 0         # Paise
    igst_rate: float = 0.0
    igst_amount: int = 0         # Paise

    line_total: int = 0          # Paise
    created_at: str = ""
