"""
Excel Import / Export service.

Export: any list of dicts or dataclass objects → .xlsx with auto-width columns.
Import: .xlsx → list of dicts (caller maps to models).

Column mapping: case-insensitive, order-independent matching with alias support.
Platform-safe: uses pathlib, no OS-specific calls.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict, dataclass, fields as dc_fields
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from services.calculator import format_currency


# ======================================================================
# COLUMN ALIAS MAPS  — canonical_field → list of accepted aliases
# ======================================================================

PRODUCT_ALIASES: dict[str, list[str]] = {
    "category_name": ["category_name", "category", "cat", "product", "product_name",
                       "service", "service_name", "name", "item", "item_name"],
    "hsn_code":      ["hsn_code", "hsn", "hsn_sac", "sac", "sac_code", "hsncode",
                       "hsn_sac_code", "hsnno", "hsn_no"],
    "gst_rate":      ["gst_rate", "gst", "gst_percent", "gst_pct", "tax_rate",
                       "tax", "rate_gst", "gst_%"],
    "default_rate":  ["default_rate", "rate", "price", "unit_price", "mrp",
                       "amount", "cost", "unit_rate", "selling_price"],
}

CUSTOMER_ALIASES: dict[str, list[str]] = {
    "name":          ["name", "customer_name", "buyer_name", "buyer", "client",
                       "client_name", "party_name", "party"],
    "company_name":  ["company_name", "company", "firm", "firm_name", "comapany",
                       "organisation", "organization"],
    "mobile":        ["mobile", "phone", "contact", "phone_no", "mobile_no",
                       "contact_no", "tel", "telephone", "mob"],
    "email":         ["email", "email_id", "mail", "e_mail", "emailid"],
    "gstin":         ["gstin", "gst_no", "gstno", "gstin_client", "gst_number",
                       "gst_in", "gst"],
    "pan":           ["pan", "pan_no", "panno", "pan_number", "pan_card"],
    "address_line1": ["address_line1", "address_1", "address1", "address",
                       "addr1", "addr_1", "street"],
    "address_line2": ["address_line2", "address_2", "address2", "addr2",
                       "addr_2", "city"],
    "address_line3": ["address_line3", "address_3", "address3", "addr3",
                       "addr_3", "locality", "area"],
    "state_code":    ["state_code", "state", "state_cd", "statecode"],
    "vendor_code":   ["vendor_code", "vender_code", "vendorcode", "vender_code",
                       "vendor_id", "vcode"],
}

PURCHASE_ALIASES: dict[str, list[str]] = {
    "purchase_date": ["purchase_date", "date", "bill_date", "invoice_date", "dt"],
    "invoice_no":    ["invoice_no", "bill_no", "invoice_number", "bill_number",
                       "inv_no", "billno", "invoiceno"],
    "description":   ["description", "particular", "desc", "details", "item",
                       "narration", "remarks"],
    "amount":        ["amount", "price", "total", "value", "cost", "amt"],
    "vendor_name":   ["vendor_name", "vendor", "supplier", "party", "from",
                       "seller", "party_name"],
    "category":      ["category", "cat", "type", "head", "expense_head",
                       "purchase_type"],
    "notes":         ["notes", "note", "remark", "comments", "memo"],
}


# ======================================================================
# EXPORT
# ======================================================================

_HEADER_FILL = PatternFill("solid", fgColor="1565C0")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
_THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def export_to_excel(
    rows: Sequence[dict[str, Any]],
    filepath: str | Path,
    *,
    sheet_name: str = "Data",
    title: str = "",
    money_columns: Sequence[str] = (),
) -> Path:
    """Write a list of dicts to an .xlsx file with formatting.

    Args:
        rows: Data rows — each row is a dict.
        filepath: Destination path (will overwrite).
        sheet_name: Worksheet tab name.
        title: Optional title row above the header.
        money_columns: Column keys whose values are paise → display as ₹.

    Returns:
        Path to the written file.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    if not rows:
        ws.append(["No data to export"])
        wb.save(str(filepath))
        return filepath

    headers = list(rows[0].keys())
    start_row = 1

    # Optional title row
    if title:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        cell = ws.cell(row=1, column=1, value=title)
        cell.font = Font(bold=True, size=13)
        cell.alignment = Alignment(horizontal="center")
        start_row = 2

    # Header row
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=_pretty_header(header))
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN
        cell.border = _THIN_BORDER

    # Data rows
    money_set = set(money_columns)
    for row_offset, row_data in enumerate(rows, 1):
        for col_idx, key in enumerate(headers, 1):
            value = row_data.get(key, "")
            # Money conversion (paise → formatted)
            if key in money_set and isinstance(value, (int, float)):
                value = format_currency(int(value))
            cell = ws.cell(row=start_row + row_offset, column=col_idx, value=value)
            cell.border = _THIN_BORDER
            cell.alignment = Alignment(vertical="center")

    # Auto-width
    for col_idx in range(1, len(headers) + 1):
        max_len = 0
        letter = get_column_letter(col_idx)
        for row_cells in ws.iter_rows(min_col=col_idx, max_col=col_idx,
                                       min_row=start_row, max_row=start_row + len(rows)):
            for cell in row_cells:
                val = str(cell.value or "")
                max_len = max(max_len, len(val))
        ws.column_dimensions[letter].width = min(max(max_len + 3, 10), 50)

    # Freeze header row
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)

    wb.save(str(filepath))
    return filepath


