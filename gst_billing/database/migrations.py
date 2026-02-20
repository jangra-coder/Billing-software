"""
Database schema creation and versioned migrations.

Every CREATE TABLE from the blueprint lives here.  On first launch the full
schema is applied.  On subsequent launches the version is checked and any
incremental ALTER TABLE migrations are run automatically.
"""

from __future__ import annotations

import sqlite3
from typing import Sequence

# ---------------------------------------------------------------------------
# Current schema version — bump this whenever a migration is added
# ---------------------------------------------------------------------------
APP_SCHEMA_VERSION = 4

# ---------------------------------------------------------------------------
# Full CREATE TABLE script (version 1 — initial)
# ---------------------------------------------------------------------------
SCHEMA_V1: Sequence[str] = [
    # -- db_version (must be first)
    """
    CREATE TABLE IF NOT EXISTS db_version (
        version      INTEGER PRIMARY KEY,
        applied_at   TEXT DEFAULT (datetime('now')),
        description  TEXT
    );
    """,

    # -- company_profile
    """
    CREATE TABLE IF NOT EXISTS company_profile (
        id                  INTEGER PRIMARY KEY CHECK (id = 1),
        name                TEXT NOT NULL DEFAULT '',
        address_line1       TEXT DEFAULT '',
        address_line2       TEXT DEFAULT '',
        phone               TEXT DEFAULT '',
        email               TEXT DEFAULT '',
        website             TEXT DEFAULT '',
        gstin               TEXT DEFAULT '',
        pan                 TEXT DEFAULT '',
        cin                 TEXT DEFAULT '',
        state_name          TEXT DEFAULT '',
        state_code          TEXT DEFAULT '',
        bank_name           TEXT DEFAULT '',
        bank_branch         TEXT DEFAULT '',
        account_no          TEXT DEFAULT '',
        account_type        TEXT DEFAULT 'Current',
        ifsc_code           TEXT DEFAULT '',
        logo_path           TEXT DEFAULT '',
        stamp_path          TEXT DEFAULT '',
        signature_label     TEXT DEFAULT 'Authorised Signatory',
        currency_symbol     TEXT DEFAULT '₹',
        financial_year_start INTEGER DEFAULT 4,
        is_setup_complete   INTEGER DEFAULT 0,
        updated_at          TEXT DEFAULT (datetime('now'))
    );
    """,

    # -- state_master
    """
    CREATE TABLE IF NOT EXISTS state_master (
        code        TEXT PRIMARY KEY,
        state_name  TEXT NOT NULL
    );
    """,

    # -- customers
    """
    CREATE TABLE IF NOT EXISTS customers (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        company_name    TEXT DEFAULT '',
        mobile          TEXT DEFAULT '',
        email           TEXT DEFAULT '',
        gstin           TEXT DEFAULT '',
        pan             TEXT DEFAULT '',
        address_line1   TEXT DEFAULT '',
        address_line2   TEXT DEFAULT '',
        address_line3   TEXT DEFAULT '',
        state_code      TEXT DEFAULT '' REFERENCES state_master(code),
        vendor_code     TEXT DEFAULT '',
        is_active       INTEGER DEFAULT 1,
        custom_fields   TEXT DEFAULT '{}',
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);",
    "CREATE INDEX IF NOT EXISTS idx_customers_gstin ON customers(gstin);",
    "CREATE INDEX IF NOT EXISTS idx_customers_mobile ON customers(mobile);",

    # -- products
    """
    CREATE TABLE IF NOT EXISTS products (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name   TEXT NOT NULL UNIQUE,
        hsn_code        TEXT NOT NULL,
        default_rate    INTEGER DEFAULT 0,
        gst_rate        REAL DEFAULT 18.0,
        is_active       INTEGER DEFAULT 1,
        custom_fields   TEXT DEFAULT '{}',
        created_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_name);",
    "CREATE INDEX IF NOT EXISTS idx_products_hsn ON products(hsn_code);",

    # -- doc_type_config (must precede documents & terms_conditions)
    """
    CREATE TABLE IF NOT EXISTS doc_type_config (
        code            TEXT PRIMARY KEY,
        display_name    TEXT NOT NULL,
        prefix          TEXT NOT NULL,
        is_enabled      INTEGER DEFAULT 1,
        is_gst_doc      INTEGER DEFAULT 1,
        number_format   TEXT DEFAULT '{YYYY}{PREFIX}{NNNN}',
        padding_digits  INTEGER DEFAULT 4,
        sort_order      INTEGER DEFAULT 0
    );
    """,

    # -- documents
    """
    CREATE TABLE IF NOT EXISTS documents (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        document_number TEXT NOT NULL UNIQUE,
        document_type   TEXT NOT NULL,
        document_date   TEXT NOT NULL,
        supply_date     TEXT DEFAULT '',
        customer_id     INTEGER REFERENCES customers(id),
        customer_name   TEXT DEFAULT '',
        customer_gstin  TEXT DEFAULT '',
        buyer_address1  TEXT DEFAULT '',
        buyer_address2  TEXT DEFAULT '',
        buyer_address3  TEXT DEFAULT '',
        buyer_state_code TEXT DEFAULT '',
        buyer_state_name TEXT DEFAULT '',
        buyer_pan       TEXT DEFAULT '',
        vehicle_no      TEXT DEFAULT '',
        gr_lr_no        TEXT DEFAULT '',
        place_of_supply TEXT DEFAULT '',
        po_no_date      TEXT DEFAULT '',
        vendor_code     TEXT DEFAULT '',
        dsr_number      TEXT DEFAULT '',
        total_taxable   INTEGER DEFAULT 0,
        total_cgst      INTEGER DEFAULT 0,
        total_sgst      INTEGER DEFAULT 0,
        total_igst      INTEGER DEFAULT 0,
        grand_total     INTEGER DEFAULT 0,
        amount_in_words TEXT DEFAULT '',
        copy_type       TEXT DEFAULT 'ORIGINAL FOR RECIPIENT',
        remarks         TEXT DEFAULT '',
        status          TEXT DEFAULT 'draft'
                        CHECK (status IN ('draft','saved','exported','cancelled')),
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_documents_number ON documents(document_number);",
    "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);",
    "CREATE INDEX IF NOT EXISTS idx_documents_date ON documents(document_date);",
    "CREATE INDEX IF NOT EXISTS idx_documents_customer ON documents(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);",

    # -- document_items
    """
    CREATE TABLE IF NOT EXISTS document_items (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        serial_no       INTEGER NOT NULL,
        category_name   TEXT NOT NULL,
        item_name       TEXT DEFAULT '',
        hsn_code        TEXT NOT NULL,
        quantity        REAL NOT NULL DEFAULT 1,
        rate            INTEGER NOT NULL DEFAULT 0,
        discount_pct    REAL DEFAULT 0,
        taxable_amount  INTEGER NOT NULL DEFAULT 0,
        cgst_rate       REAL DEFAULT 0,
        cgst_amount     INTEGER DEFAULT 0,
        sgst_rate       REAL DEFAULT 0,
        sgst_amount     INTEGER DEFAULT 0,
        igst_rate       REAL DEFAULT 0,
        igst_amount     INTEGER DEFAULT 0,
        line_total      INTEGER NOT NULL DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_items_document ON document_items(document_id);",
    "CREATE INDEX IF NOT EXISTS idx_items_hsn ON document_items(hsn_code);",

    # -- terms_conditions
    """
    CREATE TABLE IF NOT EXISTS terms_conditions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        document_type   TEXT NOT NULL UNIQUE REFERENCES doc_type_config(code),
        tc_text         TEXT DEFAULT '',
        is_enabled      INTEGER DEFAULT 1
    );
    """,

    # -- purchase_categories (must precede purchases)
    """
    CREATE TABLE IF NOT EXISTS purchase_categories (
        name        TEXT PRIMARY KEY,
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1
    );
    """,

    # -- purchases
    """
    CREATE TABLE IF NOT EXISTS purchases (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_date   TEXT NOT NULL,
        invoice_no      TEXT DEFAULT '',
        description     TEXT DEFAULT '',
        amount          INTEGER DEFAULT 0,
        vendor_name     TEXT DEFAULT '',
        category        TEXT DEFAULT '' REFERENCES purchase_categories(name),
        notes           TEXT DEFAULT '',
        custom_fields   TEXT DEFAULT '{}',
        created_at      TEXT DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases(purchase_date);",
    "CREATE INDEX IF NOT EXISTS idx_purchases_vendor ON purchases(vendor_name);",
    "CREATE INDEX IF NOT EXISTS idx_purchases_category ON purchases(category);",

    # -- invoice_counter
    """
    CREATE TABLE IF NOT EXISTS invoice_counter (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        year        INTEGER NOT NULL,
        doc_type    TEXT NOT NULL,
        last_number INTEGER NOT NULL DEFAULT 0,
        UNIQUE(year, doc_type)
    );
    """,

    # -- app_settings
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        key     TEXT PRIMARY KEY,
        value   TEXT
    );
    """,

    # -- custom_field_definitions
    """
    CREATE TABLE IF NOT EXISTS custom_field_definitions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        field_name  TEXT NOT NULL,
        field_label TEXT NOT NULL,
        field_type  TEXT NOT NULL DEFAULT 'text',
        sort_order  INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1,
        is_builtin  INTEGER DEFAULT 0,
        is_required INTEGER DEFAULT 0,
        created_at  TEXT DEFAULT (datetime('now')),
        UNIQUE(entity_type, field_name)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_cfd_entity ON custom_field_definitions(entity_type);",

    # -- pdf_template_settings
    """
    CREATE TABLE IF NOT EXISTS pdf_template_settings (
        id                   INTEGER PRIMARY KEY CHECK (id = 1),
        show_logo            INTEGER DEFAULT 1,
        logo_position        TEXT DEFAULT 'left',
        logo_width_mm        REAL DEFAULT 25,
        show_stamp           INTEGER DEFAULT 1,
        show_cin             INTEGER DEFAULT 1,
        show_website         INTEGER DEFAULT 1,
        header_color_hex     TEXT DEFAULT '#000000',
        show_vehicle_no      INTEGER DEFAULT 1,
        show_gr_lr_no        INTEGER DEFAULT 1,
        show_po_field        INTEGER DEFAULT 1,
        show_vendor_code     INTEGER DEFAULT 1,
        show_dsr_number      INTEGER DEFAULT 1,
        show_supply_date     INTEGER DEFAULT 1,
        show_place_of_supply INTEGER DEFAULT 1,
        show_discount_col    INTEGER DEFAULT 1,
        show_hsn_col         INTEGER DEFAULT 1,
        show_bank_details    INTEGER DEFAULT 1,
        show_amount_in_words INTEGER DEFAULT 1,
        show_tc              INTEGER DEFAULT 1,
        footer_note          TEXT DEFAULT 'This is a Computer Generated Invoice',
        copy_types_json      TEXT DEFAULT '["Original for Recipient","Duplicate for Transporter","Triplicate for Supplier","Extra Copy"]',
        font_family          TEXT DEFAULT 'Helvetica',
        base_font_size       REAL DEFAULT 8,
        updated_at           TEXT DEFAULT (datetime('now'))
    );
    """,
]

# ---------------------------------------------------------------------------
# Incremental migrations — keyed by target version
# ---------------------------------------------------------------------------
# When you need to alter the schema after v1 ships:
#   1. Add an entry here      e.g.  2: (["ALTER TABLE ..."], "description")
#   2. Bump APP_SCHEMA_VERSION to match the new key
#
MIGRATIONS: dict[int, tuple[list[str], str]] = {
    2: (
        [
            # New table for custom field definitions
            """CREATE TABLE IF NOT EXISTS custom_field_definitions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                field_name  TEXT NOT NULL,
                field_label TEXT NOT NULL,
                field_type  TEXT NOT NULL DEFAULT 'text',
                sort_order  INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(entity_type, field_name)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_cfd_entity ON custom_field_definitions(entity_type)",
            # Add custom_fields JSON column to existing tables
            "ALTER TABLE products  ADD COLUMN custom_fields TEXT DEFAULT '{}'",
            "ALTER TABLE customers ADD COLUMN custom_fields TEXT DEFAULT '{}'",
            "ALTER TABLE purchases ADD COLUMN custom_fields TEXT DEFAULT '{}'",
        ],
        "Added custom field definitions table and custom_fields JSON column to products, customers, purchases",
    ),
    3: (
        [
            # Add is_builtin and is_required columns to custom_field_definitions
            "ALTER TABLE custom_field_definitions ADD COLUMN is_builtin  INTEGER DEFAULT 0",
            "ALTER TABLE custom_field_definitions ADD COLUMN is_required INTEGER DEFAULT 0",
        ],
        "Added is_builtin and is_required flags to custom_field_definitions",
    ),
    4: (
        [
            # Add address_line3 to customers and buyer_address3 to documents
            "ALTER TABLE customers ADD COLUMN address_line3 TEXT DEFAULT ''",
            "ALTER TABLE documents ADD COLUMN buyer_address3 TEXT DEFAULT ''",
        ],
        "Added address_line3 to customers and buyer_address3 to documents",
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def initialise_database(conn: sqlite3.Connection) -> None:
    """Create or migrate the database to the latest schema version."""
    # Check if db_version table exists (i.e. is this a fresh DB?)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='db_version'"
    )
    is_fresh = cur.fetchone() is None

    if is_fresh:
        _apply_full_schema(conn)
    else:
        _run_migrations(conn)


