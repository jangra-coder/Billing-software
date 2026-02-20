"""
Customer picker dialog — search, select, or add new customer.
"""

from __future__ import annotations

import sqlite3
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QHeaderView,
    QAbstractItemView, QFormLayout, QComboBox, QDialogButtonBox,
    QMessageBox, QWidget,
)

from models.customer import Customer
from repositories.customer_repo import CustomerRepo
from repositories.settings_repo import StateMasterRepo


class CustomerPickerDialog(QDialog):
    """Modal dialog: search/select an existing customer or add a new one."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.repo = CustomerRepo(conn)
        self.selected_customer: Customer | None = None
        self.setWindowTitle("Select Customer")
        self.setMinimumSize(700, 500)
        self._build_ui()
        self._search("")  # load all

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Search row
        search_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 Search by name, company, GSTIN, mobile…")
        self._search_edit.textChanged.connect(self._search)
        search_row.addWidget(self._search_edit)

        btn_new = QPushButton("+ New Customer")
        btn_new.clicked.connect(self._add_new_customer)
        search_row.addWidget(btn_new)
        layout.addLayout(search_row)

        # Results table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Name", "Company", "GSTIN", "Mobile", "State",
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
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._accept_selection)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ------------------------------------------------------------------
    # Search / table
    # ------------------------------------------------------------------
    def _search(self, query: str) -> None:
        if query.strip():
            results = self.repo.search(query.strip())
        else:
            results = self.repo.list_all(active_only=True)

        self._results = results
        self._table.setRowCount(len(results))
        for i, c in enumerate(results):
            self._table.setItem(i, 0, QTableWidgetItem(c.name))
            self._table.setItem(i, 1, QTableWidgetItem(c.company_name))
            self._table.setItem(i, 2, QTableWidgetItem(c.gstin))
            self._table.setItem(i, 3, QTableWidgetItem(c.mobile))
            self._table.setItem(i, 4, QTableWidgetItem(c.state_code))

    def _on_double_click(self) -> None:
        self._accept_selection()

    def _accept_selection(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._results):
            return
        self.selected_customer = self._results[row]
        self.accept()

    # ------------------------------------------------------------------
    # Add new customer inline
    # ------------------------------------------------------------------
    def _add_new_customer(self) -> None:
        dlg = _AddCustomerDialog(self.conn, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.saved_customer:
            self.selected_customer = dlg.saved_customer
            self.accept()


# ======================================================================
# Mini dialog to add a new customer quickly
# ======================================================================
class _AddCustomerDialog(QDialog):
    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.saved_customer: Customer | None = None
        self.setWindowTitle("Add New Customer")
        self.setMinimumWidth(450)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit()
        form.addRow("Name *:", self._name)

        self._company = QLineEdit()
        form.addRow("Company:", self._company)

        self._gstin = QLineEdit()
        self._gstin.setMaxLength(15)
        form.addRow("GSTIN:", self._gstin)

        self._mobile = QLineEdit()
        self._mobile.setMaxLength(10)
        form.addRow("Mobile:", self._mobile)

        self._email = QLineEdit()
        form.addRow("Email:", self._email)

        self._addr1 = QLineEdit()
        form.addRow("Address 1:", self._addr1)

        self._addr2 = QLineEdit()
        form.addRow("Address 2:", self._addr2)

        self._state = QComboBox()
        state_repo = StateMasterRepo(self.conn)
        self._states = state_repo.list_all()
        self._state.addItem("-- Select --", "")
        for s in self._states:
            self._state.addItem(f"{s.state_name} ({s.code})", s.code)
        form.addRow("State:", self._state)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _save(self) -> None:
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Customer name is required.")
            return

        c = Customer(
            name=name,
            company_name=self._company.text().strip(),
            gstin=self._gstin.text().strip().upper(),
            mobile=self._mobile.text().strip(),
            email=self._email.text().strip(),
            address_line1=self._addr1.text().strip(),
            address_line2=self._addr2.text().strip(),
            state_code=self._state.currentData() or "",
        )

        repo = CustomerRepo(self.conn)
        c.id = repo.insert(c)
        self.saved_customer = c
        self.accept()
