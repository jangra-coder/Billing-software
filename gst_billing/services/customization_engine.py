"""
Customization Engine — field visibility resolver and template settings loader.

Reads pdf_template_settings and company_profile from DB to answer questions
like "should the Vehicle No field be shown in the editor / PDF?"
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field


@dataclass
class VisibilityConfig:
    """Which optional fields/sections are visible in the UI and PDF."""
    # Document fields
    show_vehicle_no: bool = True
    show_gr_lr_no: bool = True
    show_po_field: bool = True
    show_vendor_code: bool = True
    show_dsr_number: bool = True
    show_supply_date: bool = True
    show_place_of_supply: bool = True

    # Item table columns
    show_discount_col: bool = True
    show_hsn_col: bool = True

    # Header zone
    show_logo: bool = True
    logo_position: str = "left"
    logo_width_mm: float = 25.0
    show_stamp: bool = True
    show_cin: bool = True
    show_website: bool = True
    header_color_hex: str = "#000000"

    # Footer zone
    show_bank_details: bool = True
    show_amount_in_words: bool = True
    show_tc: bool = True
    footer_note: str = "This is a Computer Generated Invoice"

    # Copy types
    copy_types: list[str] = field(default_factory=lambda: [
        "Original for Recipient",
        "Duplicate for Transporter",
        "Triplicate for Supplier",
        "Extra Copy",
    ])

    # Font
    font_family: str = "Helvetica"
    base_font_size: float = 8.0


def load_visibility_config(conn: sqlite3.Connection) -> VisibilityConfig:
    """Load the current customization settings from the database."""
    row = conn.execute(
        "SELECT * FROM pdf_template_settings WHERE id = 1"
    ).fetchone()

    if row is None:
        return VisibilityConfig()

    d = dict(row)

    # Parse copy_types JSON
    try:
        copy_types = json.loads(d.get("copy_types_json", "[]"))
    except (json.JSONDecodeError, TypeError):
        copy_types = ["Original for Recipient"]

    return VisibilityConfig(
        show_vehicle_no=bool(d.get("show_vehicle_no", 1)),
        show_gr_lr_no=bool(d.get("show_gr_lr_no", 1)),
        show_po_field=bool(d.get("show_po_field", 1)),
        show_vendor_code=bool(d.get("show_vendor_code", 1)),
        show_dsr_number=bool(d.get("show_dsr_number", 1)),
        show_supply_date=bool(d.get("show_supply_date", 1)),
        show_place_of_supply=bool(d.get("show_place_of_supply", 1)),
        show_discount_col=bool(d.get("show_discount_col", 1)),
        show_hsn_col=bool(d.get("show_hsn_col", 1)),
        show_logo=bool(d.get("show_logo", 1)),
        logo_position=d.get("logo_position", "left"),
        logo_width_mm=d.get("logo_width_mm", 25.0),
        show_stamp=bool(d.get("show_stamp", 1)),
        show_cin=bool(d.get("show_cin", 1)),
        show_website=bool(d.get("show_website", 1)),
        header_color_hex=d.get("header_color_hex", "#000000"),
        show_bank_details=bool(d.get("show_bank_details", 1)),
        show_amount_in_words=bool(d.get("show_amount_in_words", 1)),
        show_tc=bool(d.get("show_tc", 1)),
        footer_note=d.get("footer_note", "This is a Computer Generated Invoice"),
        copy_types=copy_types,
        font_family=d.get("font_family", "Helvetica"),
        base_font_size=d.get("base_font_size", 8.0),
    )


def is_field_visible(config: VisibilityConfig, field_name: str) -> bool:
    """Quick check: given a document field name, should it be shown?

    Args:
        config: Current VisibilityConfig.
        field_name: DB column name from the documents table, e.g. 'vehicle_no'.

    Returns:
        True if the field should be displayed in UI and PDF.
    """
    mapping = {
        "vehicle_no": config.show_vehicle_no,
        "gr_lr_no": config.show_gr_lr_no,
        "po_no_date": config.show_po_field,
        "vendor_code": config.show_vendor_code,
        "dsr_number": config.show_dsr_number,
        "supply_date": config.show_supply_date,
        "place_of_supply": config.show_place_of_supply,
    }
    return mapping.get(field_name, True)
