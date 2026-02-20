"""
GST Billing Suite — Application-wide constants, paths, and configuration.
Zero hardcoded company data. All business info comes from the database.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
APP_NAME = "GST Billing Suite"
APP_VERSION = "1.0.0"
APP_SCHEMA_VERSION = 1  # Bump when DB schema changes; triggers auto-migration

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "billing.db"
BACKUP_DIR = DATA_DIR / "backups"
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
FONTS_DIR = ASSETS_DIR / "fonts"
LOCK_FILE = DATA_DIR / ".app.lock"

# Ensure critical directories exist
for _dir in (DATA_DIR, BACKUP_DIR, ASSETS_DIR, ICONS_DIR, FONTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_JOURNAL_MODE = "WAL"
DB_FOREIGN_KEYS = True
DB_BUSY_TIMEOUT_MS = 5000

# ---------------------------------------------------------------------------
# PDF Defaults (overridden by pdf_template_settings in DB)
# ---------------------------------------------------------------------------
PDF_PAGE_WIDTH_MM = 210   # A4
PDF_PAGE_HEIGHT_MM = 297
PDF_ITEMS_PER_PAGE = 10
PDF_DEFAULT_FONT = "Helvetica"
PDF_DEFAULT_FONT_SIZE = 8

# ---------------------------------------------------------------------------
# UI Defaults (overridden by app_settings in DB)
# ---------------------------------------------------------------------------
MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 700
AUTOSAVE_INTERVAL_MS = 30_000  # 30 seconds

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
GSTIN_LENGTH = 15
PAN_LENGTH = 10
MAX_COPY_TYPES = 6
MAX_LINE_ITEMS = 500  # Safety cap

# ---------------------------------------------------------------------------
# Currency / Locale
# ---------------------------------------------------------------------------
DEFAULT_CURRENCY_SYMBOL = "₹"
DEFAULT_GST_RATE = 18.0
DEFAULT_FINANCIAL_YEAR_START = 4  # April
