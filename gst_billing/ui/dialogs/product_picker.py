"""
Product picker dialog — select a product category, auto-fills HSN.
"""

from __future__ import annotations

import sqlite3
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHeaderView, QAbstractItemView, QDoubleSpinBox,
    QMessageBox, QWidget,
)

from models.product import Product
from repositories.product_repo import ProductRepo


class ProductPickerDialog(QDialog):
    """Modal dialog: select or add a product/service category."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.repo = ProductRepo(conn)
        self.selected_product: Product | None = None
        self.setWindowTitle("Select Product / Service")
        self.setMinimumSize(600, 420)
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Search category or HSN…")
        self._search.textChanged.connect(self._load)
        search_row.addWidget(self._search)

        btn_new = QPushButton("+ New Product")
        btn_new.clicked.connect(self._add_new_product)
        search_row.addWidget(btn_new)
        layout.addLayout(search_row)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels([
            "Category Name", "HSN Code", "GST %", "Default Rate",
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.doubleClicked.connect(self._accept)
        layout.addWidget(self._table)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    def _load(self) -> None:
        query = self._search.text().strip() if self._search else ""
        if query:
            results = self.repo.search(query)
        else:
            results = self.repo.list_all(active_only=True)

        self._results = results
        self._table.setRowCount(len(results))
        for i, p in enumerate(results):
            self._table.setItem(i, 0, QTableWidgetItem(p.category_name))
            self._table.setItem(i, 1, QTableWidgetItem(p.hsn_code))
            self._table.setItem(i, 2, QTableWidgetItem(f"{p.gst_rate}%"))
            rate_display = f"₹{p.default_rate / 100:.2f}" if p.default_rate else "—"
            self._table.setItem(i, 3, QTableWidgetItem(rate_display))

    def _accept(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._results):
            return
        self.selected_product = self._results[row]
        self.accept()

    # ------------------------------------------------------------------
    def _add_new_product(self) -> None:
        dlg = _AddProductDialog(self.conn, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.saved_product:
            self.selected_product = dlg.saved_product
            self.accept()


class _AddProductDialog(QDialog):
    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.saved_product: Product | None = None
        self.setWindowTitle("Add New Product / Service")
        self.setMinimumWidth(380)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._cat = QLineEdit()
        form.addRow("Category Name *:", self._cat)

        self._hsn = QLineEdit()
        self._hsn.setMaxLength(8)
        form.addRow("HSN / SAC Code *:", self._hsn)

        self._gst = QDoubleSpinBox()
        self._gst.setRange(0, 100)
        self._gst.setValue(18.0)
        self._gst.setSuffix("%")
        form.addRow("GST Rate:", self._gst)

        self._rate = QDoubleSpinBox()
        self._rate.setRange(0, 99_999_999)
        self._rate.setDecimals(2)
        self._rate.setPrefix("₹")
        form.addRow("Default Rate:", self._rate)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _save(self) -> None:
        cat = self._cat.text().strip()
        hsn = self._hsn.text().strip()
        if not cat:
            QMessageBox.warning(self, "Validation", "Category name is required.")
            return
        if not hsn:
            QMessageBox.warning(self, "Validation", "HSN/SAC code is required.")
            return

        p = Product(
            category_name=cat,
            hsn_code=hsn,
            gst_rate=self._gst.value(),
            default_rate=int(self._rate.value() * 100),  # paise
        )
        repo = ProductRepo(self.conn)
        try:
            p.id = repo.insert(p)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.saved_product = p
        self.accept()
