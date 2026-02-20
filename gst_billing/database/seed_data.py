"""
Seed data — populated on first-ever database creation.

Contains:
  • 39 Indian states/UTs with GST codes
  • 5 default document types
  • 8 default purchase categories
  • 1 blank company_profile row  (is_setup_complete = 0)
  • 1 default pdf_template_settings row
  • 5 blank terms_conditions rows (one per default doc type)
"""

from __future__ import annotations

import sqlite3


# ---------------------------------------------------------------------------
# State Master — 39 Indian states & UTs  (from Excel StateMaster sheet)
# ---------------------------------------------------------------------------
STATES: list[tuple[str, str]] = [
    ("01", "Jammu & Kashmir"),
    ("02", "Himachal Pradesh"),
    ("03", "Punjab"),
    ("04", "Chandigarh"),
    ("05", "Uttarakhand"),
    ("06", "Haryana"),
    ("07", "Delhi"),
    ("08", "Rajasthan"),
    ("09", "Uttar Pradesh"),
    ("10", "Bihar"),
    ("11", "Sikkim"),
    ("12", "Arunachal Pradesh"),
    ("13", "Nagaland"),
    ("14", "Manipur"),
    ("15", "Mizoram"),
    ("16", "Tripura"),
    ("17", "Meghalaya"),
    ("18", "Assam"),
    ("19", "West Bengal"),
    ("20", "Jharkhand"),
    ("21", "Odisha"),
    ("22", "Chhattisgarh"),
    ("23", "Madhya Pradesh"),
    ("24", "Gujarat"),
    ("25", "Daman & Diu"),
    ("26", "Dadra & Nagar Haveli"),
    ("27", "Maharashtra"),
    ("29", "Karnataka"),
    ("30", "Goa"),
    ("31", "Lakshadweep"),
    ("32", "Kerala"),
    ("33", "Tamil Nadu"),
    ("34", "Puducherry"),
    ("35", "Andaman & Nicobar Islands"),
    ("36", "Telangana"),
    ("37", "Andhra Pradesh"),
    ("38", "Ladakh"),
    ("97", "Other Territory"),
    ("99", "Centre Jurisdiction"),
]

# ---------------------------------------------------------------------------
# Default document types
# ---------------------------------------------------------------------------
DOC_TYPES: list[tuple[str, str, str, int, int, str, int, int]] = [
    # code, display_name, prefix, is_enabled, is_gst_doc, number_format, padding, sort
    ("IN", "Tax Invoice",       "IN", 1, 1, "{YYYY}{PREFIX}{NNNN}", 4, 1),
    ("QT", "Quotation",         "QT", 1, 0, "{YYYY}{PREFIX}{NNNN}", 4, 2),
    ("PI", "Proforma Invoice",  "PI", 1, 0, "{YYYY}{PREFIX}{NNNN}", 4, 3),
    ("DC", "Delivery Challan",  "DC", 1, 0, "{YYYY}{PREFIX}{NNNN}", 4, 4),
    ("PO", "Purchase Order",    "PO", 1, 0, "{YYYY}{PREFIX}{NNNN}", 4, 5),
]

# ---------------------------------------------------------------------------
# Default purchase categories
# ---------------------------------------------------------------------------
PURCHASE_CATEGORIES: list[tuple[str, int]] = [
    ("Raw Material",  1),
    ("Tooling",       2),
    ("Utility",       3),
    ("Rent",          4),
    ("Maintenance",   5),
    ("Transport",     6),
    ("Salary",        7),
    ("Miscellaneous", 8),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def seed_all(conn: sqlite3.Connection) -> None:
    """Insert all seed data.  Safely skips rows that already exist."""
    _seed_states(conn)
    _seed_doc_types(conn)
    _seed_purchase_categories(conn)
    _seed_company_profile(conn)
    _seed_pdf_template_settings(conn)
    _seed_terms_conditions(conn)
    conn.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _seed_states(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO state_master (code, state_name) VALUES (?, ?)",
        STATES,
    )


def _seed_doc_types(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO doc_type_config
           (code, display_name, prefix, is_enabled, is_gst_doc,
            number_format, padding_digits, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        DOC_TYPES,
    )


def _seed_purchase_categories(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO purchase_categories (name, sort_order) VALUES (?, ?)",
        PURCHASE_CATEGORIES,
    )


def _seed_company_profile(conn: sqlite3.Connection) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO company_profile (id, name) VALUES (1, '')"""
    )


def _seed_pdf_template_settings(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO pdf_template_settings (id) VALUES (1)"
    )


def _seed_terms_conditions(conn: sqlite3.Connection) -> None:
    for code, *_ in DOC_TYPES:
        conn.execute(
            "INSERT OR IGNORE INTO terms_conditions (document_type) VALUES (?)",
            (code,),
        )
