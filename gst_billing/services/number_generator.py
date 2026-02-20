"""
Document Number Generator — format-aware, reads doc_type_config.

Atomically increments invoice_counter inside an exclusive transaction.
"""

from __future__ import annotations

import sqlite3
from datetime import date


def generate_document_number(
    conn: sqlite3.Connection,
    doc_type_code: str,
    number_format: str = "{YYYY}{PREFIX}{NNNN}",
    prefix: str = "",
    padding_digits: int = 4,
    financial_year_start: int = 4,
    ref_date: date | None = None,
) -> str:
    """Generate the next document number atomically.

    Args:
        conn: Active SQLite connection.
        doc_type_code: 'IN', 'QT', etc.
        number_format: Template string with tokens.
        prefix: Usually same as doc_type_code unless user customised.
        padding_digits: How many digits for the sequence (e.g. 4 → 0001).
        financial_year_start: Month (1-12) that starts the financial year.
        ref_date: Date to derive year from (defaults to today).

    Returns:
        Formatted document number string, e.g. '2026IN0003'.
    """
    if ref_date is None:
        ref_date = date.today()
    if not prefix:
        prefix = doc_type_code

    year = ref_date.year

    # --- Get the next sequence number atomically ---
    cur = conn.cursor()
    try:
        cur.execute("BEGIN EXCLUSIVE")

        row = cur.execute(
            "SELECT last_number FROM invoice_counter "
            "WHERE year = ? AND doc_type = ?",
            (year, doc_type_code),
        ).fetchone()

        if row is None:
            next_num = 1
            cur.execute(
                "INSERT INTO invoice_counter (year, doc_type, last_number) "
                "VALUES (?, ?, ?)",
                (year, doc_type_code, next_num),
            )
        else:
            next_num = row[0] + 1
            cur.execute(
                "UPDATE invoice_counter SET last_number = ? "
                "WHERE year = ? AND doc_type = ?",
                (next_num, year, doc_type_code),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    # --- Format the number using the template ---
    seq_str = str(next_num).zfill(padding_digits)

    # Financial year string: e.g. "2025-26"
    if financial_year_start > 1 and ref_date.month < financial_year_start:
        fy_start = year - 1
    else:
        fy_start = year
    fy_str = f"{fy_start % 100:02d}"  # "25" from 2025

    result = number_format
    result = result.replace("{YYYY}", str(year))
    result = result.replace("{YY}", str(year % 100).zfill(2))
    result = result.replace("{FY}", f"FY{fy_str}")
    result = result.replace("{PREFIX}", prefix)
    result = result.replace("{NNNN}", seq_str)       # legacy 4-digit token
    for n in range(2, 8):
        token = "{N" + str(n) + "}"
        if token in result:
            result = result.replace(token, str(next_num).zfill(n))
    result = result.replace("{MM}", str(ref_date.month).zfill(2))

    return result


def peek_next_number(
    conn: sqlite3.Connection,
    doc_type_code: str,
    year: int | None = None,
    padding_digits: int = 4,
    number_format: str = "{YYYY}{PREFIX}{NNNN}",
    prefix: str = "",
) -> str:
    """Preview the next number WITHOUT consuming it (read-only)."""
    if year is None:
        year = date.today().year
    if not prefix:
        prefix = doc_type_code

    row = conn.execute(
        "SELECT last_number FROM invoice_counter "
        "WHERE year = ? AND doc_type = ?",
        (year, doc_type_code),
    ).fetchone()

    next_num = (row[0] + 1) if row else 1
    seq_str = str(next_num).zfill(padding_digits)

    result = number_format
    result = result.replace("{YYYY}", str(year))
    result = result.replace("{YY}", str(year % 100).zfill(2))
    result = result.replace("{PREFIX}", prefix)
    result = result.replace("{NNNN}", seq_str)
    for n in range(2, 8):
        token = "{N" + str(n) + "}"
        if token in result:
            result = result.replace(token, str(next_num).zfill(n))
    return result
