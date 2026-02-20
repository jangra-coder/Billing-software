"""
Document List Page — browse, search, filter, paginate, export/import documents.

Modern layout with auto-resizing columns, toolbar card, and status badges.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from models.document import Document
from repositories.document_repo import DocumentRepo
from repositories.settings_repo import DocTypeConfigRepo
from services.calculator import format_currency
from services.excel_io import export_to_excel, import_from_excel
from ui.widgets.search_bar import SearchBar


# Status colours for badge rendering
_STATUS_COLORS = {
    "draft":     ("#FFF3E0", "#E65100"),
    "saved":     ("#E8F5E9", "#2E7D32"),
    "exported":  ("#E3F2FD", "#1565C0"),
    "cancelled": ("#FFEBEE", "#C62828"),
}


class DocumentListPage(QWidget):
    """Browse and manage all documents."""

    open_document = pyqtSignal(int)       # doc id → edit
    duplicate_document = pyqtSignal(int)  # doc id → duplicate

    PAGE_SIZE = 50

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self._doc_repo = DocumentRepo(conn)
        self._dtc = DocTypeConfigRepo(conn)
        self._current_page = 0
        self._total_count = 0
        self._build_ui()
        self.refresh()

    # ==================================================================
    # Build UI
    # ==================================================================
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(8)

        # ── Header row
        hdr = QHBoxLayout()
        title = QLabel("Documents")
        title.setObjectName("heading")
        hdr.addWidget(title)

        self._lbl_count = QLabel("")
        self._lbl_count.setObjectName("subheading")
        hdr.addWidget(self._lbl_count)
        hdr.addStretch()

        btn_new = QPushButton("＋  New Document")
        btn_new.clicked.connect(lambda: self.open_document.emit(-1))
        hdr.addWidget(btn_new)
        layout.addLayout(hdr)

        # ── Toolbar card (filters + actions)
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 6, 8, 6)

        tl.addWidget(QLabel("Type:"))
        self._cmb_type = QComboBox()
        self._cmb_type.setMinimumWidth(130)
        self._cmb_type.addItem("All Types", "")
        for dt in self._dtc.list_all():
            self._cmb_type.addItem(dt["display_name"], dt["code"])
        self._cmb_type.currentIndexChanged.connect(lambda: self._apply_filters())
        tl.addWidget(self._cmb_type)

        tl.addWidget(QLabel("Status:"))
        self._cmb_status = QComboBox()
        self._cmb_status.setMinimumWidth(110)
        for label, val in [("All Status", ""), ("Draft", "draft"), ("Saved", "saved"),
                           ("Exported", "exported"), ("Cancelled", "cancelled")]:
            self._cmb_status.addItem(label, val)
        self._cmb_status.currentIndexChanged.connect(lambda: self._apply_filters())
        tl.addWidget(self._cmb_status)

        tl.addSpacing(12)
        self._search = SearchBar("Search doc #, customer…")
        self._search.setMinimumWidth(200)
        self._search.search_changed.connect(lambda _: self._apply_filters())
        tl.addWidget(self._search, 1)

        tl.addSpacing(12)
        btn_export = QPushButton("📤 Export")
        btn_export.setProperty("secondary", True)
        btn_export.clicked.connect(self._export_excel)
        tl.addWidget(btn_export)

        btn_import = QPushButton("📥 Import")
        btn_import.setProperty("secondary", True)
        btn_import.clicked.connect(self._import_excel)
        tl.addWidget(btn_import)

        btn_sample = QPushButton("📋 Sample")
        btn_sample.setProperty("secondary", True)
        btn_sample.setToolTip("Export a sample import file")
        btn_sample.clicked.connect(self._export_sample)
        tl.addWidget(btn_sample)

        layout.addWidget(toolbar)

        # ── Table — auto-stretch columns
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "Document #", "Date", "Customer", "Items", "Amount (₹)", "Type", "Status", "ID",
        ])
        self._table.setColumnHidden(7, True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setMinimumSectionSize(60)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(38)
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table, 1)

        # ── Footer: actions + pagination
        foot = QHBoxLayout()
        self._btn_edit = QPushButton("✏️  Edit")
        self._btn_edit.clicked.connect(self._edit_selected)
        foot.addWidget(self._btn_edit)

        self._btn_dup = QPushButton("📋  Duplicate")
        self._btn_dup.setProperty("secondary", True)
        self._btn_dup.clicked.connect(self._duplicate_selected)
        foot.addWidget(self._btn_dup)

        self._btn_del = QPushButton("🗑  Delete")
        self._btn_del.setProperty("danger", True)
        self._btn_del.clicked.connect(self._delete_selected)
        foot.addWidget(self._btn_del)

        foot.addStretch()

        self._btn_prev = QPushButton("◀ Prev")
        self._btn_prev.setProperty("secondary", True)
        self._btn_prev.clicked.connect(self._prev_page)
        foot.addWidget(self._btn_prev)

        self._lbl_page = QLabel("Page 1 of 1")
        self._lbl_page.setStyleSheet("padding: 0 8px;")
        foot.addWidget(self._lbl_page)

        self._btn_next = QPushButton("Next ▶")
        self._btn_next.setProperty("secondary", True)
        self._btn_next.clicked.connect(self._next_page)
        foot.addWidget(self._btn_next)

        layout.addLayout(foot)

    # ==================================================================
    # Data
    # ==================================================================
    def refresh(self) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        self._current_page = 0
        self._load_data()

    def _load_data(self) -> None:
        doc_type = self._cmb_type.currentData() or None
        status = self._cmb_status.currentData() or None
        search = self._search.text().strip() or None

        offset = self._current_page * self.PAGE_SIZE
        docs = self._doc_repo.list_filtered(
            doc_type=doc_type, status=status, search=search,
            limit=self.PAGE_SIZE, offset=offset,
        )
        self._total_count = self._doc_repo.count_filtered(
            doc_type=doc_type, status=status,
        )

        self._lbl_count.setText(f"  ({self._total_count} records)")

        self._table.setRowCount(0)
        for doc in docs:
            row = self._table.rowCount()
            self._table.insertRow(row)

            self._table.setItem(row, 0, QTableWidgetItem(f"  {doc.document_number}"))
            self._table.setItem(row, 1, QTableWidgetItem(f"  {_format_date(doc.document_date)}"))
            self._table.setItem(row, 2, QTableWidgetItem(f"  {doc.customer_name or '(Walk-in)'}"))

            # Items count (from doc.items list if loaded, else '—')
            item_count = len(doc.items) if hasattr(doc, 'items') and doc.items else 0
            items_cell = QTableWidgetItem(str(item_count) if item_count else "—")
            items_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 3, items_cell)

            amt = QTableWidgetItem(f"{format_currency(doc.grand_total)}  ")
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 4, amt)

            self._table.setItem(row, 5, QTableWidgetItem(f"  {doc.document_type}"))

            # Styled status cell
            st = doc.status
            st_item = QTableWidgetItem(f"  {st.title()}")
            bg, fg = _STATUS_COLORS.get(st, ("#F5F5F5", "#424242"))
            st_item.setBackground(QColor(bg))
            st_item.setForeground(QColor(fg))
            self._table.setItem(row, 6, st_item)

            self._table.setItem(row, 7, QTableWidgetItem(str(doc.id)))

        total_pages = max(1, (self._total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._lbl_page.setText(f"Page {self._current_page + 1} of {total_pages}")
        self._btn_prev.setEnabled(self._current_page > 0)
        self._btn_next.setEnabled((self._current_page + 1) < total_pages)

    def _prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._load_data()

    def _next_page(self) -> None:
        self._current_page += 1
        self._load_data()

    # ==================================================================
    # Actions
    # ==================================================================
    def _selected_doc_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 7)
        return int(item.text()) if item else None

    def _on_double_click(self) -> None:
        doc_id = self._selected_doc_id()
        if doc_id is not None:
            self.open_document.emit(doc_id)

    def _edit_selected(self) -> None:
        doc_id = self._selected_doc_id()
        if doc_id is None:
            QMessageBox.information(self, "Select", "Select a document first.")
            return
        self.open_document.emit(doc_id)

    def _duplicate_selected(self) -> None:
        doc_id = self._selected_doc_id()
        if doc_id is None:
            QMessageBox.information(self, "Select", "Select a document first.")
            return
        self.duplicate_document.emit(doc_id)

    def _delete_selected(self) -> None:
        doc_id = self._selected_doc_id()
        if doc_id is None:
            QMessageBox.information(self, "Select", "Select a document first.")
            return
        reply = QMessageBox.warning(
            self, "Delete Document",
            f"Permanently delete document #{doc_id}?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._doc_repo.delete(doc_id)
            self.refresh()

    # ==================================================================
    # Excel Export / Import
    # ==================================================================
    def _export_sample(self) -> None:
        """Export a sample import file with correct headers."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Sample Import File", "document_import_sample.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        sample = [{
            "document_number": "INV-0001",
            "document_type": "INVOICE",
            "document_date": "2025-01-01",
            "customer_name": "Example Customer",
            "customer_gstin": "06AAACB1234F1Z5",
            "total_taxable": 10000,
            "total_cgst": 900,
            "total_sgst": 900,
            "total_igst": 0,
            "grand_total": 11800,
            "status": "saved",
            "remarks": "",
        }]
        export_to_excel(
            sample, path,
            sheet_name="Documents",
            title="Document Import Sample",
            money_columns=("total_taxable", "total_cgst", "total_sgst",
                           "total_igst", "grand_total"),
        )
        QMessageBox.information(
            self, "Sample Exported",
            f"Sample import file saved to:\n{path}",
        )

    def _export_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Documents to Excel", "documents.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        # Fetch all matching current filter
        doc_type = self._cmb_type.currentData() or None
        status = self._cmb_status.currentData() or None
        search = self._search.text().strip() or None
        docs = self._doc_repo.list_filtered(
            doc_type=doc_type, status=status, search=search,
            limit=99999, offset=0,
        )
        rows = []
        for d in docs:
            rows.append({
                "document_number": d.document_number,
                "document_type": d.document_type,
                "document_date": d.document_date,
                "customer_name": d.customer_name,
                "customer_gstin": d.customer_gstin,
                "total_taxable": d.total_taxable,
                "total_cgst": d.total_cgst,
                "total_sgst": d.total_sgst,
                "total_igst": d.total_igst,
                "grand_total": d.grand_total,
                "status": d.status,
                "remarks": d.remarks,
            })
        export_to_excel(
            rows, path,
            sheet_name="Documents",
            title="Document Register",
            money_columns=("total_taxable", "total_cgst", "total_sgst",
                           "total_igst", "grand_total"),
        )
        QMessageBox.information(self, "Exported", f"Exported {len(rows)} documents to:\n{path}")

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Documents from Excel", "",
            "Excel Files (*.xlsx *.xlsm)",
        )
        if not path:
            return
        try:
            raw_headers, rows = import_from_excel(path)
            if not rows:
                QMessageBox.warning(self, "Empty", "No data rows found in the file.")
                return
            QMessageBox.information(
                self, "Import Preview",
                f"Found {len(rows)} rows with columns:\n{', '.join(raw_headers[:8])}…\n\n"
                "Full import with column mapping will be available in Phase 4.\n"
                "For now, use Settings → Data & Backup → Import.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))


# ── helpers ────────────────────────────────────────────────────────
def _format_date(iso: str) -> str:
    """YYYY-MM-DD → DD-MMM-YYYY."""
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return dt.strftime("%d-%b-%Y")
    except Exception:
        return iso