def _apply_full_schema(conn: sqlite3.Connection) -> None:
    """Fresh install — run every CREATE TABLE then stamp version 1."""
    cur = conn.cursor()
    for sql in SCHEMA_V1:
        cur.executescript(sql) if "\n" in sql.strip() else cur.execute(sql)
    cur.execute(
        "INSERT OR IGNORE INTO db_version (version, description) VALUES (?, ?)",
        (1, "Initial schema v1.0"),
    )
    conn.commit()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Upgrade an existing DB from its current version to APP_SCHEMA_VERSION."""
    row = conn.execute("SELECT MAX(version) FROM db_version").fetchone()
    current = row[0] if row and row[0] else 1

    if current >= APP_SCHEMA_VERSION:
        return  # Already up-to-date

    cur = conn.cursor()
    for ver in range(current + 1, APP_SCHEMA_VERSION + 1):
        if ver not in MIGRATIONS:
            raise RuntimeError(
                f"Missing migration for version {ver}. "
                f"DB is at v{current}, app expects v{APP_SCHEMA_VERSION}."
            )
        sqls, desc = MIGRATIONS[ver]
        for sql in sqls:
            cur.execute(sql)
        cur.execute(
            "INSERT INTO db_version (version, description) VALUES (?, ?)",
            (ver, desc),
        )
    conn.commit()
