#!/usr/bin/env python3
"""
GST Billing Suite — Application entry point.

Boot sequence:
  1. Create QApplication
  2. Ensure database exists (migrations + seed data)
  3. Apply stylesheet
  4. Launch MainWindow
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from config import APP_NAME
from database.connection import get_db
from database.migrations import initialise_database
from database.seed_data import seed_all
from ui.main_window import MainWindow
from ui.styles import get_stylesheet


def main() -> int:
    """Application main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # ── Database bootstrap ────────────────────────────────────────
    conn = get_db()
    initialise_database(conn)
    seed_all(conn)

    # ── Theming ───────────────────────────────────────────────────
    # Read user's preference from DB, fallback to light
    theme = "light"
    accent = "#1565C0"
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'theme'"
        ).fetchone()
        if row and row[0] in ("light", "dark"):
            theme = row[0]
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'accent_color'"
        ).fetchone()
        if row and row[0]:
            accent = row[0]
    except Exception:
        pass

    app.setStyleSheet(get_stylesheet(theme, accent))

    # ── Main window ───────────────────────────────────────────────
    window = MainWindow(conn)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
