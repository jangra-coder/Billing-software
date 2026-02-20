"""
Customer Manager Page — full CRUD, search, detail form, Excel export/import.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from models.customer import Customer
from repositories.custom_field_repo import CustomFieldRepo
from repositories.customer_repo import CustomerRepo
from services.validator import validate_gstin, validate_mobile, validate_email, validate_pan
from services.excel_io import (
    CUSTOMER_ALIASES, build_column_map, dataclass_list_to_dicts,
    export_to_excel, get_sheet_names, import_from_excel, remap_row,
)
from ui.widgets.custom_fields import (
    ManageFieldsDialog, build_custom_inputs, load_custom_inputs,
    read_custom_inputs,
)
from ui.widgets.search_bar import SearchBar
from ui.widgets.gstin_input import GSTINInput


class CustomerManagerPage(QWidget):
    """Master-detail CRUD for customers."""

    customer_updated = pyqtSignal()

    _FIELDS = (
        ("name", "Customer / Contact Name *"),
        ("company_name", "Company / Business Name"),
        ("mobile", "Mobile"),
        ("email", "Email"),
        ("pan", "PAN"),
        ("address_line1", "Address Line 1"),
        ("address_line2", "Address Line 2"),
        ("address_line3", "Address Line 3"),
        ("state_code", "State Code (2-digit)"),
        ("vendor_code", "Vendor Code"),
    )

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self._repo = CustomerRepo(conn)
        self._editing_id: int | None = None
        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI
    # ==================================================================
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 8)
        outer.setSpacing(8)

        # ── Top row: title, search, actions
        hdr = QHBoxLayout()
        title = QLabel("Customers")
        title.setObjectName("heading")
        hdr.addWidget(title)
        hdr.addStretch()

        self._search = SearchBar("Search customers…")
        self._search.search_changed.connect(self._on_search)
        hdr.addWidget(self._search)

        btn_export = QPushButton("📤 Export to Excel")
        btn_export.clicked.connect(self._export_excel)
        hdr.addWidget(btn_export)

        btn_import = QPushButton("📥 Import from Excel")
        btn_import.clicked.connect(self._import_excel)
        hdr.addWidget(btn_import)

        btn_sample = QPushButton("📋 Export Sample")
        btn_sample.setProperty("secondary", True)
        btn_sample.clicked.connect(self._export_sample)
        hdr.addWidget(btn_sample)

        btn_manage = QPushButton("⚙️ Manage Fields")
        btn_manage.clicked.connect(self._manage_fields)
        hdr.addWidget(btn_manage)

        outer.addLayout(hdr)

        # ── Splitter: list (left) + detail (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter, 1)

        # Left: table
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels([
            "Name", "Company", "GSTIN", "Mobile", "Email", "PAN", "State", "Address", "ID",
        ])
        self._table.setColumnHidden(8, True)  # ID hidden
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        hdr.setMinimumSectionSize(60)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.currentCellChanged.connect(self._on_row_changed)
        ll.addWidget(self._table)
        splitter.addWidget(left)

        # Right: detail form
        right = QWidget()
        rl = QVBoxLayout(right)

        grp = QGroupBox("Customer Details")
        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(16, 18, 16, 14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._inputs: dict[str, QLineEdit | GSTINInput] = {}
        self._builtin_labels: dict[str, QWidget] = {}
        for key, label in self._FIELDS:
            inp = QLineEdit()
            lbl = QLabel(label)
            form.addRow(lbl, inp)
            self._inputs[key] = inp
            if key != "name":  # name is required, always visible
                self._builtin_labels[key] = lbl

        # Replace plain GSTIN line-edit with GSTINInput widget
        gstin_input = GSTINInput()
        gstin_input.state_code_detected.connect(self._on_state_detected)
        form.removeRow(self._inputs["pan"])  # keep below gstin
        lbl_gstin = QLabel("GSTIN")
        form.insertRow(4, lbl_gstin, gstin_input)
        self._inputs["gstin"] = gstin_input  # type: ignore[assignment]
        self._builtin_labels["gstin"] = lbl_gstin
        lbl_pan = QLabel("PAN")
        pan = QLineEdit()
        form.insertRow(5, lbl_pan, pan)
        self._inputs["pan"] = pan
        self._builtin_labels["pan"] = lbl_pan

        # Dynamic custom fields
        self._detail_form = form
        self._custom_inputs: dict[str, QLineEdit] = {}
        self._rebuild_custom_fields()
        self._sync_builtin_visibility()

        grp.setLayout(form)
        rl.addWidget(grp)

        # Action buttons
        btns = QHBoxLayout()
        self._btn_new = QPushButton("➕ New")
        self._btn_new.clicked.connect(self._new_customer)
        btns.addWidget(self._btn_new)

        self._btn_save = QPushButton("💾 Save")
        self._btn_save.clicked.connect(self._save)
        btns.addWidget(self._btn_save)

        self._btn_deactivate = QPushButton("�️ Remove")
        self._btn_deactivate.clicked.connect(self._deactivate)
        btns.addWidget(self._btn_deactivate)
        btns.addStretch()
        rl.addLayout(btns)
        rl.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([500, 400])

    # ==================================================================
    # Data
    # ==================================================================
    def refresh(self) -> None:
        q = self._search.text().strip()
        custs = self._repo.search(q) if q else self._repo.list_all(active_only=True)
        self._table.setRowCount(0)
        for c in custs:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(c.name))
            self._table.setItem(row, 1, QTableWidgetItem(c.company_name or ""))
            self._table.setItem(row, 2, QTableWidgetItem(c.gstin or ""))
            self._table.setItem(row, 3, QTableWidgetItem(c.mobile or ""))
            self._table.setItem(row, 4, QTableWidgetItem(c.email or ""))
            self._table.setItem(row, 5, QTableWidgetItem(c.pan or ""))
            self._table.setItem(row, 6, QTableWidgetItem(c.state_code or ""))
            addr = ", ".join(filter(None, [c.address_line1, c.address_line2, c.address_line3]))
            self._table.setItem(row, 7, QTableWidgetItem(addr))
            self._table.setItem(row, 8, QTableWidgetItem(str(c.id)))

    def _on_search(self, text: str) -> None:
        self.refresh()

    def _on_row_changed(self, row: int, _col: int, _prev_row: int, _prev_col: int) -> None:
        if row < 0:
            return
        item = self._table.item(row, 8)
        if not item:
            return
        cid = int(item.text())
        cust = self._repo.get_by_id(cid)
        if cust:
            self._load_into_form(cust)

    def _load_into_form(self, c: Customer) -> None:
        self._editing_id = c.id
        self._inputs["name"].setText(c.name)
        self._inputs["company_name"].setText(c.company_name or "")
        self._inputs["mobile"].setText(c.mobile or "")
        self._inputs["email"].setText(c.email or "")
        if isinstance(self._inputs["gstin"], GSTINInput):
            self._inputs["gstin"].setText(c.gstin or "")
        self._inputs["pan"].setText(c.pan or "")
        self._inputs["address_line1"].setText(c.address_line1 or "")
        self._inputs["address_line2"].setText(c.address_line2 or "")
        self._inputs["address_line3"].setText(c.address_line3 or "")
        self._inputs["state_code"].setText(c.state_code or "")
        self._inputs["vendor_code"].setText(c.vendor_code or "")
        load_custom_inputs(self._custom_inputs, c.custom_fields)

    def _on_state_detected(self, code: str) -> None:
        self._inputs["state_code"].setText(code)

    # ==================================================================
    # CRUD actions
    # ==================================================================
    def _new_customer(self) -> None:
        self._editing_id = None
        for key, inp in self._inputs.items():
            if isinstance(inp, GSTINInput):
                inp.clear()
            else:
                inp.clear()
        for w in self._custom_inputs.values():
            w.clear()

    def _save(self) -> None:
        name = self._inputs["name"].text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Customer name is required.")
            return

        # Helper to get text only if the field is visible
        def _field(key: str) -> str:
            w = self._inputs[key]
            if not w.isVisible():
                return ""
            if isinstance(w, GSTINInput):
                return w.text().strip()
            return w.text().strip()

        # Validate optional fields only if visible
        gstin_val = _field("gstin")
        if gstin_val:
            ok, msg = validate_gstin(gstin_val)
            if not ok:
                QMessageBox.warning(self, "Invalid GSTIN", msg)
                return

        mobile = _field("mobile")
        if mobile:
            ok, msg = validate_mobile(mobile)
            if not ok:
                QMessageBox.warning(self, "Invalid Mobile", msg)
                return

        email = _field("email")
        if email:
            ok, msg = validate_email(email)
            if not ok:
                QMessageBox.warning(self, "Invalid Email", msg)
                return

        pan_val = _field("pan")
        if pan_val:
            ok, msg = validate_pan(pan_val)
            if not ok:
                QMessageBox.warning(self, "Invalid PAN", msg)
                return

        cust = Customer(
            id=self._editing_id,
            name=name,
            company_name=_field("company_name") or None,
            mobile=mobile or None,
            email=email or None,
            gstin=gstin_val.upper() or None,
            pan=pan_val.upper() or None,
            address_line1=_field("address_line1") or None,
            address_line2=_field("address_line2") or None,
            address_line3=_field("address_line3") or None,
            state_code=_field("state_code") or None,
            vendor_code=_field("vendor_code") or None,
            custom_fields=read_custom_inputs(self._custom_inputs),
        )

        if self._editing_id:
            self._repo.update(cust)
        else:
            new_id = self._repo.insert(cust)
            self._editing_id = new_id

        self.customer_updated.emit()
        self.refresh()
        QMessageBox.information(self, "Saved", f"Customer '{name}' saved.")

    def _deactivate(self) -> None:
        if not self._editing_id:
            QMessageBox.information(self, "Select", "Select a customer first.")
            return
        reply = QMessageBox.warning(
            self, "Remove",
            "Remove this customer? They won't appear in lookups.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._repo.soft_delete(self._editing_id)
            self._new_customer()
            self.customer_updated.emit()
            self.refresh()

    # ==================================================================
    # Custom Fields
    # ==================================================================
    def _sync_builtin_visibility(self) -> None:
        """Show/hide built-in form rows based on active_builtin_names."""
        cf_repo = CustomFieldRepo(self.conn)
        active = cf_repo.active_builtin_names("customer")
        for fname, lbl in self._builtin_labels.items():
            visible = fname in active
            lbl.setVisible(visible)
            self._inputs[fname].setVisible(visible)

    def _rebuild_custom_fields(self) -> None:
        for widget in self._custom_inputs.values():
            row, _ = self._detail_form.getWidgetPosition(widget)
            if row >= 0:
                self._detail_form.removeRow(row)
        self._custom_inputs = build_custom_inputs(
            self.conn, "customer", self._detail_form,
        )

    def _manage_fields(self) -> None:
        dlg = ManageFieldsDialog(
            self.conn, "customer", "Customer", parent=self,
        )
        dlg.exec()
        self._sync_builtin_visibility()
        self._rebuild_custom_fields()

    # ==================================================================
    # Excel
    # ==================================================================
    def _export_sample(self) -> None:
        """Export a blank sample Excel template with correct headers."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Sample Import File", "customer_import_sample.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        sample = [{
            "name": "Example Customer",
            "company_name": "Example Co.",
            "mobile": "9876543210",
            "email": "example@mail.com",
            "gstin": "06AAACB1234F1Z5",
            "pan": "AAACB1234F",
            "address_line1": "123 Main St",
            "address_line2": "Suite 100",
            "address_line3": "",
            "state_code": "06",
            "vendor_code": "",
        }]
        export_to_excel(sample, path, sheet_name="Customers", title="Customer Import Sample")
        QMessageBox.information(
            self, "Sample Exported",
            f"Sample import file saved to:\n{path}\n\n"
            "Fill in your data following this template and use 'Import from Excel' to load it.",
        )

    def _export_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Customers to Excel", "customers.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        custs = self._repo.list_all(active_only=False)
        rows = dataclass_list_to_dicts(custs, exclude_fields=("updated_at", "custom_fields"))
        for cust, row_dict in zip(custs, rows):
            try:
                cf = json.loads(cust.custom_fields) if cust.custom_fields else {}
            except (json.JSONDecodeError, TypeError):
                cf = {}
            row_dict.update(cf)
        export_to_excel(rows, path, sheet_name="Customers", title="Customer Master")
        QMessageBox.information(self, "Exported", f"Exported {len(rows)} customers.")

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Customers from Excel", "",
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
                raw_headers, CUSTOMER_ALIASES,
                required_fields=["name"],
            )
            if col_map.missing_required:
                QMessageBox.warning(
                    self, "Missing Columns",
                    "Could not find required column(s):\n"
                    + ", ".join(col_map.missing_required)
                    + "\n\nAccepted names for Name: "
                    + ", ".join(CUSTOMER_ALIASES["name"])
                    + "\n\nPlease rename the column in your Excel file and try again.",
                )
                return

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
                if fname and fname not in ("id", "is_active", "created_at", "updated_at"):
                    cf_repo.ensure_field("customer", fname, orig)
                    extra_field_names.append(fname)

            imported = 0
            for r in rows:
                mapped = remap_row(r, col_map)
                name = str(mapped.get("name", "")).strip()
                if not name:
                    continue

                # Collect extra column values into custom_fields JSON
                cf_data: dict = {}
                for orig in col_map.unmapped:
                    fname = CustomFieldRepo.to_field_name(orig)
                    snake_key = CustomFieldRepo.to_field_name(orig)
                    if fname and snake_key in r:
                        val = r[snake_key]
                        if val is not None and str(val).strip():
                            cf_data[fname] = val

                cust = Customer(
                    name=name,
                    company_name=str(mapped.get("company_name", "")).strip() or None,
                    mobile=str(mapped.get("mobile", "")).strip() or None,
                    email=str(mapped.get("email", "")).strip() or None,
                    gstin=str(mapped.get("gstin", "")).strip().upper() or None,
                    pan=str(mapped.get("pan", "")).strip().upper() or None,
                    address_line1=str(mapped.get("address_line1", "")).strip() or None,
                    address_line2=str(mapped.get("address_line2", "")).strip() or None,
                    address_line3=str(mapped.get("address_line3", "")).strip() or None,
                    state_code=str(mapped.get("state_code", "")).strip() or None,
                    vendor_code=str(mapped.get("vendor_code", "")).strip() or None,
                    custom_fields=json.dumps(cf_data, ensure_ascii=False) if cf_data else "{}",
                )
                self._repo.insert(cust)
                imported += 1

            self._rebuild_custom_fields()
            self.customer_updated.emit()
            self.refresh()
            extra_msg = ""
            if extra_field_names:
                extra_msg = f"\n\nCustom fields auto-created: {', '.join(extra_field_names)}"
            QMessageBox.information(
                self, "Imported",
                f"Successfully imported {imported} customers from {len(rows)} rows."
                + extra_msg,
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))
