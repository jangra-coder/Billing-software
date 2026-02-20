"""
Purchase Tracker Page — expense register with category, vendor, date filters,
summary panel, and Excel export/import.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from models.purchase import Purchase
from repositories.custom_field_repo import CustomFieldRepo
from repositories.purchase_repo import PurchaseRepo
from repositories.settings_repo import PurchaseCategoryRepo
from services.calculator import format_currency, paise_to_rupees, rupees_to_paise
from services.excel_io import (
    PURCHASE_ALIASES, build_column_map, dataclass_list_to_dicts,
    export_to_excel, get_sheet_names, import_from_excel, remap_row,
)
from services.validator import validate_amount, validate_date
from ui.widgets.custom_fields import (
    ManageFieldsDialog, build_custom_inputs, load_custom_inputs,
    read_custom_inputs,
)
from ui.widgets.search_bar import SearchBar
from ui.widgets.currency_input import CurrencyInput
from ui.widgets.date_picker import DatePicker


class PurchaseTrackerPage(QWidget):
    """Full purchase/expense tracker with filters, CRUD dialog, Excel I/O."""

    PAGE_SIZE = 100

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self._repo = PurchaseRepo(conn)
        self._cat_repo = PurchaseCategoryRepo(conn)
        self._current_page = 0
        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI
    # ==================================================================
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 8)
        outer.setSpacing(8)

        # ── Header
        hdr = QHBoxLayout()
        title = QLabel("Purchases & Expenses")
        title.setObjectName("heading")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_add = QPushButton("+ Add Purchase")
        btn_add.clicked.connect(self._add_purchase)
        hdr.addWidget(btn_add)

        btn_export = QPushButton("📤 Export to Excel")
        btn_export.clicked.connect(self._export_excel)
        hdr.addWidget(btn_export)

        btn_import = QPushButton("📥 Import from Excel")
        btn_import.clicked.connect(self._import_excel)
        hdr.addWidget(btn_import)

        btn_manage = QPushButton("⚙️ Manage Fields")
        btn_manage.clicked.connect(self._manage_fields)
        hdr.addWidget(btn_manage)

        outer.addLayout(hdr)

        # ── Filter row
        filt = QHBoxLayout()

        filt.addWidget(QLabel("From:"))
        self._date_from = DatePicker()
        self._date_from.setDate(date(date.today().year, 4, 1))
        filt.addWidget(self._date_from)

        filt.addWidget(QLabel("To:"))
        self._date_to = DatePicker()
        filt.addWidget(self._date_to)

        filt.addWidget(QLabel("Vendor:"))
        self._cmb_vendor = QComboBox()
        self._cmb_vendor.setEditable(True)
        self._cmb_vendor.addItem("All")
        for v in self._repo.distinct_vendors():
            self._cmb_vendor.addItem(v)
        filt.addWidget(self._cmb_vendor)

        filt.addWidget(QLabel("Category:"))
        self._cmb_category = QComboBox()
        self._cmb_category.addItem("All", "")
        for cat in self._cat_repo.list_active():
            self._cmb_category.addItem(cat, cat)
        filt.addWidget(self._cmb_category)

        btn_filter = QPushButton("🔍 Apply")
        btn_filter.clicked.connect(self._apply_filters)
        filt.addWidget(btn_filter)

        outer.addLayout(filt)

        # ── Table
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Date", "Invoice #", "Description", "Vendor", "Category", "Amount (₹)", "ID",
        ])
        self._table.setColumnHidden(6, True)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setMinimumSectionSize(70)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.doubleClicked.connect(self._edit_selected)
        outer.addWidget(self._table, 1)

        # ── Summary + actions
        foot = QHBoxLayout()

        self._lbl_summary = QLabel("Total: ₹ 0.00")
        self._lbl_summary.setStyleSheet("font-weight: bold; font-size: 14px;")
        foot.addWidget(self._lbl_summary)
        foot.addStretch()

        self._btn_edit = QPushButton("✏️ Edit")
        self._btn_edit.clicked.connect(self._edit_selected)
        foot.addWidget(self._btn_edit)

        self._btn_del = QPushButton("🗑️ Delete")
        self._btn_del.setProperty("danger", True)
        self._btn_del.clicked.connect(self._delete_selected)
        foot.addWidget(self._btn_del)

        outer.addLayout(foot)

    # ==================================================================
    # Data
    # ==================================================================
    def refresh(self) -> None:
        self._apply_filters()

    def _get_filters(self) -> dict:
        d = {}
        d["date_from"] = self._date_from.iso_date()
        d["date_to"] = self._date_to.iso_date()
        vendor = self._cmb_vendor.currentText().strip()
        if vendor and vendor != "All":
            d["vendor"] = vendor
        cat = self._cmb_category.currentData()
        if cat:
            d["category"] = cat
        return d

    def _apply_filters(self) -> None:
        self._current_page = 0
        self._load_data()

    def _load_data(self) -> None:
        kw = self._get_filters()
        purchases = self._repo.list_filtered(**kw, limit=self.PAGE_SIZE,
                                              offset=self._current_page * self.PAGE_SIZE)
        total_paise = self._repo.sum_filtered(**kw)

        self._lbl_summary.setText(f"Total: {format_currency(total_paise)}")

        self._table.setRowCount(0)
        for p in purchases:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(_fmt_date(p.purchase_date)))
            self._table.setItem(row, 1, QTableWidgetItem(p.invoice_no or ""))
            self._table.setItem(row, 2, QTableWidgetItem(p.description or ""))
            self._table.setItem(row, 3, QTableWidgetItem(p.vendor_name or ""))
            self._table.setItem(row, 4, QTableWidgetItem(p.category or ""))
            amt = QTableWidgetItem(format_currency(p.amount))
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 5, amt)
            self._table.setItem(row, 6, QTableWidgetItem(str(p.id)))

    def _selected_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 6)
        return int(item.text()) if item else None

    # ==================================================================
    # CRUD
    # ==================================================================
    def _add_purchase(self) -> None:
        dlg = _PurchaseDialog(self.conn, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.purchase:
            self._repo.insert(dlg.purchase)
            self._refresh_vendors()
            self.refresh()

    def _edit_selected(self) -> None:
        pid = self._selected_id()
        if pid is None:
            QMessageBox.information(self, "Select", "Select a purchase first.")
            return
        existing = self._repo.get_by_id(pid)
        if not existing:
            return
        dlg = _PurchaseDialog(self.conn, existing=existing, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.purchase:
            dlg.purchase.id = pid
            self._repo.update(dlg.purchase)
            self.refresh()

    def _delete_selected(self) -> None:
        pid = self._selected_id()
        if pid is None:
            QMessageBox.information(self, "Select", "Select a purchase first.")
            return
        reply = QMessageBox.warning(
            self, "Delete Purchase",
            "Delete this purchase entry? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._repo.delete(pid)
            self.refresh()

    def _refresh_vendors(self) -> None:
        self._cmb_vendor.clear()
        self._cmb_vendor.addItem("All")
        for v in self._repo.distinct_vendors():
            self._cmb_vendor.addItem(v)

    def _manage_fields(self) -> None:
        dlg = ManageFieldsDialog(
            self.conn, "purchase", "Purchase", parent=self,
        )
        dlg.exec()
        # No form to sync here — the dialog is created fresh each time

    # ==================================================================
    # Excel
    # ==================================================================
    def _export_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Purchases to Excel", "purchases.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        kw = self._get_filters()
        purchases = self._repo.list_filtered(**kw, limit=99999, offset=0)
        rows = dataclass_list_to_dicts(purchases, exclude_fields=("created_at", "custom_fields"))
        for purch, row_dict in zip(purchases, rows):
            try:
                cf = json.loads(purch.custom_fields) if purch.custom_fields else {}
            except (json.JSONDecodeError, TypeError):
                cf = {}
            row_dict.update(cf)
        export_to_excel(
            rows, path,
            sheet_name="Purchases",
            title="Purchase Register",
            money_columns=("amount",),
        )
        QMessageBox.information(self, "Exported", f"Exported {len(rows)} purchases.")

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Purchases from Excel", "",
            "Excel Files (*.xlsx *.xlsm)",
        )
        if not path:
            return
        try:
            # Sheet selection for multi-sheet files
            sheets = get_sheet_names(path)
            sheet_name = None
            if len(sheets) > 1:
                chosen, ok = QInputDialog.getItem(
                    self, "Select Sheet",
                    "This file has multiple sheets.\nSelect the sheet to import from:",
                    sheets, 0, False,
                )
                if not ok:
                    return
                sheet_name = chosen

            raw_headers, rows = import_from_excel(path, sheet_name=sheet_name)
            if not rows:
                QMessageBox.warning(self, "Empty", "No data rows found in the selected sheet.")
                return

            # ── Flexible column mapping ──
            col_map = build_column_map(
                raw_headers, PURCHASE_ALIASES,
                required_fields=[],
            )

            # Show mapping preview
            preview_lines = []
            for canon, orig in col_map.mapped.items():
                preview_lines.append(f"  {orig}  →  {canon}")
            if col_map.unmapped:
                preview_lines.append(f"\nExtra columns (will become custom fields):")
                for u in col_map.unmapped:
                    preview_lines.append(f"  {u}  →  custom: {u}")
            reply = QMessageBox.question(
                self, "Column Mapping",
                f"Found {len(rows)} rows. Column mapping:\n\n"
                + "\n".join(preview_lines)
                + "\n\nProceed with import?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # Auto-create custom field definitions for unmapped columns
            cf_repo = CustomFieldRepo(self.conn)
            extra_field_names: list[str] = []
            for orig in col_map.unmapped:
                fname = CustomFieldRepo.to_field_name(orig)
                if fname and fname not in ("id", "created_at"):
                    cf_repo.ensure_field("purchase", fname, orig)
                    extra_field_names.append(fname)

            imported = 0
            for r in rows:
                mapped = remap_row(r, col_map)
                desc = str(mapped.get("description", "")).strip()

                raw_amt = mapped.get("amount", 0) or 0
                try:
                    amt_val = float(raw_amt)
                except (ValueError, TypeError):
                    amt_val = 0.0
                if 0 < amt_val < 100_000:
                    amt_paise = rupees_to_paise(amt_val)
                else:
                    amt_paise = int(amt_val)

                dt = str(mapped.get("purchase_date", "")).strip()
                if not dt:
                    dt = date.today().isoformat()
                dt = dt[:10]

                # Collect extra column values into custom_fields JSON
                cf_data: dict = {}
                for orig in col_map.unmapped:
                    fname = CustomFieldRepo.to_field_name(orig)
                    snake_key = CustomFieldRepo.to_field_name(orig)
                    if fname and snake_key in r:
                        val = r[snake_key]
                        if val is not None and str(val).strip():
                            cf_data[fname] = val

                p = Purchase(
                    purchase_date=dt,
                    invoice_no=str(mapped.get("invoice_no", "")).strip() or None,
                    description=desc or None,
                    amount=amt_paise,
                    vendor_name=str(mapped.get("vendor_name", "")).strip() or None,
                    category=str(mapped.get("category", "")).strip() or None,
                    notes=str(mapped.get("notes", "")).strip() or None,
                    custom_fields=json.dumps(cf_data, ensure_ascii=False) if cf_data else "{}",
                )
                self._repo.insert(p)
                imported += 1

            self._refresh_vendors()
            self.refresh()
            extra_msg = ""
            if extra_field_names:
                extra_msg = f"\n\nCustom fields auto-created: {', '.join(extra_field_names)}"
            QMessageBox.information(
                self, "Imported",
                f"Successfully imported {imported} purchases from {len(rows)} rows."
                + extra_msg,
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))


# ── Purchase add/edit dialog ───────────────────────────────────────
class _PurchaseDialog(QDialog):
    """Modal dialog for adding / editing a purchase."""

    def __init__(self, conn: sqlite3.Connection, *,
                 existing: Purchase | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Purchase" if existing else "Add Purchase")
        self.setMinimumWidth(420)
        self.purchase: Purchase | None = None
        self._conn = conn
        self._cat_repo = PurchaseCategoryRepo(conn)
        self._build(existing)

    def _build(self, existing: Purchase | None) -> None:
        form = QFormLayout(self)
        form.setSpacing(14)
        form.setContentsMargins(20, 20, 20, 16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # Determine which built-in fields are active
        cf_repo = CustomFieldRepo(self._conn)
        active = cf_repo.active_builtin_names("purchase")

        # Date — always shown (required)
        self._date = DatePicker()
        form.addRow("Date *", self._date)

        # Invoice # — optional built-in
        self._invoice = QLineEdit()
        self._invoice.setPlaceholderText("Invoice / Bill number")
        if "invoice_no" in active:
            form.addRow("Invoice #", self._invoice)

        # Description — optional built-in
        self._desc = QLineEdit()
        self._desc.setPlaceholderText("Description / Particulars")
        if "description" in active:
            form.addRow("Description", self._desc)

        # Amount — always shown (required)
        self._amount = CurrencyInput()
        form.addRow("Amount *", self._amount)

        # Vendor — optional built-in
        self._vendor = QLineEdit()
        self._vendor.setPlaceholderText("Vendor / Supplier name")
        if "vendor_name" in active:
            form.addRow("Vendor", self._vendor)

        # Category — optional built-in
        self._category = QComboBox()
        self._category.setEditable(True)
        for cat in self._cat_repo.list_active():
            self._category.addItem(cat)
        if "category" in active:
            form.addRow("Category", self._category)

        # Notes — optional built-in
        self._notes = QPlainTextEdit()
        self._notes.setMaximumHeight(80)
        if "notes" in active:
            form.addRow("Notes", self._notes)

        # Dynamic custom fields
        self._custom_inputs = build_custom_inputs(
            self._conn, "purchase", form,
        )

        if existing:
            try:
                self._date.set_date(existing.purchase_date)
            except Exception:
                pass
            self._invoice.setText(existing.invoice_no or "")
            self._desc.setText(existing.description or "")
            self._amount.set_paise(existing.amount)
            self._vendor.setText(existing.vendor_name or "")
            if existing.category:
                idx = self._category.findText(existing.category)
                if idx >= 0:
                    self._category.setCurrentIndex(idx)
                else:
                    self._category.setCurrentText(existing.category)
            self._notes.setPlainText(existing.notes or "")
            load_custom_inputs(self._custom_inputs, existing.custom_fields)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._on_ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _on_ok(self) -> None:
        amt = self._amount.paise()
        if amt <= 0:
            QMessageBox.warning(self, "Required", "Amount must be greater than zero.")
            return
        self.purchase = Purchase(
            purchase_date=self._date.iso_date(),
            invoice_no=self._invoice.text().strip() or None,
            description=self._desc.text().strip() or None,
            amount=amt,
            vendor_name=self._vendor.text().strip() or None,
            category=self._category.currentText().strip() or None,
            notes=self._notes.toPlainText().strip() or None,
            custom_fields=read_custom_inputs(self._custom_inputs),
        )
        self.accept()


def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.strptime(iso, "%Y-%m-%d")
        return dt.strftime("%d-%b-%y")
    except Exception:
        return iso
