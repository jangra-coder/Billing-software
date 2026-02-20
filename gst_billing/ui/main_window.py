"""
Main Window — sidebar navigation + page stack + first-run detection.

Responsibilities:
  • Shows FirstRunWizard on first launch (is_setup_complete == 0)
  • Houses the sidebar and a QStackedWidget of all pages
  • Routes sidebar.page_requested signals to the correct page
"""

from __future__ import annotations

import sqlite3

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QMainWindow, QStackedWidget, QStatusBar, QWidget,
)

from repositories.company_repo import CompanyRepo

from ui.pages.document_editor import DocumentEditor
from ui.pages.document_list import DocumentListPage
from ui.pages.customer_manager import CustomerManagerPage
from ui.pages.product_manager import ProductManagerPage
from ui.pages.purchase_tracker import PurchaseTrackerPage
from ui.pages.placeholder_pages import (
    DashboardPage,
    Gstr1Page,
    ReportsPage,
)
from ui.pages.settings_page import SettingsPage
from ui.widgets.sidebar import Sidebar
from ui.wizards.first_run_wizard import FirstRunWizard


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        super().__init__()
        self.conn = conn

        self.setWindowTitle("GST Billing Suite")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.page_requested.connect(self._navigate_to)
        main_layout.addWidget(self._sidebar)

        # Page stack
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack, 1)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

        # Build pages
        self._pages: dict[str, QWidget] = {}
        self._build_pages()

        # Navigate to default
        self._sidebar.set_active("dashboard")
        self._navigate_to("dashboard")

        # First-run check (deferred so the window appears first)
        QTimer.singleShot(200, self._check_first_run)

    # ------------------------------------------------------------------
    # Build pages
    # ------------------------------------------------------------------
    def _build_pages(self) -> None:
        """Register all pages in the stack."""
        self._register("dashboard", DashboardPage())

        editor = DocumentEditor(self.conn)
        self._register("new_doc", editor)

        doc_list = DocumentListPage(self.conn)
        doc_list.open_document.connect(self._open_or_new_doc)
        doc_list.duplicate_document.connect(self._duplicate_doc)
        self._register("documents", doc_list)

        # Connect editor → refresh doc list after save
        editor.document_saved.connect(lambda _id: doc_list.refresh())

        self._register("customers", CustomerManagerPage(self.conn))
        self._register("products", ProductManagerPage(self.conn))
        self._register("purchases", PurchaseTrackerPage(self.conn))
        self._register("gstr1", Gstr1Page())
        self._register("reports", ReportsPage())

        settings_page = SettingsPage(conn=self.conn)
        settings_page.reset_requested.connect(self._on_factory_reset)
        self._register("settings", settings_page)

    def _register(self, page_id: str, widget: QWidget) -> None:
        self._pages[page_id] = widget
        self._stack.addWidget(widget)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _navigate_to(self, page_id: str) -> None:
        widget = self._pages.get(page_id)
        if widget is None:
            self._status.showMessage(f"Page '{page_id}' not implemented yet.", 3000)
            return

        # Don't reset "new_doc" editor on navigation — preserve form state.
        # User can explicitly click the 🧹 Clear button to reset.

        # Refresh data pages when navigating to them
        if page_id == "documents" and isinstance(widget, DocumentListPage):
            widget.refresh()
        elif page_id == "customers" and isinstance(widget, CustomerManagerPage):
            widget.refresh()
        elif page_id == "products" and isinstance(widget, ProductManagerPage):
            widget.refresh()
        elif page_id == "purchases" and isinstance(widget, PurchaseTrackerPage):
            widget.refresh()

        self._stack.setCurrentWidget(widget)
        self._sidebar.set_active(page_id)
        self._status.showMessage(f"{page_id.replace('_', ' ').title()}", 2000)

    # ------------------------------------------------------------------
    # First-run wizard
    # ------------------------------------------------------------------
    def _check_first_run(self) -> None:
        profile = CompanyRepo(self.conn).get()
        if not profile.is_setup_complete:
            self._show_wizard()

    def _show_wizard(self) -> None:
        wizard = FirstRunWizard(self.conn, self)
        wizard.setup_complete.connect(self._on_setup_complete)
        wizard.exec()

    def _on_setup_complete(self) -> None:
        """Refresh company data in the document editor after wizard finishes."""
        self._status.showMessage("Setup complete! Welcome.", 4000)
        # Rebuild the editor page so it picks up new company data
        old_editor = self._pages.get("new_doc")
        if old_editor:
            self._stack.removeWidget(old_editor)
            old_editor.deleteLater()

        new_editor = DocumentEditor(self.conn)
        self._pages["new_doc"] = new_editor
        self._stack.addWidget(new_editor)

    # ------------------------------------------------------------------
    # Factory reset
    # ------------------------------------------------------------------
    def _on_factory_reset(self) -> None:
        """Tear down all pages, rebuild them, and show the wizard."""
        # Remove every page from the stack
        for page_id, widget in list(self._pages.items()):
            self._stack.removeWidget(widget)
            widget.deleteLater()
        self._pages.clear()

        # Rebuild fresh pages (picks up clean DB state)
        self._build_pages()
        self._navigate_to("dashboard")

        # Show the wizard again (is_setup_complete is now 0)
        self._show_wizard()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def open_document_for_edit(self, doc_id: int) -> None:
        """Navigate to the editor and load a document."""
        editor = self._pages.get("new_doc")
        if isinstance(editor, DocumentEditor):
            editor.load_for_edit(doc_id)
            self._navigate_to("new_doc")

    def _open_or_new_doc(self, doc_id: int) -> None:
        """Signal handler: open existing doc or create new."""
        if doc_id <= 0:
            self._navigate_to("new_doc")
        else:
            self.open_document_for_edit(doc_id)

    def _duplicate_doc(self, doc_id: int) -> None:
        """Load a document then clear its id so saving creates a copy."""
        editor = self._pages.get("new_doc")
        if isinstance(editor, DocumentEditor):
            editor.load_for_edit(doc_id)
            # Clear the id so it saves as a new document
            editor._doc_id = None
            self._stack.setCurrentWidget(editor)
            self._sidebar.set_active("new_doc")
            self._status.showMessage("Editing duplicate — save to create a new document.", 4000)
