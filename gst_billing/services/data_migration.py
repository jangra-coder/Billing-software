"""
Data Migration Script — reads supreme_billa6.xlsm and populates the SQLite database.

This is an MKRD-specific legacy migration tool.
It reads:
  - Sheet1 (MKRD company header + products)
  - CustData (52 customers)
  - Existing invoices / quotations on individual sheets

Run once after first-run wizard to bring in legacy data.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

try:
    import openpyxl
except ImportError:
    openpyxl = None  # type: ignore[assignment]


PAISE = Decimal("100")
TWO_PLACES = Decimal("0.01")


def _to_paise(val: float | str | None) -> int:
    """Convert a rupee value to integer paise, safely."""
    if val is None:
        return 0
    try:
        d = Decimal(str(val)).quantize(TWO_PLACES, ROUND_HALF_UP)
        return int(d * PAISE)
    except Exception:
        return 0


def _safe_str(val) -> str:
    """Convert cell value to a stripped string or empty."""
    if val is None:
        return ""
    return str(val).strip()


def _safe_date(val) -> str:
    """Convert a cell value to YYYY-MM-DD string or empty."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    return ""


def migrate_from_xlsm(xlsm_path: str, conn: sqlite3.Connection) -> dict:
    """Read the xlsm workbook and populate the database.

    Args:
        xlsm_path: Path to supreme_billa6.xlsm.
        conn: Active SQLite connection (should already have tables created).

    Returns:
        A dict with counts: {'products': n, 'customers': n, 'documents': n, 'errors': [...]}
    """
    if openpyxl is None:
        return {"products": 0, "customers": 0, "documents": 0,
                "errors": ["openpyxl not installed"]}

    if not os.path.exists(xlsm_path):
        return {"products": 0, "customers": 0, "documents": 0,
                "errors": [f"File not found: {xlsm_path}"]}

    wb = openpyxl.load_workbook(xlsm_path, data_only=True, read_only=True)
    result = {"products": 0, "customers": 0, "documents": 0, "errors": []}

    try:
        _migrate_company_profile(wb, conn)
        result["products"] = _migrate_products(wb, conn)
        result["customers"] = _migrate_customers(wb, conn)
        conn.commit()
    except Exception as e:
        conn.rollback()
        result["errors"].append(str(e))
    finally:
        wb.close()

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _migrate_company_profile(wb, conn: sqlite3.Connection) -> None:
    """Read company info from Sheet1 header area and update company_profile."""
    try:
        ws = wb["Sheet1"]
    except KeyError:
        return

    # The xlsm has company info in fixed cells — typical layout:
    # B2: Company Name, B3: Address Line 1, B4: City State Pin
    # B5: GSTIN, B6: PAN, B7: Phone, B8: Email, B9: Bank details
    rows = list(ws.iter_rows(min_row=1, max_row=15, min_col=1, max_col=10, values_only=True))

    if len(rows) < 5:
        return

    # Extract what we can — positions may vary, so be defensive
    company_name = _safe_str(rows[1][1]) if len(rows) > 1 and len(rows[1]) > 1 else ""
    address_1 = _safe_str(rows[2][1]) if len(rows) > 2 and len(rows[2]) > 1 else ""
    gstin = _safe_str(rows[4][1]) if len(rows) > 4 and len(rows[4]) > 1 else ""

    if company_name:
        conn.execute(
            "UPDATE company_profile SET company_name = ?, address_line1 = ?, "
            "gstin = ?, is_setup_complete = 1 WHERE id = 1",
            (company_name, address_1, gstin),
        )


def _migrate_products(wb, conn: sqlite3.Connection) -> int:
    """Read product categories from Sheet1 drop-down area."""
    try:
        ws = wb["Sheet1"]
    except KeyError:
        return 0

    # Products are typically in columns around the dropdown list area
    # The xlsm stores category_name + HSN in a vertical list
    count = 0
    seen_names: set[str] = set()

    for row in ws.iter_rows(min_row=2, max_row=50, min_col=11, max_col=14, values_only=True):
        name = _safe_str(row[0]) if row[0] else ""
        hsn = _safe_str(row[1]) if len(row) > 1 and row[1] else ""

        if not name or name in seen_names:
            continue
        seen_names.add(name)

        try:
            conn.execute(
                "INSERT INTO products (category_name, hsn_code, unit, gst_rate, "
                "default_rate, is_active, created_at) "
                "VALUES (?, ?, 'NOS', 18.0, 0, 1, ?)",
                (name, hsn, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass  # duplicate

    return count


def _migrate_customers(wb, conn: sqlite3.Connection) -> int:
    """Read customer data from CustData sheet."""
    try:
        ws = wb["CustData"]
    except KeyError:
        return 0

    count = 0
    # CustData: Row 1 = header; columns = Name, GSTIN, Address, City, State, Pin, Mobile, Email
    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not header_row:
        return 0

    for row in ws.iter_rows(min_row=2, max_row=200, values_only=True):
        if not row or not row[0]:
            continue

        name = _safe_str(row[0])
        if not name:
            continue

        gstin = _safe_str(row[1]) if len(row) > 1 else ""
        address1 = _safe_str(row[2]) if len(row) > 2 else ""
        city = _safe_str(row[3]) if len(row) > 3 else ""
        state_name = _safe_str(row[4]) if len(row) > 4 else ""
        pin = _safe_str(row[5]) if len(row) > 5 else ""
        mobile = _safe_str(row[6]) if len(row) > 6 else ""
        email = _safe_str(row[7]) if len(row) > 7 else ""

        # Look up state code from name
        state_code = ""
        if state_name:
            row_state = conn.execute(
                "SELECT code FROM state_master WHERE state_name LIKE ?",
                (f"%{state_name}%",),
            ).fetchone()
            if row_state:
                state_code = row_state[0]

        try:
            conn.execute(
                "INSERT INTO customers (company_name, contact_person, gstin, "
                "address_line1, city, state_code, pincode, mobile, email, "
                "is_active, created_at) "
                "VALUES (?, '', ?, ?, ?, ?, ?, ?, ?, 1, ?)",
                (name, gstin, address1, city, state_code, pin, mobile, email,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass

    return count
