"""
Dynamic line-item table widget.

Provides add/remove rows, category dropdown with search-as-you-type
(QCompleter), QLineEdit for qty/rate/discount for free typing,
and emits signals whenever data changes so the editor can
recompute totals in real time.

Columns (12):
  S.No | Category | Item Name | HSN | Qty | Rate | Disc % |
  Taxable | CGST | SGST | IGST | Total

GST columns show the amount; the rate % is shown as a tooltip
on each GST cell and dynamically in the column header.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QHBoxLayout,
    QHeaderView, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from models.product import Product


class ItemGrid(QWidget):
    """Table of line items with live-editing."""

    items_changed = pyqtSignal()  # emitted whenever any value changes

    # Column indices  (no separate GST rate% columns)
    COL_SN       = 0
    COL_CATEGORY = 1
    COL_ITEM     = 2
    COL_HSN      = 3
    COL_QTY      = 4
    COL_RATE     = 5
    COL_DISC     = 6
    COL_TAXABLE  = 7
    COL_CGST     = 8
    COL_SGST     = 9
    COL_IGST     = 10
    COL_TOTAL    = 11

    HEADERS = [
        "S.No", "Category", "Item Name", "HSN", "Qty", "Rate",
        "Disc %", "Taxable", "CGST", "SGST", "IGST", "Total",
    ]

    # Layout constants
    _MAX_VISIBLE_ROWS = 15
    _ROW_HEIGHT = 38
    _HEADER_HEIGHT = 32

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._products: list[Product] = []
        self._category_names: list[str] = []
        self._show_discount = True
        self._show_hsn = True
        self._is_intra_state: bool = True  # default intra (Haryana)
        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )

        # ── Improved column widths (wider Rate, HSN, GST) ──
        widths = [38, 190, 170, 100, 70, 115, 65, 108, 98, 98, 98, 118]
        for i, w in enumerate(widths):
            self.table.setColumnWidth(i, w)
        self.table.verticalHeader().setDefaultSectionSize(self._ROW_HEIGHT)

        # Enable word-wrap for item name column
        self.table.setWordWrap(True)

        # Ensure headers are fully visible
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(38)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )

        # All GST columns (CGST, SGST, IGST) are always visible.
        # Unused columns will show 0.00 values based on supply type.

        layout.addWidget(self.table, 1)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Add Item")
        self.btn_add.clicked.connect(self.add_row)
        btn_row.addWidget(self.btn_add)

        self.btn_remove = QPushButton("\u2212 Remove Last")
        self.btn_remove.setProperty("flat", True)
        self.btn_remove.clicked.connect(self.remove_last_row)
        btn_row.addWidget(self.btn_remove)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Initial sizing for empty table (7-row minimum)
        self._update_size()

    # ------------------------------------------------------------------
    # Products setup
    # ------------------------------------------------------------------
    def set_products(self, products: list[Product]) -> None:
        """Load available product categories for the combo boxes."""
        self._products = products
        self._category_names = [p.category_name for p in products]

    def set_column_visibility(
        self, show_discount: bool = True, show_hsn: bool = True
    ) -> None:
        self._show_discount = show_discount
        self._show_hsn = show_hsn
        self.table.setColumnHidden(self.COL_DISC, not show_discount)
        self.table.setColumnHidden(self.COL_HSN, not show_hsn)

    def set_gst_columns(self, is_intra_state: bool) -> None:
        """Record supply type for reference.

        All three GST columns (CGST, SGST, IGST) are always visible.
        Unused columns display 0.00 based on the supply type.
        """
        self._is_intra_state = is_intra_state

    # ------------------------------------------------------------------
    # Auto-resize: grows with rows up to 15, then scrollbar
    # ------------------------------------------------------------------
    def _update_size(self) -> None:
        """Adjust the table height based on row count."""
        rows = self.table.rowCount()
        # Show at least 7 rows worth of space
        visible = max(7, min(rows, self._MAX_VISIBLE_ROWS))
        desired = self._HEADER_HEIGHT + (visible * self._ROW_HEIGHT) + 4
        self.table.setMinimumHeight(desired)
        if rows > self._MAX_VISIBLE_ROWS:
            self.table.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
        else:
            self.table.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )

    # ------------------------------------------------------------------
    # Row management
    # ------------------------------------------------------------------
    def add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        # S.No (read-only)
        sn_item = QTableWidgetItem(str(row + 1))
        sn_item.setFlags(sn_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        sn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, self.COL_SN, sn_item)

        # ---- Category combo with search-as-you-type ----
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.addItems(self._category_names)
        combo.setCurrentIndex(-1)
        combo.lineEdit().setPlaceholderText("Type to search\u2026")

        # Completer for search-as-you-type (matches anywhere in text)
        completer = QCompleter(self._category_names, combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setMaxVisibleItems(12)
        combo.setMaxVisibleItems(12)
        combo.setCompleter(completer)

        combo.currentTextChanged.connect(
            lambda text, r=row: self._on_category_changed(r, text)
        )
        self.table.setCellWidget(row, self.COL_CATEGORY, combo)

        # Item name (editable table cell)
        self.table.setItem(row, self.COL_ITEM, QTableWidgetItem(""))

        # HSN (auto-filled, still editable)
        self.table.setItem(row, self.COL_HSN, QTableWidgetItem(""))

        # ---- Qty: QLineEdit (default = 1) ----
        qty_edit = QLineEdit("1")
        qty_validator = QDoubleValidator(0.001, 999999.0, 3, qty_edit)
        qty_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        qty_edit.setValidator(qty_validator)
        qty_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        qty_edit.textChanged.connect(lambda _: self.items_changed.emit())
        self.table.setCellWidget(row, self.COL_QTY, qty_edit)

        # ---- Rate: QLineEdit (user types rupee amount freely) ----
        rate_edit = QLineEdit("0.00")
        rate_validator = QDoubleValidator(0.0, 99999999.99, 2, rate_edit)
        rate_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        rate_edit.setValidator(rate_validator)
        rate_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        rate_edit.textChanged.connect(lambda _: self.items_changed.emit())
        self.table.setCellWidget(row, self.COL_RATE, rate_edit)

        # ---- Discount %: QLineEdit (user types 5 for 5%) ----
        disc_edit = QLineEdit("0")
        disc_validator = QDoubleValidator(0.0, 100.0, 2, disc_edit)
        disc_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        disc_edit.setValidator(disc_validator)
        disc_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        disc_edit.textChanged.connect(lambda _: self.items_changed.emit())
        self.table.setCellWidget(row, self.COL_DISC, disc_edit)

        # Computed columns (read-only): Taxable, CGST, SGST, IGST, Total
        for col in (
            self.COL_TAXABLE, self.COL_CGST, self.COL_SGST,
            self.COL_IGST, self.COL_TOTAL,
        ):
            item = QTableWidgetItem("0.00")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row, col, item)

        self._update_size()
        self.items_changed.emit()

    def remove_last_row(self) -> None:
        if self.table.rowCount() > 0:
            self.table.removeRow(self.table.rowCount() - 1)
            self._renumber()
            self._update_size()
            self.items_changed.emit()

    def remove_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.table.selectedIndexes()},
            reverse=True,
        )
        for r in rows:
            self.table.removeRow(r)
        self._renumber()
        self._update_size()
        self.items_changed.emit()

    def clear_all(self) -> None:
        self.table.setRowCount(0)
        self._update_size()
        self.items_changed.emit()

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------
    def row_count(self) -> int:
        return self.table.rowCount()

    def get_row_data(self, row: int) -> dict:
        """Return raw data for one row.

        Keys: category, item_name, hsn, qty, rate_rupees, discount_pct
        """
        combo = self.table.cellWidget(row, self.COL_CATEGORY)
        category = combo.currentText().strip() if combo else ""

        item_cell = self.table.item(row, self.COL_ITEM)
        item_name = item_cell.text().strip() if item_cell else ""

        hsn_cell = self.table.item(row, self.COL_HSN)
        hsn = hsn_cell.text().strip() if hsn_cell else ""

        # Qty from QLineEdit
        qty_edit = self.table.cellWidget(row, self.COL_QTY)
        try:
            qty = float(qty_edit.text()) if qty_edit and qty_edit.text() else 1.0
        except ValueError:
            qty = 1.0

        # Rate from QLineEdit
        rate_edit = self.table.cellWidget(row, self.COL_RATE)
        try:
            rate_rupees = float(rate_edit.text()) if rate_edit and rate_edit.text() else 0.0
        except ValueError:
            rate_rupees = 0.0

        # Discount from QLineEdit  (user types 5 for 5%)
        disc_edit = self.table.cellWidget(row, self.COL_DISC)
        try:
            disc_val = float(disc_edit.text()) if disc_edit and disc_edit.text() else 0.0
        except ValueError:
            disc_val = 0.0
        discount_pct = disc_val / 100.0   # convert % to fraction

        return {
            "category": category,
            "item_name": item_name,
            "hsn": hsn,
            "qty": qty,
            "rate_rupees": rate_rupees,
            "discount_pct": discount_pct,
        }

    def set_computed_values(
        self,
        row: int,
        *,
        taxable: str,
        cgst_rate: float,
        cgst_amt: str,
        sgst_rate: float,
        sgst_amt: str,
        igst_rate: float,
        igst_amt: str,
        total: str,
    ) -> None:
        """Set the read-only computed columns for a given row.

        GST rate % is shown as cell tooltip and in the column header.
        The cell text shows only the formatted amount.
        """
        mapping = {
            self.COL_TAXABLE: (taxable, ""),
            self.COL_CGST:    (cgst_amt, f"CGST @ {cgst_rate:.1f}%"),
            self.COL_SGST:    (sgst_amt, f"SGST @ {sgst_rate:.1f}%"),
            self.COL_IGST:    (igst_amt, f"IGST @ {igst_rate:.1f}%"),
            self.COL_TOTAL:   (total, ""),
        }
        for col, (text, tooltip) in mapping.items():
            item = self.table.item(row, col)
            if item:
                item.setText(text)
                if tooltip:
                    item.setToolTip(tooltip)

        # Update column headers to show the rate
        if cgst_rate > 0:
            self.table.setHorizontalHeaderItem(
                self.COL_CGST,
                self._header_item(f"CGST ({cgst_rate:.1f}%)"),
            )
            self.table.setHorizontalHeaderItem(
                self.COL_SGST,
                self._header_item(f"SGST ({sgst_rate:.1f}%)"),
            )
        if igst_rate > 0:
            self.table.setHorizontalHeaderItem(
                self.COL_IGST,
                self._header_item(f"IGST ({igst_rate:.1f}%)"),
            )

    # ------------------------------------------------------------------
    # Populate from existing document items (edit mode)
    # ------------------------------------------------------------------
    def load_items(self, items: list) -> None:
        """Populate the grid from a list of DocumentItem objects."""
        self.clear_all()
        for di in items:
            self.add_row()
            row = self.table.rowCount() - 1

            # Category combo
            combo = self.table.cellWidget(row, self.COL_CATEGORY)
            idx = combo.findText(di.category_name)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(di.category_name)

            # Item name
            self.table.item(row, self.COL_ITEM).setText(di.item_name)

            # HSN
            self.table.item(row, self.COL_HSN).setText(di.hsn_code)

            # Qty (QLineEdit)
            qty_edit = self.table.cellWidget(row, self.COL_QTY)
            qty_edit.setText(str(di.quantity))

            # Rate (stored as paise, display as rupees)
            rate_edit = self.table.cellWidget(row, self.COL_RATE)
            rate_edit.setText(f"{di.rate / 100.0:.2f}")

            # Discount (stored as fraction, display as %)
            disc_edit = self.table.cellWidget(row, self.COL_DISC)
            disc_edit.setText(f"{di.discount_pct * 100.0:.2f}")

        self._update_size()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _on_category_changed(self, row: int, text: str) -> None:
        """Auto-fill HSN + default rate when category is selected."""
        for p in self._products:
            if p.category_name == text:
                hsn_cell = self.table.item(row, self.COL_HSN)
                if hsn_cell:
                    hsn_cell.setText(p.hsn_code)
                # Auto-fill rate if product has a default
                if p.default_rate:
                    rate_edit = self.table.cellWidget(row, self.COL_RATE)
                    if rate_edit:
                        rate_edit.setText(f"{p.default_rate / 100.0:.2f}")
                break
        self.items_changed.emit()

    def _renumber(self) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COL_SN)
            if item:
                item.setText(str(row + 1))

    def _get_gst_rate_for_category(self, category: str) -> float:
        for p in self._products:
            if p.category_name == category:
                return p.gst_rate
        return 18.0  # fallback

    def _header_item(self, text: str) -> QTableWidgetItem:
        """Create a styled header item."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        return item
