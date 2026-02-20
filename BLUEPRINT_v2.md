# GST Billing Suite — Complete Architecture Blueprint v3.0

> **Target:** Standalone, distributable desktop billing software for **any** GST-registered Indian business  
> **Replaces:** `supreme_billa6.xlsm` + `gstr1_generator_COMPLETE.py` (original MKRD workflow)  
> **Stack:** Python 3.13 · PyQt6 (GUI) · SQLite (DB) · ReportLab (PDF)  
> **Design Principle:** Zero hardcoded company data — every field is user-configurable via GUI  
> **Date:** 2026-02-16 (v3.0 — Generalized for multi-business distribution)  

---

## TABLE OF CONTENTS

1. [System Architecture](#1-system-architecture)
2. [Database Schema](#2-database-schema)
3. [Backend Modules](#3-backend-modules)
4. [UI / GUI Design](#4-ui--gui-design)
5. [PDF Engine](#5-pdf-engine)
6. [GSTR-1 Engine](#6-gstr-1-engine)
7. [Vulnerability & Flaw Analysis](#7-vulnerability--flaw-analysis)
8. [Optimized Workflow](#8-optimized-workflow)
9. [Customization & Distribution Engine](#9-customization--distribution-engine)
10. [Phase Plan](#10-phase-plan)

---

## 1. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                     GST BILLING SUITE                         │
│          (Company-agnostic — configurable per business)        │
├──────────────┬────────────┬───────────────┬───────────────────────┤
│   UI LAYER   │  BUSINESS  │  DATA LAYER   │    OUTPUT LAYER       │
│  (PyQt6)     │   LOGIC    │   (SQLite)    │  (ReportLab/openpyxl) │
├──────────────┼────────────┼───────────────┼───────────────────────┤
│ FirstRunWiz  │ GSTEngine  │ CompanyRepo   │ PDFController         │
│ Dashboard    │ NumGen     │ CustomerRepo  │ ├─ InvoicePDF         │
│ DocEditor    │ NumToWords │ ProductRepo   │ ├─ QuotationPDF       │
│ CustMgr      │ Validator  │ InvoiceRepo   │ ├─ ProformaPDF        │
│ ProdMgr      │ Calculator │ PurchaseRepo  │ ├─ ChallanPDF         │
│ PurchaseV    │ GSTR1Gen   │ StateMasterR  │ └─ PurchaseOrderPDF   │
│ Reports      │ ExcelExport│ TCRepo        │ GSTR1ExcelExport      │
│ Settings     │ BackupMgr  │ SettingsRepo  │ BackupExport          │
│ GSTR1View    │ CustomEng  │ TemplateRepo  │ ReportExport          │
└──────────────┴────────────┴───────────────┴───────────────────────┘
```

### Directory Structure
```
gst_billing/
├── main.py                      # Entry point + DB migration check + first-run detection
├── config.py                    # App-wide constants, paths, APP_SCHEMA_VERSION
├── database/
│   ├── __init__.py
│   ├── connection.py            # SQLite connection manager (singleton)
│   ├── migrations.py            # Versioned schema creation & incremental ALTER TABLE upgrades
│   └── seed_data.py             # Initial state master, doc types, purchase categories
├── models/
│   ├── __init__.py
│   ├── company.py               # CompanyProfile dataclass
│   ├── customer.py              # Customer dataclass
│   ├── product.py               # Product (Category + HSN) dataclass
│   ├── document.py              # Document (Invoice/Quotation/PI/DC/PO) dataclass
│   ├── document_item.py         # DocumentItem dataclass
│   ├── purchase.py              # Purchase entry dataclass
│   └── state.py                 # State dataclass
├── repositories/
│   ├── __init__.py
│   ├── base_repo.py             # Abstract CRUD base
│   ├── company_repo.py
│   ├── customer_repo.py
│   ├── product_repo.py
│   ├── document_repo.py         # Handles all 5 doc types
│   ├── purchase_repo.py
│   ├── state_repo.py
│   └── settings_repo.py         # T&C, preferences
├── services/
│   ├── __init__.py
│   ├── gst_engine.py            # Tax calculation (CGST/SGST/IGST logic)
│   ├── number_generator.py      # Auto-increment: 2026IN0001, 2026QT0001, etc.
│   ├── num_to_words.py          # Indian numbering (Crore/Lakh/Thousand)
│   ├── calculator.py            # Line-item & totals computation
│   ├── validator.py             # Input validation, GSTIN format, etc.
│   ├── gstr1_generator.py       # Full GSTR-1 multi-sheet Excel export
│   ├── pdf_controller.py        # PDF generation orchestrator
│   ├── excel_exporter.py        # Generic Excel export utility
│   └── backup_manager.py        # DB backup/restore
├── ui/
│   ├── __init__.py
│   ├── main_window.py           # QMainWindow with sidebar nav
│   ├── styles.py                # QSS stylesheet (theme)
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── sidebar.py           # Navigation sidebar
│   │   ├── search_bar.py        # Reusable search with autocomplete
│   │   ├── date_picker.py       # Indian DD/MM/YYYY date picker
│   │   ├── item_grid.py         # Dynamic item table (add/remove rows)
│   │   ├── currency_input.py    # ₹ formatted numeric input
│   │   ├── gstin_input.py       # GSTIN formatted input with validation
│   │   └── status_badge.py      # Color-coded status labels
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── dashboard.py         # Home dashboard with stats & charts
│   │   ├── document_editor.py   # Create/Edit invoice (all 5 types)
│   │   ├── document_list.py     # List/Search/Filter saved documents
│   │   ├── customer_manager.py  # Customer CRUD + search
│   │   ├── product_manager.py   # Product/Category CRUD
│   │   ├── purchase_tracker.py  # Purchase register
│   │   ├── gstr1_page.py        # GSTR-1 generation UI
│   │   ├── reports_page.py      # Revenue, tax, customer reports
│   │   └── settings_page.py     # Company profile, T&C, preferences, customization
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── customer_picker.py   # Quick customer search & select
│   │   ├── product_picker.py    # Category selector with HSN auto-fill
│   │   ├── print_preview.py     # PDF preview before print/save
│   │   ├── confirm_dialog.py    # Generic yes/no confirmation
│   │   ├── backup_dialog.py     # Backup/restore wizard
│   │   └── import_data_dialog.py # Import data from Excel/CSV/backup
│   └── wizards/
│       ├── __init__.py
│       └── first_run_wizard.py  # Multi-step onboarding wizard for new businesses
├── services/
│   ├── ...
│   ├── customization_engine.py  # PDF layout builder, field visibility engine
│   └── data_import_export.py    # Import/export business data (Excel, CSV, SQLite backup)
├── assets/
│   ├── logo.png                 # Company logo for PDF header
│   ├── stamp.png                # Company stamp for PDF
│   ├── icons/                   # UI icons (SVG preferred)
│   └── fonts/                   # PDF fonts if needed
├── tests/
│   ├── test_gst_engine.py
│   ├── test_number_generator.py
│   ├── test_num_to_words.py
│   ├── test_calculator.py
│   ├── test_validator.py
│   └── test_gstr1.py
└── requirements.txt
```

---

## 2. DATABASE SCHEMA

### 2.1 `company_profile` — Seller Identity (Single Row)
```sql
CREATE TABLE company_profile (
    id              INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton
    name            TEXT NOT NULL,           -- Set by First-Run Wizard (no defaults)
    address_line1   TEXT,
    address_line2   TEXT,
    phone           TEXT,
    email           TEXT,
    website         TEXT,
    gstin           TEXT,                    -- 15-char GSTIN (nullable for unregistered)
    pan             TEXT,
    cin             TEXT,                    -- Nullable (only for companies, not proprietorships)
    state_name      TEXT,
    state_code      TEXT,
    bank_name       TEXT,
    bank_branch     TEXT,
    account_no      TEXT,
    account_type    TEXT DEFAULT 'Current',  -- Current / Savings
    ifsc_code       TEXT,
    logo_path       TEXT,                    -- Path to logo image
    stamp_path      TEXT,                    -- Path to stamp image
    signature_label TEXT DEFAULT 'Authorised Signatory',  -- Customizable
    currency_symbol TEXT DEFAULT '₹',        -- Configurable per business
    financial_year_start INTEGER DEFAULT 4,  -- April (month number 1-12)
    is_setup_complete INTEGER DEFAULT 0,     -- 0 = First-Run Wizard not done
    updated_at      TEXT DEFAULT (datetime('now'))
);
-- NOTE: ALL fields are blank by default. First-Run Wizard populates them.
-- No hardcoded company data anywhere in the codebase.
```

### 2.2 `customers` — Buyer Master
```sql
CREATE TABLE customers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    company_name    TEXT,               -- Can differ from name (e.g., contact vs company)
    mobile          TEXT,
    email           TEXT,
    gstin           TEXT,               -- 15-char GSTIN (nullable for unregistered)
    pan             TEXT,               -- 10-char PAN
    address_line1   TEXT,
    address_line2   TEXT,
    state_code      TEXT REFERENCES state_master(code),
    vendor_code     TEXT,
    is_active       INTEGER DEFAULT 1,  -- Soft delete
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_customers_gstin ON customers(gstin);
CREATE INDEX idx_customers_mobile ON customers(mobile);
```

### 2.3 `products` — Service/Product Category ↔ HSN
```sql
CREATE TABLE products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name   TEXT NOT NULL UNIQUE,  -- "Wirecut Job work", "Gauge Design", etc.
    hsn_code        TEXT NOT NULL,          -- "998391", "82071900", etc.
    default_rate    INTEGER,                -- Paise (₹1,000 → 100000). Optional default unit price
    gst_rate        REAL DEFAULT 18.0,      -- GST % (18% default, configurable) — not money, stays REAL
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_products_category ON products(category_name);
CREATE INDEX idx_products_hsn ON products(hsn_code);
```

### 2.4 `state_master` — Indian States/UTs (GST Codes)
```sql
CREATE TABLE state_master (
    code            TEXT PRIMARY KEY,       -- "06", "07", "27", etc.
    state_name      TEXT NOT NULL           -- "Haryana", "Delhi", "Maharashtra"
);
-- Seeded with all 39 entries from the Excel StateMaster sheet
```

### 2.5 `documents` — Unified table for all 5 document types
```sql
CREATE TABLE documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identity
    document_number TEXT NOT NULL UNIQUE,    -- "2026IN0001", "2026QT0003", etc.
    document_type   TEXT NOT NULL CHECK (document_type IN ('IN','QT','PI','DC','PO')),
    -- IN=Tax Invoice, QT=Quotation, PI=Proforma Invoice
    -- DC=Delivery Challan, PO=Purchase Order
    
    -- Dates
    document_date   TEXT NOT NULL,           -- ISO format: 2026-01-23
    supply_date     TEXT,                    -- Date of supply (optional)
    
    -- Customer Link
    customer_id     INTEGER REFERENCES customers(id),
    customer_name   TEXT,                    -- Denormalized for quick access
    customer_gstin  TEXT,                    -- Snapshot at time of creation
    
    -- Addresses (snapshot — customer might change address later)
    buyer_address1  TEXT,
    buyer_address2  TEXT,
    buyer_state_code TEXT,
    buyer_state_name TEXT,                   -- Derived from state_master at creation
    buyer_pan       TEXT,
    
    -- Logistics / Reference
    vehicle_no      TEXT,
    gr_lr_no        TEXT,
    place_of_supply TEXT,                    -- State name for GST determination
    po_no_date      TEXT,                    -- PO reference
    vendor_code     TEXT,
    dsr_number      TEXT,
    
    -- Totals (denormalized for fast queries/reports)
    -- ALL MONEY VALUES STORED AS INTEGER PAISE (₹100.50 → 10050)
    total_taxable   INTEGER DEFAULT 0,      -- Paise
    total_cgst      INTEGER DEFAULT 0,      -- Paise
    total_sgst      INTEGER DEFAULT 0,      -- Paise
    total_igst      INTEGER DEFAULT 0,      -- Paise
    grand_total     INTEGER DEFAULT 0,      -- Paise
    amount_in_words TEXT,                    -- "Fifteen Thousand Seven Hundred..."
    
    -- Copy type last printed
    copy_type       TEXT DEFAULT 'ORIGINAL FOR RECIPIENT',
    
    -- Metadata
    remarks         TEXT,
    status          TEXT DEFAULT 'draft' CHECK (status IN ('draft','saved','exported','cancelled')),
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_documents_number ON documents(document_number);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_date ON documents(document_date);
CREATE INDEX idx_documents_customer ON documents(customer_id);
CREATE INDEX idx_documents_status ON documents(status);
```

### 2.6 `document_items` — Line Items
```sql
CREATE TABLE document_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    serial_no       INTEGER NOT NULL,       -- 1, 2, 3...
    
    -- Product info (snapshot)
    category_name   TEXT NOT NULL,           -- "Wirecut Job work"
    item_name       TEXT,                    -- Description / sub-item name  
    hsn_code        TEXT NOT NULL,           -- "998391"
    
    -- Pricing
    -- MONEY = INTEGER PAISE (₹100.50 → 10050). Qty/Rate/Discount stay REAL.
    quantity        REAL NOT NULL DEFAULT 1,
    rate            INTEGER NOT NULL DEFAULT 0,  -- Paise (₹1,000 → 100000)
    discount_pct    REAL DEFAULT 0,               -- 0.05 = 5% (not money, stays REAL)
    taxable_amount  INTEGER NOT NULL DEFAULT 0,   -- Paise: qty * rate * (1 - disc)
    
    -- Tax (only one pair will be non-zero per item)
    cgst_rate       REAL DEFAULT 0,          -- 9 (percent — not money, stays REAL)
    cgst_amount     INTEGER DEFAULT 0,       -- Paise
    sgst_rate       REAL DEFAULT 0,          -- 9 (percent)
    sgst_amount     INTEGER DEFAULT 0,       -- Paise
    igst_rate       REAL DEFAULT 0,          -- 18 (percent)
    igst_amount     INTEGER DEFAULT 0,       -- Paise
    
    -- Line total
    line_total      INTEGER NOT NULL DEFAULT 0, -- Paise: taxable + all taxes
    
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_items_document ON document_items(document_id);
CREATE INDEX idx_items_hsn ON document_items(hsn_code);
```

### 2.7 `terms_conditions` — T&C Per Document Type
```sql
CREATE TABLE terms_conditions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    document_type   TEXT NOT NULL UNIQUE REFERENCES doc_type_config(code),
    tc_text         TEXT,                    -- Multi-line terms text
    is_enabled      INTEGER DEFAULT 1        -- Toggle T&C on/off per type
);
-- Seeded with 5 default types (all blank — user fills via Settings → T&C tab)
-- When user adds custom doc type, a matching T&C row is auto-created
```

### 2.8 `purchases` — Expense/Purchase Register
```sql
CREATE TABLE purchases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_date   TEXT NOT NULL,
    invoice_no      TEXT,
    description     TEXT,
    amount          INTEGER DEFAULT 0,      -- Paise (₹18,500 → 1850000)
    vendor_name     TEXT,
    category        TEXT REFERENCES purchase_categories(name),
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_purchases_date ON purchases(purchase_date);
CREATE INDEX idx_purchases_vendor ON purchases(vendor_name);
CREATE INDEX idx_purchases_category ON purchases(category);
```

### 2.8.1 `purchase_categories` — Expense Categories (User-Extensible)
```sql
CREATE TABLE purchase_categories (
    name            TEXT PRIMARY KEY,       -- "Raw Material", "Tooling", etc.
    sort_order      INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1
);
-- Seeded: Raw Material, Tooling, Utility, Rent, Maintenance, Transport, Salary, Miscellaneous
-- User can add custom categories via Purchase Tracker [+] button
```

### 2.9 `invoice_counter` — Sequence Tracker (Per Type Per Year)
```sql
CREATE TABLE invoice_counter (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    year            INTEGER NOT NULL,          -- 2026
    doc_type        TEXT NOT NULL,              -- 'IN', 'QT', 'PI', 'DC', 'PO'
    last_number     INTEGER NOT NULL DEFAULT 0, -- 0001, 0002...
    UNIQUE(year, doc_type)
);
```

### 2.10 `app_settings` — Key-Value Preferences
```sql
CREATE TABLE app_settings (
    key             TEXT PRIMARY KEY,
    value           TEXT
);
-- Examples: 'default_pdf_path', 'last_backup_date', 'theme', 'language'
```

### 2.10.1 `db_version` — Schema Version Tracker
```sql
CREATE TABLE db_version (
    version         INTEGER PRIMARY KEY,     -- Current schema version (1, 2, 3...)
    applied_at      TEXT DEFAULT (datetime('now')),
    description     TEXT                      -- "Added transport_mode to documents"
);
-- INSERT INTO db_version (version, description) VALUES (1, 'Initial schema v1.0');
```

**Schema Migration Engine (`database/migrations.py`):**
```
App starts → main.py
  │
  ├─→ Open/create billing.db
  ├─→ Read MAX(version) from db_version
  │     │
  │     ├─→ No db_version table? → Fresh install → run full CREATE script → set version=1
  │     │
  │     ├─→ DB version < APP version? → Run incremental migrations:
  │     │     migration_002():  ALTER TABLE documents ADD COLUMN transport_mode TEXT;
  │     │     migration_003():  ALTER TABLE ... ;
  │     │     ...up to current APP_SCHEMA_VERSION
  │     │     → Update db_version with each step
  │     │
  │     └─→ DB version == APP version? → All good, continue to UI
  │
  └─→ Launch app
```

**Migration file structure (in `database/migrations.py`):**
```python
APP_SCHEMA_VERSION = 1  # Bump this when schema changes

MIGRATIONS = {
    # version: (sql_statements, description)
    2: ("ALTER TABLE documents ADD COLUMN transport_mode TEXT;",
        "Added transport_mode field to documents"),
    3: ("ALTER TABLE purchases ADD COLUMN gst_amount INTEGER DEFAULT 0;",
        "Added GST tracking to purchases"),
    # ... future migrations added here
}

def run_migrations(conn, current_db_version: int):
    for ver in range(current_db_version + 1, APP_SCHEMA_VERSION + 1):
        sql, desc = MIGRATIONS[ver]
        conn.execute(sql)
        conn.execute("INSERT INTO db_version VALUES (?, datetime('now'), ?)", (ver, desc))
    conn.commit()
```

### 2.11 `pdf_template_settings` — Invoice/Document Layout Customization
```sql
CREATE TABLE pdf_template_settings (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),  -- Singleton

    -- Header Zone
    show_logo           INTEGER DEFAULT 1,       -- 0 = hide logo
    logo_position       TEXT DEFAULT 'left',     -- 'left', 'center', 'right'
    logo_width_mm       REAL DEFAULT 25,         -- Logo width in mm
    show_stamp          INTEGER DEFAULT 1,
    show_cin            INTEGER DEFAULT 1,       -- Some businesses don't have CIN
    show_website        INTEGER DEFAULT 1,
    header_color_hex    TEXT DEFAULT '#000000',   -- Brand color for header bar

    -- Document Fields Visibility (toggle per field)
    show_vehicle_no     INTEGER DEFAULT 1,       -- Relevant for manufacturing/transport
    show_gr_lr_no       INTEGER DEFAULT 1,       -- GR/LR number
    show_po_field       INTEGER DEFAULT 1,       -- PO No & Date
    show_vendor_code    INTEGER DEFAULT 1,       -- Vendor code
    show_dsr_number     INTEGER DEFAULT 1,       -- DSR Number
    show_supply_date    INTEGER DEFAULT 1,       -- Date of supply
    show_place_of_supply INTEGER DEFAULT 1,      -- Place of supply

    -- Item Table Columns Visibility
    show_discount_col   INTEGER DEFAULT 1,       -- Discount % column
    show_hsn_col        INTEGER DEFAULT 1,       -- HSN/SAC column (mandatory for GST, but toggle for display)

    -- Footer Zone
    show_bank_details   INTEGER DEFAULT 1,       -- Show bank on invoice
    show_amount_in_words INTEGER DEFAULT 1,
    show_tc             INTEGER DEFAULT 1,       -- Show T&C on last page
    footer_note         TEXT DEFAULT 'This is a Computer Generated Invoice',

    -- Copy Types (JSON array of enabled labels)
    copy_types_json     TEXT DEFAULT '["Original for Recipient","Duplicate for Transporter","Triplicate for Supplier","Extra Copy"]',

    -- Font & Style
    font_family         TEXT DEFAULT 'Helvetica', -- 'Helvetica', 'Times', 'Courier', or custom path
    base_font_size      REAL DEFAULT 8,           -- Base font size in pt
    
    updated_at          TEXT DEFAULT (datetime('now'))
);
```

### 2.12 `doc_type_config` — Configurable Document Types
```sql
CREATE TABLE doc_type_config (
    code            TEXT PRIMARY KEY,            -- 'IN', 'QT', 'PI', 'DC', 'PO', or custom
    display_name    TEXT NOT NULL,               -- 'Tax Invoice', 'Quotation', etc.
    prefix          TEXT NOT NULL,               -- 'IN', 'QT' — used in doc number
    is_enabled      INTEGER DEFAULT 1,           -- User can disable types they don't use
    is_gst_doc      INTEGER DEFAULT 1,           -- Whether this doc type goes into GSTR-1
    number_format   TEXT DEFAULT '{YYYY}{PREFIX}{NNNN}', -- Customizable format
    padding_digits  INTEGER DEFAULT 4,           -- 0001 vs 001 vs 00001
    sort_order      INTEGER DEFAULT 0            -- Display order in dropdown
);
-- Seeded with 5 default types; user can add custom types via Settings
-- number_format tokens: {YYYY}, {YY}, {FY} (fin.year), {PREFIX}, {NNNN}, {MM}, {COMPANY}
```

### ER Diagram (Relationships)
```
company_profile (1) ──── used globally (blank on fresh install)
                          │
                          └──── pdf_template_settings (1) ── layout config

customers (1) ◄──── (N) documents
                          │
                          ├──── (N) document_items
                          │           │
                          │           └──── products (lookup HSN + GST rate)
                          │
                          └──── state_master (lookup state name)

doc_type_config ──── defines available doc types + number format

terms_conditions ──── keyed by document_type (from doc_type_config.code)

terms_conditions ──── keyed by document_type (from doc_type_config.code)

invoice_counter ──── keyed by (year, doc_type)

purchases ──── standalone expense log (with categories)

app_settings ──── key-value pairs (theme, paths, preferences)
```

---

## 3. BACKEND MODULES

### 3.1 `gst_engine.py` — Tax Calculation Core

**Responsibilities:**
- Determine if transaction is **intra-state** (CGST+SGST) or **inter-state** (IGST)
- Compare seller's state code (from `company_profile.state_code`) with buyer's state code (from `customers.state_code` or first 2 chars of GSTIN)
- Apply configurable GST rate (default 18% → 9%+9% or 18%)
- Handle edge cases: no GSTIN (unregistered), empty state, export

**Rules replicated from Excel:**
```
IF buyer_state == seller_state (both "06" / "HARYANA"):
    CGST = taxable × (gst_rate / 2)%   → 9%
    SGST = taxable × (gst_rate / 2)%   → 9%
    IGST = 0
ELSE:
    CGST = 0
    SGST = 0
    IGST = taxable × gst_rate%         → 18%
```

### 3.2 `number_generator.py` — Document Number Sequencing

**Format:** `{YYYY}{TYPE_CODE}{NNNN}`

| Doc Type | Code | Example |
|---|---|---|
| Tax Invoice | IN | 2026IN0001 |
| Quotation | QT | 2026QT0001 |
| Proforma Invoice | PI | 2026PI0001 |
| Delivery Challan | DC | 2026DC0001 |
| Purchase Order | PO | 2026PO0001 |

**Logic (from VBA Module3):**
1. Read `invoice_counter` for (current_year, doc_type)
2. If no row exists → start at 0001, create counter row
3. If year changed → reset to 0001
4. Increment atomically within a transaction
5. Return formatted string

**Critical:** Use SQL transaction with `UPDATE ... SET last_number = last_number + 1` to prevent duplicates under any circumstance.

### 3.3 `num_to_words.py` — Indian Number-to-Words

**Exact replication of VBA Module5:**
- Indian grouping: Crore → Lakh → Thousand → Hundred → Tens/Ones
- Handles paise (2 decimal places)
- Output: `"Fifteen Thousand Seven Hundred Forty Three Rupees and Fifty Six Paise Only"`

### 3.4 `calculator.py` — Line-Item & Document Totals

> **CRITICAL: Money Handling Policy**
> - All monetary calculations use Python's `decimal.Decimal` (not `float`)
> - `from decimal import Decimal, ROUND_HALF_UP`
> - All inputs converted to `Decimal(str(value))` before any arithmetic
> - Final results rounded to 2 decimal places then stored as **integer paise** (× 100)
> - Display/PDF layer converts paise back to ₹ format: `paise // 100` + `.` + `paise % 100`
> - **Never use `float` for any money value anywhere in the codebase**

**Per line item (all in Decimal, stored as paise):**
```python
from decimal import Decimal, ROUND_HALF_UP

PAISE = Decimal('100')
TWO_PLACES = Decimal('0.01')

# rate is already in paise from DB; convert to rupees for calc
rate_rupees = Decimal(rate_paise) / PAISE
taxable = (Decimal(str(quantity)) * rate_rupees * (1 - Decimal(str(discount_pct)))).quantize(TWO_PLACES, ROUND_HALF_UP)
cgst_amount = (taxable * Decimal(str(cgst_rate)) / 100).quantize(TWO_PLACES, ROUND_HALF_UP)
sgst_amount = (taxable * Decimal(str(sgst_rate)) / 100).quantize(TWO_PLACES, ROUND_HALF_UP)
igst_amount = (taxable * Decimal(str(igst_rate)) / 100).quantize(TWO_PLACES, ROUND_HALF_UP)
line_total = taxable + cgst_amount + sgst_amount + igst_amount

# Store as paise (integer)
taxable_paise = int(taxable * PAISE)
line_total_paise = int(line_total * PAISE)
```

**Document totals:**
```python
total_taxable = SUM(all items taxable_paise)   # Sum of integers — no drift
total_cgst    = SUM(all items cgst_paise)
total_sgst    = SUM(all items sgst_paise)
total_igst    = SUM(all items igst_paise)
grand_total   = total_taxable + total_cgst + total_sgst + total_igst
amount_in_words = num_to_words(grand_total / 100)  # Convert paise → rupees for words
```

**Display helper (used everywhere in UI + PDF):**
```python
def format_currency(paise: int, symbol: str = '₹') -> str:
    """Convert integer paise to display string: 1234567 → '₹12,345.67'"""
    rupees = paise // 100
    remaining = paise % 100
    # Indian numbering: 12,34,567
    return f"{symbol}{rupees:,}.{remaining:02d}"
```

### 3.5 `validator.py` — Input Validation

| Field | Rule |
|---|---|
| GSTIN | 15 chars, format: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$` |
| PAN | 10 chars, format: `^[A-Z]{5}[0-9]{4}[A-Z]{1}$` |
| Mobile | 10 digits, starts with 6-9 |
| Email | Standard email regex |
| HSN | 4, 6, or 8 digit numeric string |
| Document Number | Format: `^[0-9]{4}(IN|QT|PI|DC|PO)[0-9]{4}$` |
| Date | Valid date, not future (for invoices), ISO format internally |
| Amount | Non-negative, max 2 decimal places |
| State Code | Must exist in `state_master` |
| Quantity | Positive number |
| Rate | Non-negative |
| Discount | 0 ≤ discount ≤ 1 (0% to 100%) |

### 3.6 `gstr1_generator.py` — GSTR-1 Report

**Full port of `gstr1_generator_COMPLETE.py` (1074 lines) rewritten to:**
1. Read from SQLite `documents` + `document_items` instead of Excel
2. Filter by date range and document_type = 'IN' only (tax invoices)
3. Generate same 14-sheet Excel workbook:

| Sheet | Description | Data Source |
|---|---|---|
| GSTR1 Summary | Aggregate totals | All filtered invoices |
| b2b/sez/de | B2B by GSTIN, grouped by rate | Invoices where buyer has GSTIN |
| b2cl | B2C Large (inter-state > ₹2.5L) | IGST invoices, grand_total > 250000 |
| b2cs | B2C Small (summary by rate+POS) | Remaining B2C |
| cdnr | Credit/Debit notes (registered) | Future: when CN/DN support added |
| cdnur | Credit/Debit notes (unregistered) | Future |
| exp | Export invoices | Future |
| at | Advance tax received | Future |
| atadj | Advance tax adjustments | Future |
| exemp | Exempt/Nil/Non-GST | Future |
| hsn(b2b) | HSN summary for B2B | Grouped by HSN from items |
| hsn(b2c) | HSN summary for B2C | Grouped by HSN from items |
| itemSummary | All individual items expanded | document_items with joins |
| docs | Document serial summary | Count of docs in number ranges |

### 3.7 `pdf_controller.py` — PDF Generation

**Replaces Excel VBA Module10 + invoice_gen.py**

Features:
- **Exact A4 layout** — customizable via `pdf_template_settings`
- **10-item pagination** — if >10 items, split into pages with "Continued on next page"
- **Logo** in header — position (left/center/right) and size from settings
- **Stamp** in signature area (bottom-right) — toggleable
- **Copy type** label (from `pdf_template_settings.copy_types_json`)
- **T&C** on last page only (from `terms_conditions` table, toggleable per type)
- **Amount in words** (Indian format, toggleable)
- **Dynamic content** — all fields populated from document + items
- **Field visibility** — reads `pdf_template_settings` to show/hide fields
- **Font & style** — font family and base size from settings
- **Header color** — brand color from settings
- **Footer note** — customizable text from settings
- **Signature label** — from `company_profile.signature_label`
- **Currency symbol** — from `company_profile.currency_symbol`

### 3.8 `backup_manager.py` — Data Safety

- **Export:** Copy SQLite .db file to chosen location with timestamp
- **Import:** Restore from a backup .db file (with confirmation)
- **Auto-backup:** On app close, if >24h since last backup, prompt user
- **Excel export:** Dump any table to .xlsx for external use

---

## 4. UI / GUI DESIGN

### 4.1 Main Window Layout
```
┌──────────────────────────────────────────────────────────────┐
│  ☰  GST Billing Suite                           ─ □ ✕      │
├────────────┬─────────────────────────────────────────────────┤
│            │                                                 │
│  📊 Dashboard  │          PAGE CONTENT AREA                 │
│            │          (swapped by sidebar)                   │
│  📝 New Doc    │                                            │
│            │                                                 │
│  📋 Documents  │                                            │
│            │                                                 │
│  👥 Customers  │                                            │
│            │                                                 │
│  📦 Products   │                                            │
│            │                                                 │
│  🛒 Purchases  │                                            │
│            │                                                 │
│  📊 GSTR-1     │                                            │
│            │                                                 │
│  📈 Reports    │                                            │
│            │                                                 │
│  ⚙️  Settings  │                                            │
│            │                                                 │
├────────────┤                                                 │
│  💾 Backup     │                                            │
│  ℹ️  About     │                                            │
└────────────┴─────────────────────────────────────────────────┘
```

### 4.2 Dashboard Page
```
┌─────────────────────────────────────────────────────────────┐
│  DASHBOARD                                    Feb 2026      │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ ₹ Revenue│ Invoices │ Quotations│ Customers│                │
│ THIS MTH │ THIS MTH │ THIS MTH  │ TOTAL   │   Revenue      │
│ ₹2,45,000│    12    │     8     │   52    │   Chart         │
│ ▲ 15%    │ ▲ 3      │ ▼ 2      │ +5 new  │   (6 months)   │
├──────────┴──────────┴──────────┴─────┬────┴─────────────────┤
│  RECENT DOCUMENTS                     │  TOP CUSTOMERS      │
│  ┌─────────────────────────────────┐  │  ┌──────────────┐   │
│  │ {doc_no}    {customer_name}     │  │  │ Customer A   │   │
│  │ ₹xx,xxx   dd-Mon   Tax Invoice │  │  │ ₹x,xx,000   │   │
│  │ {doc_no}    {customer_name}     │  │  │ Customer B   │   │
│  │ ₹xx,xxx   dd-Mon   Quotation   │  │  │ ₹x,xx,000   │   │
│  │ {doc_no}    {customer_name}     │  │  │ Customer C   │   │
│  │ ₹xx,xxx   dd-Mon   Tax Invoice │  │  │ ₹x,xx,000   │   │
│  └─────────────────────────────────┘  │  └──────────────┘   │
├───────────────────────────────────────┴──────────────────────┤
│  PENDING ACTIONS                                             │
│  ⚠ 3 draft invoices unsaved  │  ⚠ GSTR-1 Jan 2026 not filed│
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Document Editor Page (The Core)
```
┌─────────────────────────────────────────────────────────────────┐
│  NEW TAX INVOICE              [Save Draft] [Export] [PDF] [🖨️]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Doc Type: [TAX INVOICE ▼]    Invoice No: 2026IN0004  (auto)    │
│  Copy:     [ORIGINAL FOR RECIPIENT ▼]                            │
│                                                                  │
│  ┌─── SELLER (auto-filled) ──────┐  ┌─── BUYER ─────────────┐  │
│  │ (from company_profile)        │  │ Customer: [🔍 Search.. ]│  │
│  │ Business Name                 │  │ Name: ___________      │  │
│  │ Address Line 1                │  │ Addr1: ___________     │  │
│  │ GSTIN: _______________        │  │ Addr2: ___________     │  │
│  │ PAN: __________               │  │ GSTIN: _______________  │  │
│  │ CIN: _______________ (if set) │  │ State: [▼ Select] (##) │  │
│  │ State: _________ (##)         │  │ PAN: ___________       │  │
│  └───────────────────────────────┘  └────────────────────────┘  │
│  Invoice Date: [28/01/2026]  Supply Date: [__/__/____]          │
│  Place of Supply: [Haryana ▼]  Vehicle No: [________]           │
│  GR/LR No: [________]  PO No & Date: [________________]        │
│  Vendor Code: [________]  DSR Number: [________]                │
│  ↑ Fields shown/hidden based on Settings → Invoice Layout       │
│                                                                  │
│  ┌─── LINE ITEMS ──────────────────────────────────────────────┐│
│  │ S.No │ Category ▼     │ Item Name │ HSN    │ Qty│ Rate    ││
│  │      │                │           │(auto)  │    │         ││
│  │──────│────────────────│───────────│────────│────│─────────││
│  │ dis% │ Taxable Amt    │ SGST %    │SGST ₹  │CGST%│CGST ₹  ││
│  │      │ (computed)     │(computed) │(comp)  │(co) │(comp)  ││
│  │──────│────────────────│───────────│────────│────│─────────││
│  │  1   │ Wirecut Job    │ hello     │ 998391 │ 1  │ 1,000  ││
│  │  0%  │ 1,000.00       │ 9%       │ 90.00  │ 9% │ 90.00  ││
│  │──────│────────────────│───────────│────────│────│─────────││
│  │  2   │ Gauge Design   │ world     │ 82071900│ 1 │ 10,000 ││
│  │  0%  │ 10,000.00      │ 9%       │ 900.00 │ 9% │ 900.00 ││
│  │──────│────────────────│───────────│────────│────│─────────││
│  │               [+ Add Item]  [− Remove Last]                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─── TOTALS ──────────────────────────────────────────────────┐│
│  │ Total Taxable: ₹11,000.00    │ Bank: AXIS Bank            ││
│  │ Add SGST @9%:  ₹   990.00   │ A/C:  925020047471799      ││
│  │ Add CGST @9%:  ₹   990.00   │ IFSC: UTIB0001081          ││
│  │ Add IGST @18%: ₹     0.00   │                             ││
│  │ ═══════════════════════════  │                             ││
│  │ GRAND TOTAL:   ₹12,980.00   │                             ││
│  │                               │                             ││
│  │ In Words: Twelve Thousand Nine Hundred Eighty Rupees Only  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Remarks: [_________________________________________________]   │
│  T&C: (auto-filled from settings for TAX INVOICE)               │
│  1) Payment should be made through A/C payee...                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.4 Document List Page
```
┌─────────────────────────────────────────────────────────────────┐
│  DOCUMENTS                    [🔍 Search...] [Filter ▼] [+ New]│
├─────────────────────────────────────────────────────────────────┤
│  Type: [All ▼]  Status: [All ▼]  From: [__/__/____]           │
│  To: [__/__/____]  Customer: [All ▼]                           │
├────────┬──────────┬────────────────┬──────────┬────────┬───────┤
│  Doc # │ Date     │ Customer       │ Amount   │ Type   │Status │
├────────┼──────────┼────────────────┼──────────┼────────┼───────┤
│IN0003  │23-Jan-26 │Nigasavi Soln   │₹15,743.56│Invoice │ ✅    │
│QT0008  │28-Jan-26 │UNO Mindarika   │₹27,704.04│Quotation│ ✅   │
│IN0002  │23-Jan-26 │Hesha Mgmt      │₹1,685.04 │Invoice │ ✅    │
│IN0001  │23-Jan-26 │(Walk-in)       │₹1,328.68 │Invoice │ ✅    │
│QT0007  │28-Jan-26 │(Walk-in)       │₹0.00     │Quotation│ 📝   │
├────────┴──────────┴────────────────┴──────────┴────────┴───────┤
│  [View] [Edit] [Duplicate] [PDF] [Delete]      Page 1 of 3    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.5 Customer Manager Page
```
┌─────────────────────────────────────────────────────────────────┐
│  CUSTOMERS                          [🔍 Search...]  [+ Add New]│
├────────────────────────┬────────────────────────────────────────┤
│  CUSTOMER LIST         │  CUSTOMER DETAIL                      │
│  ┌──────────────────┐  │  ┌──────────────────────────────────┐ │
│  │ MS Seisakusho    │  │  │ Name: MS SEISAKUSHO INDIA PVT   │ │
│  │ Shankar Moulding │  │  │ Mobile: ___________              │ │
│  │ ► Motherson Tools│  │  │ Email: ___________               │ │
│  │ Paramjyoti movers│  │  │ GSTIN: 06ABP81910G1Z8   ✅      │ │
│  │ SARV SAI IND.    │  │  │ PAN: ___________                 │ │
│  │ SANKO SVANCE     │  │  │ Address 1: G-141, RICO Ind...    │ │
│  │ INNOVATIVE COMP  │  │  │ Address 2: Karoli, Alwar - Raj.  │ │
│  │ INNOVATION TOOLS │  │  │ State: [Rajasthan ▼] (08)        │ │
│  │ ...              │  │  │ Vendor Code: ___________          │ │
│  └──────────────────┘  │  │                                   │ │
│                         │  │ [Save] [Cancel]                   │ │
│  Showing 52 customers  │  │                                   │ │
│                         │  │ ─── RECENT DOCUMENTS ───          │ │
│                         │  │ 2026IN0015  ₹45,000  12-Feb      │ │
│                         │  │ 2026QT0009  ₹12,500  08-Feb      │ │
│                         │  └──────────────────────────────────┘ │
└────────────────────────┴────────────────────────────────────────┘
```

### 4.6 Product Manager Page
```
┌─────────────────────────────────────────────────────────────┐
│  PRODUCTS / SERVICES                    [🔍 Search] [+ Add]│
├──────┬──────────────────────────────┬──────────┬────────────┤
│  #   │ Category Name               │ HSN Code │ GST Rate   │
├──────┼──────────────────────────────┼──────────┼────────────┤
│  1   │ Wirecut Job work             │ 998391   │ 18%        │
│  2   │ Fixture Design               │ 998391   │ 18%        │
│  3   │ Gauge Design                 │ 82071900 │ 18%        │
│  4   │ Product                      │ 82071900 │ 18%        │
│  5   │ Plastic Inj Mould Design     │ 998391   │ 18%        │
│  6   │ MOULD FLOW ANALYSIS          │ 998391   │ 18%        │
│  7   │ 3D PRINTTING                 │ 39261091 │ 18%        │
│  ...                                                        │
│  [Edit] [Deactivate]                       17 products      │
└─────────────────────────────────────────────────────────────┘
```

### 4.7 Purchase Tracker Page
```
┌──────────────────────────────────────────────────────────────────┐
│  PURCHASES / EXPENSES             [🔍 Search...]  [+ Add New]  │
├──────────────────────────────────────────────────────────────────┤
│  From: [01/01/2026]  To: [31/01/2026]  Vendor: [All ▼]        │
│  Category: [All ▼]                      [Apply Filters]        │
├──────┬───────────┬──────────────┬──────────────┬────────┬───────┤
│ Date │ Invoice # │ Vendor       │ Description  │Category│Amount │
├──────┼───────────┼──────────────┼──────────────┼────────┼───────┤
│21-Jan│ VND-0045  │ Steel Mart   │ MS Flat Bars │Raw Mat.│₹18,500│
│22-Jan│ VND-0046  │ Tool House   │ Carbide Bits │Tooling │₹ 7,200│
│23-Jan│ ELC-2145  │ DHBVN        │ Electricity  │Utility │₹12,400│
│25-Jan│ RNT-JAN   │ Dayanand Est.│ Rent Jan'26  │Rent    │₹35,000│
│28-Jan│ VND-0047  │ Wire Supplies│ EDM Wire 5Kg │Raw Mat.│₹22,800│
│30-Jan│ MNT-0012  │ Servo Repair │ CNC Servo Fix│Maint.  │₹ 8,500│
├──────┴───────────┴──────────────┴──────────────┴────────┴───────┤
│                                                                  │
│  ┌──── SUMMARY ────────────────────────────────────────────────┐ │
│  │ Total (filtered): ₹1,04,400     Entries: 6                 │ │
│  │                                                              │ │
│  │ By Category:   Raw Material: ₹41,300  │  Tooling: ₹7,200   │ │
│  │                Utility: ₹12,400       │  Rent: ₹35,000     │ │
│  │                Maintenance: ₹8,500    │                     │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [Edit] [Delete] [📥 Export to Excel]            Page 1 of 1    │
└──────────────────────────────────────────────────────────────────┘
```

**Add/Edit Purchase Dialog:**
```
┌────────────────────────────────────────────────┐
│  ADD NEW PURCHASE                      [✕]    │
├────────────────────────────────────────────────┤
│                                                │
│  Date:        [📅 28/01/2026           ]      │
│  Invoice No:  [VND-0048               ]       │
│  Vendor:      [🔍 Type to search...   ]  [+] │
│  Description: [________________________]      │
│  Category:    [Raw Material        ▼]    [+]  │
│  Amount (₹):  [0.00                   ]       │
│  Notes:       [________________________]      │
│               [________________________]      │
│                                                │
│  [Cancel]                          [Save]     │
└────────────────────────────────────────────────┘
```
- **Vendor auto-suggest:** Remembers previously used vendor names for quick entry
- **Category management:** Predefined list + user can add custom categories via [+] button
- **Default categories seeded:** Raw Material, Tooling, Utility, Rent, Maintenance, Transport, Salary, Miscellaneous
- **Export:** Filtered view exportable to Excel with column headers

### 4.8 Reports Page
```
┌──────────────────────────────────────────────────────────────────────┐
│  REPORTS                                                             │
├───────────┬──────────────────────────────────────────────────────────┤
│           │                                                          │
│ REPORT    │  ┌─── REPORT PARAMETERS ────────────────────────────┐   │
│ TYPES     │  │                                                   │   │
│           │  │  Period: [This Month ▼]  Custom: [__/__] to [__/__]│  │
│ ► Revenue │  │  Group By: [Monthly ▼]   Customer: [All ▼]       │   │
│   Summary │  │                                                   │   │
│           │  │  [Generate Report]                                │   │
│ Sales by  │  └───────────────────────────────────────────────────┘   │
│ Customer  │                                                          │
│           │  ┌─── REVENUE SUMMARY (Jan 2026) ────────────────────┐  │
│ Sales by  │  │                                                    │  │
│ Product   │  │  Invoices Raised: 15      Total Revenue: ₹4,52,000│  │
│           │  │  Quotations Sent: 8       Purchases:     ₹1,04,400│  │
│ Tax       │  │  Avg Invoice:     ₹30,133 Net Margin:    ₹3,47,600│  │
│ Summary   │  │                                                    │  │
│           │  │  ┌──────────────────────────────────────────────┐  │  │
│ Purchase  │  │  │  MONTHLY REVENUE TREND (Bar/Line Chart)      │  │  │
│ Summary   │  │  │                                               │  │  │
│           │  │  │  ₹5L ┤                          ██            │  │  │
│ Expense   │  │  │  ₹4L ┤          ██  ██          ██            │  │  │
│ vs Revenue│  │  │  ₹3L ┤  ██      ██  ██  ██      ██  ██       │  │  │
│           │  │  │  ₹2L ┤  ██  ██  ██  ██  ██  ██  ██  ██       │  │  │
│ Outstanding│ │  │  ₹1L ┤  ██  ██  ██  ██  ██  ██  ██  ██       │  │  │
│ /Aging    │  │  │      └──Jul─Aug─Sep─Oct─Nov─Dec─Jan─Feb       │  │  │
│           │  │  └──────────────────────────────────────────────┘  │  │
│ Doc Count │  │                                                    │  │
│ Summary   │  │  ┌──────────────────────────────────────────────┐  │  │
│           │  │  │  BREAKDOWN TABLE                              │  │  │
│ HSN-wise  │  │  │ Month   │ Invoices│ Revenue │ Tax    │Expense │  │  │
│ Summary   │  │  │ Jul'25  │    8    │₹2,80,000│₹50,400│₹45,000 │  │  │
│           │  │  │ Aug'25  │   11    │₹1,95,000│₹35,100│₹62,000 │  │  │
│           │  │  │ Sep'25  │   14    │₹3,60,000│₹64,800│₹55,000 │  │  │
│           │  │  │ ...     │  ...    │   ...   │  ...  │  ...   │  │  │
│           │  │  │ Jan'26  │   15    │₹4,52,000│₹81,360│₹1,04,400│ │  │
│           │  │  └──────────────────────────────────────────────┘  │  │
│           │  │                                                    │  │
│           │  │  [📥 Export to Excel] [📄 Export to PDF] [🖨 Print]│  │
│           │  └────────────────────────────────────────────────────┘  │
└───────────┴──────────────────────────────────────────────────────────┘
```

**Report Types Detail:**

| Report | Description | Filters | Output |
|---|---|---|---|
| **Revenue Summary** | Total invoiced revenue by period with trend chart | Date range, Monthly/Quarterly/Yearly | Chart + Table |
| **Sales by Customer** | Revenue breakdown per customer, ranked by amount | Date range, Customer filter | Table + Pie chart |
| **Sales by Product** | Revenue breakdown per product/service category | Date range, Category filter | Table + Bar chart |
| **Tax Summary** | CGST + SGST + IGST collected, grouped by month & rate | Date range | Table (GSTR-1 compatible) |
| **Purchase Summary** | Total expenses by category with trend | Date range, Category, Vendor | Chart + Table |
| **Expense vs Revenue** | Side-by-side comparison showing net margin | Date range, Monthly/Quarterly | Dual-axis chart |
| **Outstanding / Aging** | Documents in draft/saved status (not exported) sorted by age | Status filter | Table with age buckets |
| **Document Count** | Count of each doc type by period | Date range, Doc type | Summary table |
| **HSN-wise Summary** | Revenue and tax grouped by HSN/SAC code | Date range | Table (GST audit compatible) |

### 4.9 GSTR-1 Generation Page
```
┌─────────────────────────────────────────────────────────────┐
│  GSTR-1 REPORT GENERATOR                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  GSTIN: 06AATCM6932B1ZC  (from company profile)            │
│  Business: (from company profile)                            │
│                                                              │
│  Period: From [01/01/2026] To [31/01/2026]                  │
│                                                              │
│  [Generate Report]                                           │
│                                                              │
│  ┌── PREVIEW ─────────────────────────────────────────────┐ │
│  │ Invoices found: 15                                      │ │
│  │ B2B invoices: 12  │  B2C: 3                             │ │
│  │ Total taxable: ₹4,52,000                                │ │
│  │ Total CGST: ₹28,800  │ SGST: ₹28,800 │ IGST: ₹15,400 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  [📥 Export to Excel]  [📋 Copy Summary]                    │
│                                                              │
│  Status: ✅ Report generated successfully                    │
│  Saved: /Users/admin/Desktop/GSTR1_Jan_2026.xlsx            │
└─────────────────────────────────────────────────────────────┘
```

### 4.10 Settings Page (Tabbed — Full Customization Hub)
```
┌──────────────────────────────────────────────────────────────────────┐
│  SETTINGS                                                            │
├────────────────────────────────────────────────────────────────────── ┤
│  ┌─────────┬──────────┬─────────┬──────────┬────────┬──────┬──────┐ │
│  │ Company │ Bank     │ Terms & │ Document │Invoice │Theme │About │ │
│  │ Profile │ Details  │ Cond.   │ Types    │Layout  │      │      │ │
│  └─────────┴──────────┴─────────┴──────────┴────────┴──────┴──────┘ │
│                                                                      │
│  ═══ TAB: COMPANY PROFILE ═══════════════════════════════════════   │
│                                                                      │
│  Business Name:  [___________________________________]              │
│  GSTIN:          [_______________]  [✓ Validate]                    │
│  PAN:            [__________]                                        │
│  CIN:            [___________________]  (optional)                  │
│  Address Line 1: [___________________________________]              │
│  Address Line 2: [___________________________________]              │
│  Phone:          [_______________]                                   │
│  Email:          [___________________________________]              │
│  Website:        [___________________________________]              │
│  State:          [▼ Select State]  Code: (auto)                     │
│  Logo:           [📁 Choose...]  [Preview]  [Remove]               │
│  Stamp/Seal:     [📁 Choose...]  [Preview]  [Remove]               │
│  Signature Label:[Authorised Signatory_______________]              │
│  Currency Symbol:[₹_]   Financial Year Starts: [April ▼]           │
│                                                                      │
│  [Save Changes]                                                     │
│                                                                      │
│  ═══ TAB: BANK DETAILS ═════════════════════════════════════════   │
│                                                                      │
│  Bank Name:      [___________________________________]              │
│  Branch:         [___________________________________]              │
│  Account No:     [___________________________________]              │
│  Account Type:   [Current ▼]                                        │
│  IFSC Code:      [___________]                                      │
│  Show bank details on invoice?  [✓]                                 │
│                                                                      │
│  [Save Changes]                                                     │
│                                                                      │
│  ═══ TAB: TERMS & CONDITIONS ═══════════════════════════════════   │
│                                                                      │
│  Document Type: [Tax Invoice ▼]                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ 1) Payment should be made through A/C payee cheque/RTGS/    │   │
│  │    NEFT in the name of the company.                          │   │
│  │ 2) Goods once sold will not be taken back or exchanged.     │   │
│  │ 3) Subject to Gurugram jurisdiction only.                    │   │
│  │ 4) Interest @24% p.a. will be charged on delayed payment.  │   │
│  │                                                              │   │
│  │ (multi-line text editor — plain text)                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  Enable T&C on this doc type?  [✓]                                  │
│                                                                      │
│  [Save for Tax Invoice]  [Copy to All Types]                        │
│                                                                      │
│  ═══ TAB: DOCUMENT TYPES ═══════════════════════════════════════   │
│                                                                      │
│  ┌────────┬──────────────────┬────────┬──────────────────┬───────┐  │
│  │ Code   │ Display Name     │Prefix  │Number Format     │Active │  │
│  ├────────┼──────────────────┼────────┼──────────────────┼───────┤  │
│  │ IN     │ Tax Invoice      │ IN     │{YYYY}{PREFIX}{N4}│  ✓   │  │
│  │ QT     │ Quotation        │ QT     │{YYYY}{PREFIX}{N4}│  ✓   │  │
│  │ PI     │ Proforma Invoice │ PI     │{YYYY}{PREFIX}{N4}│  ✓   │  │
│  │ DC     │ Delivery Challan │ DC     │{YYYY}{PREFIX}{N4}│  ✓   │  │
│  │ PO     │ Purchase Order   │ PO     │{YYYY}{PREFIX}{N4}│  ✓   │  │
│  └────────┴──────────────────┴────────┴──────────────────┴───────┘  │
│                                                                      │
│  [Edit Selected]  [+ Add Custom Type]  [Disable Selected]          │
│                                                                      │
│  Number Format Tokens:                                              │
│  {YYYY}=Full year  {YY}=Short year  {FY}=Financial year            │
│  {PREFIX}=Type prefix  {N4}=4-digit seq  {N5}=5-digit seq          │
│  {MM}=Month  {COMPANY}=Company short code                          │
│  Preview: 2026IN0001                                                │
│                                                                      │
│  ═══ TAB: INVOICE LAYOUT ═══════════════════════════════════════   │
│                                                                      │
│  ┌─ HEADER SETTINGS ──────────────────────────────────────────────┐ │
│  │ Show Logo: [✓]    Position: [Left ▼]   Width: [25mm ▼]       │ │
│  │ Show CIN: [✓]     Show Website: [✓]                           │ │
│  │ Show Stamp: [✓]   Header Color: [■ #000000] [Pick...]        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─ DOCUMENT FIELD VISIBILITY ────────────────────────────────────┐ │
│  │ [✓] Vehicle Number     [✓] GR/LR Number                      │ │
│  │ [✓] PO No & Date       [✓] Vendor Code                       │ │
│  │ [✓] DSR Number         [✓] Supply Date                       │ │
│  │ [✓] Place of Supply                                           │ │
│  │                                                                │ │
│  │ Hint: Uncheck fields your business doesn't use.               │ │
│  │       They won't appear on the Document Editor or PDF.        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─ ITEM TABLE COLUMNS ──────────────────────────────────────────┐ │
│  │ [✓] Discount %         [✓] HSN/SAC Code                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─ FOOTER SETTINGS ─────────────────────────────────────────────┐ │
│  │ [✓] Show Bank Details   [✓] Amount in Words                  │ │
│  │ [✓] Show T&C                                                  │ │
│  │ Footer Note: [This is a Computer Generated Invoice________]   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─ COPY TYPES ──────────────────────────────────────────────────┐ │
│  │ [✓] Original for Recipient    [✓] Duplicate for Transporter  │ │
│  │ [✓] Triplicate for Supplier   [✓] Extra Copy                 │ │
│  │ [+ Add Custom Label]  [Edit Label]  [Remove]                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─ FONT & STYLE ───────────────────────────────────────────────┐  │
│  │ Font: [Helvetica ▼]   Base Size: [8pt ▼]                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  [Save Layout]  [Preview Sample PDF]                                │
│                                                                      │
│  ═══ TAB: THEME & APPEARANCE ══════════════════════════════════   │
│                                                                      │
│  App Theme:     (● Light)  (○ Dark)  (○ System)                    │
│  Accent Color:  [■ #2196F3] [Pick...]                               │
│  Sidebar Style: (● Icons+Text)  (○ Icons Only)  (○ Text Only)     │
│                                                                      │
│  [Apply Theme]                                                      │
│                                                                      │
│  ═══ TAB: DATA & BACKUP ═══════════════════════════════════════   │
│                                                                      │
│  Default PDF Save Path:  [📁 /Users/admin/Desktop/]  [Browse...]   │
│  Auto-backup: [✓ On app close if >24h since last]                   │
│  Last Backup: 15-Feb-2026 18:30                                     │
│                                                                      │
│  [💾 Backup Now]  [📂 Restore from Backup]                         │
│                                                                      │
│  ─── DATA IMPORT/EXPORT ────────────────────────────────────────   │
│  [📥 Import from Excel (.xlsm/.xlsx)]                               │
│  [📥 Import from CSV]                                               │
│  [📤 Export All Data to Excel]                                      │
│  [📤 Export Database (.db backup)]                                  │
│                                                                      │
│  ═══ TAB: ABOUT ═══════════════════════════════════════════════   │
│                                                                      │
│  GST Billing Suite v1.0                                             │
│  © 2026                                                             │
│  Python 3.13 · PyQt6 · SQLite · ReportLab                          │
│  Database: /Users/admin/Desktop/gst/billing.db                      │
│  Size: 2.4 MB  │  Records: 52 customers, 17 products, 26 invoices │
│                                                                      │
│  [Check for Updates]                                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.11 First-Run Wizard (Onboarding)
```
┌──────────────────────────────────────────────────────────────┐
│                 WELCOME TO GST BILLING SUITE                 │
│                                                              │
│  Let's set up your business in 4 simple steps.              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  STEP 1 of 4: Business Identity                      │   │
│  │  ════════════════════════════════                     │   │
│  │                                                       │   │
│  │  Business Name: [_______________________________]    │   │
│  │  GSTIN:         [_______________]  [✓ Validate]      │   │
│  │  PAN:           [__________]  (auto-extracted if GSTIN│   │
│  │  CIN:           [___________________]  (optional)    │   │
│  │                                                       │   │
│  │  Address Line 1:[_______________________________]    │   │
│  │  Address Line 2:[_______________________________]    │   │
│  │  State:         [▼ Select State]                      │   │
│  │  Phone:         [_______________]                     │   │
│  │  Email:         [_______________________________]    │   │
│  │                                                       │   │
│  │                             [Next → Step 2: Bank]    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ○───●───○───○                                              │
│  1   2   3   4                                              │
│                                                              │
│  [Skip Setup — I'll configure later in Settings]            │
└──────────────────────────────────────────────────────────────┘
```

**Wizard Steps:**

| Step | Title | Fields | Required? |
|---|---|---|---|
| 1 | Business Identity | Name, GSTIN, PAN, CIN, Address, State, Phone, Email | Name + State required, rest optional |
| 2 | Bank Details | Bank Name, Branch, Account No, Type, IFSC | All optional |
| 3 | Branding | Upload Logo, Upload Stamp/Seal, Signature Label | All optional |
| 4 | Preferences | Default GST Rate, Doc types to enable, Number format preview, Theme | All have defaults |

- **Skip option:** User can skip and configure later via Settings
- **GSTIN auto-extract:** If user enters GSTIN, auto-extract state code (first 2 chars) and PAN (chars 3-12)
- **On completion:** `company_profile.is_setup_complete = 1` — wizard never shows again
- **Can be re-run:** Settings → "Re-run Setup Wizard" button

### 4.12 Key UI Behaviors

| Behavior | Current Excel | Standalone Equivalent |
|---|---|---|
| Customer dropdown fill | VBA `cmbBuyer_Change` fills D17-D21 | Customer search dialog → auto-fills all buyer fields |
| HSN auto-lookup | Formula `VLOOKUP(D24, Product!A:B, 2, FALSE)` | On category select → auto-fill HSN from products table |
| State auto-detect | `LEFT(GSTIN, 2)` → `VLOOKUP(code, StateMaster)` | On GSTIN entry → extract state code → lookup state name |
| Tax type switch | Formula checks `H18 = "HARYANA"` | `gst_engine.py` checks buyer state vs seller state |
| Serial number | Formula `=IF(D25="","", N)` | Computed in item_grid widget, auto-renumber on add/remove |
| Taxable amount | Formula `=Qty*Rate*(1-Disc)` | Live-computed in calculator, shown in read-only cell |
| Grand total in words | ArrayFormula `NumToWords()` | `num_to_words.py` called on total change |
| T&C display | `VLOOKUP(T10, T&C!A:B, 2, FALSE)` | On doc_type change → fetch from `terms_conditions` table |
| Invoice number | VBA `GetNextInvoiceNumber()` | `number_generator.py` on new document creation |
| Add item row | VBA `AddItemRow()` | "Add Item" button in item_grid widget |
| Formula guardian | VBA `Worksheet_Change` | Not needed — computed fields are read-only in UI |

---

## 5. PDF ENGINE

### 5.1 Page Layout (A4 Portrait)
```
┌──────────────────────────────────────┐
│  ┌─LOGO─┐  {company_name}            │ ← Header zone (rows 1-10)
│  │      │  {address}                 │
│  └──────┘  GSTIN | PAN | CIN | etc   │   (CIN/Website shown per settings)
│            [COPY TYPE LABEL]         │
│──────────────────────────────────────│
│  [DOC TYPE TITLE: TAX INVOICE]       │ ← Title + doc info (rows 11-15)
│  Invoice No: 2026IN0001             │
│  Date: 28/01/2026                    │
│──────────────────────────────────────│
│  SELLER DETAILS  │  BUYER DETAILS    │ ← Parties (rows 16-21)
│  Name            │  Name             │
│  Address         │  Address          │
│  GSTIN / PAN     │  GSTIN / PAN      │
│  State / Code    │  State / Code     │
│  Bank Details    │                    │
│──────────────────────────────────────│
│ S.No│ Desc │ HSN│Qty│Rate│Tax│SGST...│ ← Item header (rows 22-23)
│─────│──────│────│───│────│───│───────│
│  1  │ Wire │998 │ 1 │1000│1K │ 90    │ ← Items (rows 24-43, max 10)
│  2  │ Gauge│820 │ 1 │10K │10K│ 900   │
│  .. │ ...  │... │...│... │...│ ...   │
│ 10  │ Last │... │...│... │...│ ...   │
│──────────────────────────────────────│
│  Total Taxable │ ₹xx,xxx            │ ← Footer totals (rows 44-54)
│  SGST @9%      │ ₹x,xxx             │
│  CGST @9%      │ ₹x,xxx             │
│  IGST @18%     │ ₹0                 │
│  GRAND TOTAL   │ ₹xx,xxx            │
│──────────────────────────────────────│
│  In Words: ... Rupees Only           │ ← Words + T&C (rows 55-62)
│  Terms & Conditions:                 │
│  1) Payment should be made through.. │
│──────────────────────────────────────│
│         For {company_name}   ┌STAMP┐ │ ← Signature (rows 58-63)
│         {signature_label}    └─────┘ │
│  *{footer_note}                      │
└──────────────────────────────────────┘
```

### 5.2 Multi-Page Pagination
```
IF items > 10:
    Page 1: Items 1-10, footer shows "Continued on next page →"
    Page 2: Items 11-20, footer shows "Continued on next page →"  
    ...
    Last Page: Remaining items + Full footer (totals + T&C + signature)
```

### 5.3 Copy Types
User can print multiple copies in one go:
- [x] Original for Recipient
- [x] Duplicate for Transporter  
- [ ] Triplicate for Supplier
- [ ] Extra Copy

Each copy is a separate page(s) with the label printed at top-right.

---

## 6. GSTR-1 ENGINE

### 6.1 Data Flow
```
SQLite DB ──→ Filter (date range, type=IN) ──→ Classify ──→ Generate Sheets
                                                   │
                                    ┌──────────────┼──────────────┐
                                    │              │              │
                              Has GSTIN?     Inter-state?    > ₹2.5L?
                                    │              │              │
                                  B2B           IGST>0         B2CL
                                  sheet          │              sheet
                                              B2CS sheet
```

### 6.2 Key Differences from Current Script
| Aspect | Current (gstr1_generator) | New (standalone) |
|---|---|---|
| Data source | Excel .xlsm file | SQLite database |
| Item parsing | `parse_comma_separated()` | Direct query from `document_items` |
| GSTIN source | Column Z (hardcoded index) | `customers.gstin` via join |
| UI | Tkinter | PyQt6 page |
| Date format | DD/MM/YYYY string | ISO date in DB, formatted on display |
| Output | Excel file only | Excel + on-screen preview |

---

## 7. VULNERABILITY & FLAW ANALYSIS

### 7.1 Flaws in Current Excel System

| # | Flaw | Severity | Root Cause | Standalone Fix |
|---|---|---|---|---|
| F1 | **Formula overwrite** — users can accidentally delete formulas (HSN lookup, tax calc, serial numbers) | 🔴 Critical | Excel allows editing any cell | Computed fields are **read-only** in UI. No user-editable formula cells. |
| F2 | **Duplicate invoice numbers** — no atomic lock; two rapid saves could create same number | 🔴 Critical | VBA reads last row, no transaction isolation | SQL `UPDATE counter SET num=num+1` inside `BEGIN EXCLUSIVE TRANSACTION` |
| F3 | **Data loss on crash** — unsaved Bill Format data lost if Excel crashes | 🔴 Critical | No auto-save; data only persists on Export | **Auto-save drafts** every 30 seconds; SQLite WAL mode for crash safety |
| F4 | **GSTIN mismatch** — gstr1 script hardcodes `06AHXPJ4596L1ZD`, Excel has `06AATCM6932B1ZC` | 🔴 Critical | Hardcoded in two places | Single source of truth: `company_profile` table |
| F5 | **No data validation** — invalid GSTIN, impossible dates, negative amounts all accepted | 🟠 High | Excel has no input validation except dropdown | `validator.py` enforces rules on every save |
| F6 | **CSV item storage** — comma-separated items in single cells; parsing errors if item names contain commas | 🟠 High | Excel row limitation hack | Normalized `document_items` table — one row per item |
| F7 | **No audit trail** — can't see who changed what, or when an invoice was modified | 🟠 High | No logging | `created_at`, `updated_at` timestamps; status transitions tracked |
| F8 | **Column drift** — Quotation Details has 33 cols, Tax Invoice Details has 32; inconsistent mapping | 🟠 High | Manual sheet creation | Single `documents` table with unified schema |
| F9 | **No backup** — single .xlsm file is the entire database; corruption = total loss | 🟠 High | Single-file architecture | Automated backup on close; manual backup/restore; SQLite is more corruption-resistant |
| F10 | **Duplicate customer entries** — "Shankar Moulding Ltd" and "Shankar Moulding Ltd." both exist | 🟡 Medium | No uniqueness enforcement | Case-insensitive name matching + merge duplicates tool |
| F11 | **Date format inconsistency** — some dates are `DD-MM-YYYY`, others `YYYY-MM-DD HH:MM:SS` | 🟡 Medium | No date format enforcement | ISO 8601 in DB (`YYYY-MM-DD`), displayed as `DD-MMM-YYYY` |
| F12 | **No search** — finding old invoices requires scrolling through detail sheets | 🟡 Medium | Excel limitations | Full-text search with filters by date, customer, amount, type, status |
| F13 | **Hardcoded tax rate** — 9%/18% baked into every formula | 🟡 Medium | Formula-based | Configurable `gst_rate` in settings; `products.gst_rate` for per-product rates |
| F14 | **No multi-page PDF** — VBA SaveAsPDF doesn't handle >10 items properly | 🟡 Medium | VBA PageSetup limitations | ReportLab pagination engine with 10-item-per-page hard limit |
| F15 | **Address snapshot missing** — if customer changes address, old invoices show new address | 🟡 Medium | Lookups are live | Address is **snapshotted** into `documents` at creation time |
| F16 | **No draft/status tracking** — can't tell if invoice is draft, finalized, or cancelled | 🟡 Medium | No concept of status | `status` field: draft → saved → exported → cancelled |
| F17 | **Print formatting fragile** — logo stacking, T&C #NAME? errors, image duplication | 🟡 Medium | openpyxl + LibreOffice conversion issues | Native ReportLab PDF — no Excel → PDF conversion needed |
| F18 | **No Purchase tracking** — Purchase sheet is empty, never used | 🟢 Low | Abandoned feature | Full purchase register with date, vendor, amount, category |
| F19 | **Empty T&C for DC/PO** — Delivery Challan and Purchase Order have no terms | 🟢 Low | Never filled in | Configurable T&C per doc type; allow blank if intended |
| F20 | **Row 24-43 hardcoded** — item rows fixed between 24-43 in formulas and VBA | 🟢 Low | Template-based design | Dynamic item list with no row limits |

### 7.2 Potential Flaws in New System (Preemptive)

| # | Risk | Mitigation |
|---|---|---|
| N1 | **SQLite concurrency** — if app opened twice, writes could conflict | Single-instance lock using `fcntl.flock()` on a lock file |
| N2 | **PDF font rendering** — ReportLab may not render ₹ symbol or regional chars | Ship with DejaVu Sans or Noto Sans font; test ₹ and Hindi chars |
| N3 | **Large dataset performance** — 10,000+ invoices could slow queries | Proper indexes (already defined); pagination in list views |
| N4 | **Backup corruption** — user restores wrong backup and loses recent data | Show backup date/time, record count before restore; keep last 3 auto-backups |
| N5 | **Screen resolution** — UI must work on 1366×768 (common) to 4K | Use relative sizing, QScrollArea, minimum window size 1200×700 |
| N6 | **Data migration** — need to import existing 52 customers + 17 products + invoices from Excel | Migration script in Phase 1 to read xlsm and populate SQLite |
| N7 | **GSTR-1 accuracy** — HSN grouping, rate grouping must match GST portal format exactly | Test against known GSTR-1 submissions; validate totals |
| N8 | **Floating-point money drift** — `REAL` (float) causes ₹15,743.560000001 or penny discrepancies in GST rounding (18% of ₹100.10 drifts) | All money stored as **INTEGER paise** in SQLite (₹100.50 → 10050). All calculations use Python `decimal.Decimal`, never `float`. Display layer converts paise → ₹ string. See Section 3.4 for implementation. |
| N9 | **Schema migration on update** — distributing a new `.exe` that expects a column (e.g. `transport_mode`) not in the user's old `billing.db` → instant crash | `db_version` table tracks schema version. On startup, `main.py` compares `APP_SCHEMA_VERSION` vs `MAX(db_version.version)` and runs incremental `ALTER TABLE` scripts automatically before UI loads. See Section 2.10.1 for implementation. |

---

## 8. OPTIMIZED WORKFLOW

### 8.1 Invoice Creation Workflow
```
START
  │
  ├─→ User clicks "New Document"
  │     │
  │     ├─→ Select doc type (Tax Invoice / Quotation / PI / DC / PO)
  │     │     │
  │     │     └─→ Auto-generate document number (2026IN0004)
  │     │         Auto-fill today's date
  │     │         Auto-fill seller details from company_profile
  │     │         Load T&C for this doc type
  │     │
  │     ├─→ Select/Search Customer
  │     │     │
  │     │     ├─→ Found → Auto-fill buyer name, address, GSTIN, PAN, state
  │     │     │            Auto-detect intra/inter-state from GSTIN
  │     │     │
  │     │     └─→ Not found → [+ Add New Customer] dialog
  │     │                       Save → auto-fill buyer fields
  │     │
  │     ├─→ Fill logistics (Vehicle No, GR/LR, PO, etc.) — all optional
  │     │
  │     ├─→ Add Line Items (repeat):
  │     │     │
  │     │     ├─→ Select Category from dropdown (filterable)
  │     │     │     → Auto-fill HSN code from products table
  │     │     │     → Auto-fill GST rate from products table
  │     │     │
  │     │     ├─→ Enter Item Name (description)
  │     │     ├─→ Enter Quantity, Rate, Discount %
  │     │     │
  │     │     └─→ LIVE COMPUTE (instant, read-only display):
  │     │           Taxable = Qty × Rate × (1 - Disc%)
  │     │           If intra-state: CGST = Taxable × 9%, SGST = same
  │     │           If inter-state: IGST = Taxable × 18%
  │     │           Line Total = Taxable + Taxes
  │     │
  │     ├─→ [+ Add Item] — adds new row (no limit)
  │     ├─→ [− Remove] — removes selected row, renumbers
  │     │
  │     ├─→ LIVE FOOTER (updates on every change):
  │     │     Total Taxable, SGST, CGST, IGST, Grand Total
  │     │     Amount in Words (Indian format)
  │     │
  │     ├─→ Auto-save as DRAFT every 30 seconds
  │     │
  │     └─→ User chooses action:
  │           │
  │           ├─→ [Save] → status = 'saved', persists to DB
  │           ├─→ [Export] → status = 'exported', locks editing
  │           ├─→ [PDF] → generates PDF → optional print
  │           │     │
  │           │     ├─→ Select copy types (checkboxes)
  │           │     ├─→ Preview in-app
  │           │     └─→ Save to file / Print
  │           │
  │           └─→ [Cancel] → discard draft (with confirmation)
  │
END
```

### 8.2 Invoice Edit/Regenerate Workflow
```
START
  │
  ├─→ User goes to "Documents" list
  ├─→ Search/Filter by number, customer, date, type, status
  ├─→ Select document → Click [Edit] or [View]
  │     │
  │     ├─→ IF status = 'draft' or 'saved':
  │     │     → Open in Document Editor (fully editable)
  │     │     → Make changes → [Save] / [PDF]
  │     │
  │     ├─→ IF status = 'exported':
  │     │     → Warning: "This document has been exported. Edit anyway?"
  │     │     → If yes → set status back to 'saved', allow editing
  │     │     → If no → view-only mode
  │     │
  │     └─→ [Duplicate] → Creates new document with same data,
  │                        new number, today's date, status = 'draft'
  │
END
```

### 8.3 GSTR-1 Workflow
```
START
  │
  ├─→ User goes to "GSTR-1" page
  ├─→ GSTIN + Business name pre-filled from company_profile
  ├─→ Select date range (From / To)
  ├─→ Click [Generate]
  │     │
  │     ├─→ Query all Tax Invoices (type='IN') in date range
  │     ├─→ Classify: B2B vs B2C, Large vs Small, by GSTIN, by rate
  │     ├─→ Show preview summary:
  │     │     - Invoice count, B2B count, B2C count
  │     │     - Total taxable, CGST, SGST, IGST
  │     │
  │     └─→ [Export to Excel] → generates 14-sheet .xlsx
  │           → Save dialog → file saved
  │
END
```

### 8.4 Daily Workflow (Typical User Day)
```
1. Open app → Dashboard shows today's stats, pending items
2. Create 2-3 new invoices → auto-save protects work
3. Generate PDFs → email/print for customers
4. Add a new customer mid-invoice → quick dialog, no page switch
5. End of month → generate GSTR-1 → export Excel → upload to GST portal
6. Close app → auto-backup prompt if >24h since last backup
```

---

## 9. CUSTOMIZATION & DISTRIBUTION ENGINE

> **Design Principle:** Every piece of company-specific data, every field label, every toggle, and every layout choice is stored in the database and exposed through the Settings UI. The codebase contains **zero hardcoded company information**. A fresh install is a blank canvas — the First-Run Wizard (Section 4.11) or Settings page (Section 4.10) configures everything.

### 9.1 Generalization Strategy

| Layer | What's Customizable | Where Configured | Stored In |
|---|---|---|---|
| **Identity** | Company name, address, GSTIN, PAN, CIN, logo, stamp, signature label | First-Run Wizard / Settings → Company Profile | `company_profile` |
| **Banking** | Bank name, branch, account, IFSC; show/hide on PDF | Settings → Bank Details | `company_profile` |
| **Document Types** | Which types are active (IN/QT/PI/DC/PO); custom types; display names | Settings → Document Types | `doc_type_config` |
| **Numbering** | Format pattern ({YYYY}{PREFIX}{NNNN}), digit padding, custom prefixes | Settings → Document Types → Edit | `doc_type_config` |
| **Tax** | Per-product GST rates (not hardcoded 18%); composition scheme support (future) | Product Manager → GST Rate column | `products.gst_rate` |
| **T&C** | Per document type; enable/disable; full text editor | Settings → Terms & Conditions | `terms_conditions` |
| **PDF Layout** | Logo position/size, field visibility, column toggles, copy type labels, font, footer note, header color | Settings → Invoice Layout | `pdf_template_settings` |
| **Theme** | Light/Dark/System mode, accent color, sidebar style | Settings → Theme | `app_settings` |
| **Currency** | Currency symbol (₹, $, €, etc.) | Settings → Company Profile | `company_profile.currency_symbol` |
| **Financial Year** | Start month (April for India, Jan for others) | Settings → Company Profile | `company_profile.financial_year_start` |
| **Data** | Import from Excel/CSV, export to Excel, backup/restore DB | Settings → Data & Backup | File system + `app_settings` |

### 9.2 Field Visibility Engine

The `pdf_template_settings` table drives what appears on both the **Document Editor UI** and the **generated PDF**. When a field is toggled off:

```
Settings → Invoice Layout → uncheck "Vehicle Number"
    │
    ├─→ Document Editor: Vehicle No field is HIDDEN (not just disabled)
    │     → More screen space for other fields
    │     → documents.vehicle_no is NULL for new documents
    │
    └─→ PDF Output: Vehicle No row is OMITTED
          → Layout auto-adjusts (no blank space)
```

**Fields controlled by visibility toggles:**

| Field | Default | Typical Users Who Disable |
|---|---|---|
| Vehicle Number | ON | Service companies, consultants |
| GR/LR Number | ON | Non-manufacturing, service sector |
| PO No & Date | ON | Retail, B2C-only businesses |
| Vendor Code | ON | Small shops, non-B2B |
| DSR Number | ON | Most businesses (MKRD-specific field) |
| Supply Date | ON | Simple retail |
| Place of Supply | ON | Single-state businesses |
| CIN | ON | Proprietorships, partnerships (no CIN) |
| Website | ON | Businesses without websites |
| Discount Column | ON | Fixed-price businesses |
| HSN/SAC Column | ON | Businesses below HSN threshold (turnover < ₹5Cr) |
| Bank Details on PDF | ON | Cash-only businesses |

### 9.3 Document Type Extensibility

The 5 default doc types (IN, QT, PI, DC, PO) cover most manufacturing businesses. Other businesses may need:

| Business Type | Custom Types They Might Add |
|---|---|
| Retail shop | **Bill of Supply** (for composition scheme) |
| Service firm | **Work Order (WO)**, **Service Report (SR)** |
| Exporter | **Export Invoice (EI)**, **Packing List (PL)** |
| Construction | **Running Account Bill (RA)** |
| Trader | **Credit Note (CN)**, **Debit Note (DN)** |

**How it works:**
1. User goes to Settings → Document Types → [+ Add Custom Type]
2. Enters: Code (2-3 chars), Display Name, Prefix for numbering
3. Chooses: Is it a GST document? (affects GSTR-1 inclusion)
4. The new type appears in the Document Editor dropdown immediately
5. T&C can be configured for the new type in Settings → T&C tab

### 9.4 Invoice Number Format Customization

Different businesses use different numbering conventions:

| Business | Preferred Format | Template |
|---|---|---|
| MKRD Engineers | 2026IN0001 | `{YYYY}{PREFIX}{N4}` |
| Small retailer | INV-001 | `{PREFIX}-{N3}` |
| Multi-branch | MUM-2026-IN-0001 | `{COMPANY}-{YYYY}-{PREFIX}-{N4}` |
| Financial-year | FY26-QT-0015 | `FY{YY}-{PREFIX}-{N4}` |
| Monthly reset | 2026-01-IN-001 | `{YYYY}-{MM}-{PREFIX}-{N3}` |

The `doc_type_config.number_format` field stores the template. The `number_generator.py` service parses tokens and constructs the number. Padding is controlled by `padding_digits`.

### 9.5 Copy Type Label Customization

Default labels (from GST rules):
1. Original for Recipient
2. Duplicate for Transporter
3. Triplicate for Supplier
4. Extra Copy

Businesses can:
- **Rename** labels (e.g., "Office Copy" instead of "Extra Copy")
- **Add** new labels (up to 6 total)
- **Remove** labels they don't use (e.g., transporter copy for service firms)
- **Reorder** labels

Stored as JSON array in `pdf_template_settings.copy_types_json`.

### 9.6 Data Import / Export for New Business Onboarding

When distributing to a new business, they may have existing data in Excel:

**Import Wizard (Settings → Data & Backup → Import):**
```
┌───────────────────────────────────────────────────────┐
│  IMPORT DATA                                    [✕]  │
├───────────────────────────────────────────────────────┤
│                                                       │
│  Source: (● Excel .xlsx/.xlsm)  (○ CSV)  (○ Backup) │
│  File:   [📁 Choose...]                              │
│                                                       │
│  What to import:                                      │
│  [✓] Customers                                        │
│  [✓] Products / Services                              │
│  [ ] Previous Invoices                                │
│  [ ] Purchases                                        │
│                                                       │
│  ┌─ COLUMN MAPPING ─────────────────────────────┐    │
│  │ Excel Column    →    App Field               │    │
│  │ ─────────────────────────────────────────     │    │
│  │ Column A (Name) →    [Customer Name ▼]       │    │
│  │ Column B (GSTIN)→    [GSTIN ▼]               │    │
│  │ Column C (Addr) →    [Address Line 1 ▼]      │    │
│  │ Column D (State)→    [State ▼]               │    │
│  │ ...                                           │    │
│  └───────────────────────────────────────────────┘    │
│                                                       │
│  Preview: 52 customers found, 0 duplicates            │
│                                                       │
│  [Cancel]  [Import]                                   │
└───────────────────────────────────────────────────────┘
```

**Export:** Full database export to Excel (one sheet per table) or SQLite backup copy.

### 9.7 Multi-Business Distribution Checklist

When deploying to a new business:

| # | Step | How |
|---|---|---|
| 1 | Install app | Single executable (PyInstaller bundle) |
| 2 | First launch | First-Run Wizard opens automatically |
| 3 | Enter business details | Wizard Step 1: Name, GSTIN, PAN, Address |
| 4 | Bank details | Wizard Step 2: Bank info |
| 5 | Upload branding | Wizard Step 3: Logo + Stamp |
| 6 | Configure preferences | Wizard Step 4: GST rate, doc types, theme |
| 7 | Import existing data | Settings → Import from Excel (optional) |
| 8 | Customize PDF layout | Settings → Invoice Layout (hide unused fields) |
| 9 | Set T&C | Settings → Terms & Conditions (per doc type) |
| 10 | Create first invoice | Ready to go! |

**Time to operational:** < 10 minutes for a basic setup, < 30 minutes for full customization.

---

## 10. PHASE PLAN

### Phase 1: Foundation (Backend + Database)
**Goal:** All data models, database, repositories, and core business logic — fully testable without UI.

| Task | Description |
|---|---|
| 1.1 | Project scaffolding (directory structure, requirements.txt) |
| 1.2 | `config.py` — paths, constants (zero hardcoded company data) |
| 1.3 | `database/connection.py` — SQLite singleton with WAL mode |
| 1.4 | `database/migrations.py` — all CREATE TABLE statements (including `pdf_template_settings`, `doc_type_config`) |
| 1.5 | `database/seed_data.py` — state_master (39 states), default doc_type_config (5 types), default pdf_template_settings, purchase categories |
| 1.6 | All `models/` dataclasses |
| 1.7 | All `repositories/` CRUD classes |
| 1.8 | `services/gst_engine.py` — tax calculation |
| 1.9 | `services/number_generator.py` — document numbering (format-aware, reads `doc_type_config`) |
| 1.10 | `services/num_to_words.py` — Indian number words |
| 1.11 | `services/calculator.py` — line item + totals |
| 1.12 | `services/validator.py` — all input validation |
| 1.13 | `services/customization_engine.py` — field visibility resolver, template settings loader |
| 1.14 | Data migration script (read xlsm → populate SQLite) |
| 1.15 | Unit tests for all services |

### Phase 2: UI Shell + Document Editor + First-Run Wizard
**Goal:** Working PyQt6 app with onboarding and the most critical page: document creation/editing.

| Task | Description |
|---|---|
| 2.1 | `main.py` + `main_window.py` — QMainWindow with sidebar |
| 2.2 | `ui/styles.py` — QSS theme (light/dark support) |
| 2.3 | Sidebar navigation (all pages as placeholders) |
| 2.4 | `ui/wizards/first_run_wizard.py` — 4-step onboarding wizard |
| 2.5 | First-run detection: if `company_profile.is_setup_complete = 0` → show wizard |
| 2.6 | `ui/widgets/item_grid.py` — dynamic line item table |
| 2.7 | `ui/widgets/` — all reusable widgets (search, date, currency) |
| 2.8 | `ui/pages/document_editor.py` — full editor with field visibility support |
| 2.9 | `ui/dialogs/customer_picker.py` — search & select customer |
| 2.10 | `ui/dialogs/product_picker.py` — category selector |
| 2.11 | Wire editor to backend (save/load documents) |
| 2.12 | Live calculation in editor |

### Phase 3: Full CRUD + PDF + Purchase Tracker
**Goal:** All remaining CRUD pages + customization-aware PDF generation.

| Task | Description |
|---|---|
| 3.1 | `ui/pages/document_list.py` — list, search, filter, paginate |
| 3.2 | `ui/pages/customer_manager.py` — full CRUD |
| 3.3 | `ui/pages/product_manager.py` — full CRUD with per-product GST rates |
| 3.4 | `ui/pages/purchase_tracker.py` — expense register with categories, vendor auto-suggest, summary |
| 3.5 | `ui/pages/settings_page.py` — ALL 7 tabs (Company, Bank, T&C, Doc Types, Invoice Layout, Theme, Data & Backup, About) |
| 3.6 | `services/pdf_controller.py` — ReportLab A4 invoice PDF (reads `pdf_template_settings` for layout) |
| 3.7 | `ui/dialogs/print_preview.py` — in-app PDF preview |
| 3.8 | Multi-page pagination (10 items/page) |
| 3.9 | Copy type selection (from `pdf_template_settings.copy_types_json`) |
| 3.10 | Field visibility: hide toggled-off fields in editor + PDF |
| 3.11 | Doc type management: add/edit/disable types in Settings |

### Phase 4: GSTR-1 + Reports + Import/Export + Polish
**Goal:** GSTR-1 engine, dashboard, full reports, data import/export, final polish.

| Task | Description |
|---|---|
| 4.1 | `services/gstr1_generator.py` — full 14-sheet Excel export |
| 4.2 | `ui/pages/gstr1_page.py` — GSTR-1 generation UI |
| 4.3 | `ui/pages/dashboard.py` — stats, charts, recent docs |
| 4.4 | `ui/pages/reports_page.py` — 9 report types (Revenue, Sales by Customer/Product, Tax, Purchase, Expense vs Revenue, Outstanding, Doc Count, HSN) with charts + export |
| 4.5 | `services/backup_manager.py` — backup/restore |
| 4.6 | `services/data_import_export.py` — import from Excel/CSV, column mapping wizard |
| 4.7 | `ui/dialogs/import_data_dialog.py` — import wizard UI |
| 4.8 | Data migration tool (import from xlsm — MKRD-specific legacy migration) |
| 4.9 | Single-instance lock |
| 4.10 | Auto-save drafts |
| 4.11 | PyInstaller packaging for distribution |
| 4.12 | Final QA, edge case testing, multi-business scenario testing |

---

## APPENDIX A: Technology Choices Rationale

| Choice | Why | Alternatives Considered |
|---|---|---|
| **PyQt6** | Most mature Python GUI framework; native look; complex layouts; good table/grid widgets | Tkinter (too basic), PySide6 (same Qt, LGPL), CustomTkinter (no table widget) |
| **SQLite** | Zero-config, single-file DB, ACID compliant, handles 100K+ rows easily, portable per business | PostgreSQL (overkill for single-user), JSON files (no queries) |
| **ReportLab** | Full control over PDF layout, pixel-perfect positioning, reads layout settings from DB | WeasyPrint (HTML→PDF, less control), FPDF (less capable), LibreOffice (fragile) |
| **openpyxl** | GSTR-1 needs multi-sheet Excel output with formatting; also used for data import | xlsxwriter (can't read), pandas (less format control) |
| **PyInstaller** | Single-file distribution, no Python install required on target machines | cx_Freeze (less maintained), Nuitka (slower build) |

## APPENDIX B: Seed Data Summary

> **IMPORTANT:** No company-specific data is seeded. All company data is entered via First-Run Wizard.

- **State Master:** 39 entries (01-Jammu & Kashmir through 99-Centre Jurisdiction)
- **Doc Type Config:** 5 default types (IN, QT, PI, DC, PO) with standard format `{YYYY}{PREFIX}{N4}`
- **PDF Template Settings:** 1 row with all defaults (all fields ON, Helvetica, 8pt)
- **Purchase Categories:** 8 defaults (Raw Material, Tooling, Utility, Rent, Maintenance, Transport, Salary, Miscellaneous)
- **Company Profile:** 1 row, all fields blank, `is_setup_complete = 0`
- **T&C:** 5 empty entries (one per default doc type — user fills in Settings)

### For MKRD Migration Only (Phase 4, Task 4.8):
- **Products:** 17 categories with HSN codes (migrated from xlsm)
- **Customers:** 52 records (migrated from xlsm)
- **Existing Documents:** 3 tax invoices + 8 quotations (migrated from xlsm)
- **Company Profile:** Populated from xlsm data
- **T&C:** Populated from T&C sheet

## APPENDIX C: Customization Quick-Reference Matrix

| What | Where in UI | DB Table | PDF Impact |
|---|---|---|---|
| Company name/address | Settings → Company Profile | `company_profile` | Header zone |
| Logo | Settings → Company Profile | `company_profile.logo_path` | Top-left (or center/right) |
| Stamp/Seal | Settings → Company Profile | `company_profile.stamp_path` | Signature zone |
| Bank details | Settings → Bank Details | `company_profile` | Footer zone (toggle) |
| GSTIN/PAN/CIN | Settings → Company Profile | `company_profile` | Header zone (CIN toggle) |
| T&C per doc type | Settings → Terms & Conditions | `terms_conditions` | Last page footer |
| Invoice number format | Settings → Document Types → Edit | `doc_type_config` | Title zone |
| Copy type labels | Settings → Invoice Layout → Copy Types | `pdf_template_settings` | Top-right label |
| Field visibility | Settings → Invoice Layout | `pdf_template_settings` | Dynamic show/hide |
| Font & size | Settings → Invoice Layout → Font | `pdf_template_settings` | Entire document |
| Header color | Settings → Invoice Layout → Header | `pdf_template_settings` | Header bar |
| Footer note | Settings → Invoice Layout → Footer | `pdf_template_settings` | Bottom text |
| Currency symbol | Settings → Company Profile | `company_profile` | All amounts |
| GST rate per product | Product Manager → GST Rate | `products.gst_rate` | Tax calculations |
| App theme | Settings → Theme | `app_settings` | UI only (not PDF) |
| Accent color | Settings → Theme | `app_settings` | UI only |

---

*Blueprint v3.0 — Generalized for multi-business distribution. Ready for implementation upon confirmation.*