def _pretty_header(key: str) -> str:
    """Convert snake_case key to Title Case header."""
    return key.replace("_", " ").title()


# ======================================================================
# IMPORT
# ======================================================================

def import_from_excel(
    filepath: str | Path,
    *,
    sheet_name: str | None = None,
    header_row: int = 1,
    max_rows: int = 10_000,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Read an Excel file and return (headers, rows).

    Args:
        filepath: Source .xlsx / .xlsm path.
        sheet_name: Tab to read (None = first sheet).
        header_row: Which row contains column headers (1-based).
        max_rows: Safety cap.

    Returns:
        (headers, rows) — headers is list of strings,
        rows is list of dicts keyed by header names.
    """
    filepath = Path(filepath)
    wb = load_workbook(str(filepath), read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    # Read headers
    raw_headers = []
    for cell in ws[header_row]:
        val = str(cell.value).strip() if cell.value is not None else ""
        raw_headers.append(val)

    # Normalise headers to snake_case
    headers = [_to_snake(h) for h in raw_headers]

    # Read data rows
    rows: list[dict[str, Any]] = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True)):
        if row_idx >= max_rows:
            break
        # Skip entirely blank rows
        if all(v is None or str(v).strip() == "" for v in row):
            continue
        record: dict[str, Any] = {}
        for col_idx, value in enumerate(row):
            if col_idx < len(headers) and headers[col_idx]:
                record[headers[col_idx]] = _clean_value(value)
        rows.append(record)

    wb.close()
    return raw_headers, rows


def _to_snake(text: str) -> str:
    """Convert a header like 'Customer Name' → 'customer_name'."""
    text = text.strip()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text.lower()


# ======================================================================
# COLUMN MAPPING ENGINE
# ======================================================================

@dataclass
class ColumnMapResult:
    """Result of mapping Excel columns to canonical field names."""
    mapped: dict[str, str]        # canonical_field → original_header
    unmapped: list[str]           # original headers that didn't match
    missing_required: list[str]   # required fields not found in Excel


def build_column_map(
    raw_headers: list[str],
    alias_map: dict[str, list[str]],
    required_fields: Sequence[str] = (),
) -> ColumnMapResult:
    """Map Excel column headers to canonical field names.

    Matching is case-insensitive, order-independent, and supports
    aliases.  The first alias that matches wins.

    Args:
        raw_headers: Column names from the Excel file.
        alias_map:   canonical_field → [accepted_aliases…]
        required_fields: Fields that MUST be present.

    Returns:
        ColumnMapResult with mapped, unmapped, and missing info.
    """
    # Normalise all Excel headers to lowercase-snake for matching
    norm_headers = [_to_snake(h) for h in raw_headers]

    # Build reverse lookup: normalised_alias → canonical_field
    reverse: dict[str, str] = {}
    for canonical, aliases in alias_map.items():
        for alias in aliases:
            key = _to_snake(alias)
            if key not in reverse:
                reverse[key] = canonical

    mapped: dict[str, str] = {}      # canonical → original header
    unmapped: list[str] = []

    for idx, norm in enumerate(norm_headers):
        original = raw_headers[idx]
        if not norm:
            continue
        canon = reverse.get(norm)
        if canon and canon not in mapped:
            mapped[canon] = original
        else:
            unmapped.append(original)

    missing = [f for f in required_fields if f not in mapped]
    return ColumnMapResult(mapped=mapped, unmapped=unmapped, missing_required=missing)


def remap_row(
    row_dict: dict[str, Any],
    column_map: ColumnMapResult,
) -> dict[str, Any]:
    """Re-key a row dict from snake(original_header) → canonical field names.

    Args:
        row_dict: Dict keyed by _to_snake(original_header).
        column_map: Result from build_column_map.

    Returns:
        Dict keyed by canonical field names.
    """
    out: dict[str, Any] = {}
    for canonical, original in column_map.mapped.items():
        snake_key = _to_snake(original)
        if snake_key in row_dict:
            out[canonical] = row_dict[snake_key]
    return out


def _clean_value(value: Any) -> Any:
    """Normalise cell values."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value == int(value):
        return int(value)
    return value


def get_sheet_names(filepath: str | Path) -> list[str]:
    """Return the list of sheet names in an Excel file."""
    filepath = Path(filepath)
    wb = load_workbook(str(filepath), read_only=True, data_only=True)
    names = wb.sheetnames
    wb.close()
    return names


# ======================================================================
# CONVENIENCE: dataclass list → dicts
# ======================================================================

def dataclass_list_to_dicts(
    objects: Sequence[Any],
    exclude_fields: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Convert a list of dataclass objects to list of dicts for export."""
    exclude = set(exclude_fields)
    result = []
    for obj in objects:
        d = asdict(obj)
        for key in exclude:
            d.pop(key, None)
        result.append(d)
    return result
