"""
Product Manager Page — full CRUD for products (category / HSN / GST rate / default rate).

Includes Excel export and import.
"""

from __future__ import annotations

import json
import sqlite3

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from models.product import Product
from repositories.custom_field_repo import CustomFieldRepo
from repositories.product_repo import ProductRepo
from services.calculator import format_currency, paise_to_rupees, rupees_to_paise
from services.excel_io import (
    PRODUCT_ALIASES, build_column_map, dataclass_list_to_dicts,
    export_to_excel, get_sheet_names, import_from_excel, remap_row,
)
from services.validator import validate_hsn
from ui.widgets.custom_fields import (
    ManageFieldsDialog, build_custom_inputs, load_custom_inputs,
    read_custom_inputs,
)
from ui.widgets.search_bar import SearchBar


class ProductManagerPage(QWidget):
    """Master-detail CRUD for products."""

    product_updated = pyqtSignal()

    def __init__(self, conn: sqlite3.Connection, parent: QWidget | None = None):
        super().__init__(parent)
        self.conn = conn
        self._repo = ProductRepo(conn)
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

        # ── Top row
        hdr = QHBoxLayout()
        title = QLabel("Products & Services")
        title.setObjectName("heading")
        hdr.addWidget(title)
        hdr.addStretch()

        self._search = SearchBar("Search products…")
        self._search.search_changed.connect(lambda _: self.refresh())
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

        # ── Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter, 1)

        # Left: table
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Category / Name", "HSN / SAC", "GST %", "Rate (₹)", "ID"])
        self._table.setColumnHidden(4, True)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setMinimumSectionSize(70)
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

        grp = QGroupBox("Product / Service Details")
        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(16, 18, 16, 14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._inp_category = QLineEdit()
        self._inp_category.setPlaceholderText("e.g. IT Consulting, Web Design")
        form.addRow("Category / Name *", self._inp_category)

        self._inp_hsn = QLineEdit()
        self._inp_hsn.setPlaceholderText("4 or 6 digit HSN/SAC")
        self._lbl_hsn = QLabel("HSN / SAC Code")
        form.addRow(self._lbl_hsn, self._inp_hsn)

        self._inp_gst = QDoubleSpinBox()
        self._inp_gst.setRange(0, 28)
        self._inp_gst.setDecimals(1)
        self._inp_gst.setValue(18.0)
        self._inp_gst.setSuffix(" %")
        self._lbl_gst = QLabel("GST Rate")
        form.addRow(self._lbl_gst, self._inp_gst)

        self._inp_rate = QDoubleSpinBox()
        self._inp_rate.setRange(0, 99_99_999.99)
        self._inp_rate.setDecimals(2)
        self._inp_rate.setPrefix("₹ ")
        self._lbl_rate = QLabel("Default Rate")
        form.addRow(self._lbl_rate, self._inp_rate)

        # Map built-in field_name → (label_widget, input_widget)
        self._builtin_widgets: dict[str, tuple[QWidget, QWidget]] = {
            "hsn_code":     (self._lbl_hsn, self._inp_hsn),
            "gst_rate":     (self._lbl_gst, self._inp_gst),
            "default_rate": (self._lbl_rate, self._inp_rate),
        }

        # Dynamic custom fields
        self._detail_form = form
        self._custom_inputs: dict[str, QLineEdit] = {}
        self._rebuild_custom_fields()
        self._sync_builtin_visibility()

        grp.setLayout(form)
        rl.addWidget(grp)

        btns = QHBoxLayout()
        self._btn_new = QPushButton("➕ New")
        self._btn_new.clicked.connect(self._new_product)
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
        splitter.setSizes([500, 350])

    # ==================================================================
    # Data
    # ==================================================================
    def refresh(self) -> None:
        q = self._search.text().strip()
        prods = self._repo.search(q) if q else self._repo.list_all(active_only=True)
        self._table.setRowCount(0)
        for p in prods:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(p.category_name))
            self._table.setItem(row, 1, QTableWidgetItem(p.hsn_code or ""))
            gst = QTableWidgetItem(f"{p.gst_rate:.1f}")
            gst.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 2, gst)
            rate = QTableWidgetItem(format_currency(p.default_rate))
            rate.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 3, rate)
            self._table.setItem(row, 4, QTableWidgetItem(str(p.id)))

    def _on_row_changed(self, row: int, _col: int, _prev_row: int, _prev_col: int) -> None:
        if row < 0:
            return
        item = self._table.item(row, 4)
        if not item:
            return
        pid = int(item.text())
        prod = self._repo.get_by_id(pid)
        if prod:
            self._load_into_form(prod)

    def _load_into_form(self, p: Product) -> None:
        self._editing_id = p.id
        self._inp_category.setText(p.category_name)
        self._inp_hsn.setText(p.hsn_code or "")
        self._inp_gst.setValue(p.gst_rate)
        self._inp_rate.setValue(float(paise_to_rupees(p.default_rate)))
        load_custom_inputs(self._custom_inputs, p.custom_fields)

    # ==================================================================
    # CRUD
    # ==================================================================
    def _new_product(self) -> None:
        self._editing_id = None
        self._inp_category.clear()
        self._inp_hsn.clear()
        self._inp_gst.setValue(18.0)
        self._inp_rate.setValue(0)
        for w in self._custom_inputs.values():
            w.clear()

    def _save(self) -> None:
        cat = self._inp_category.text().strip()
        if not cat:
            QMessageBox.warning(self, "Required", "Category / Name is required.")
            return

        # Only validate HSN if the field is visible
        hsn = self._inp_hsn.text().strip() if self._inp_hsn.isVisible() else ""
        if hsn:
            ok, msg = validate_hsn(hsn)
            if not ok:
                QMessageBox.warning(self, "Invalid HSN", msg)
                return

        prod = Product(
            id=self._editing_id,
            category_name=cat,
            hsn_code=hsn or None,
            gst_rate=self._inp_gst.value() if self._inp_gst.isVisible() else 18.0,
            default_rate=rupees_to_paise(self._inp_rate.value()) if self._inp_rate.isVisible() else 0,
            custom_fields=read_custom_inputs(self._custom_inputs),
        )

        if self._editing_id:
            self._repo.update(prod)
        else:
            new_id = self._repo.insert(prod)
            self._editing_id = new_id

        self.product_updated.emit()
        self.refresh()
        QMessageBox.information(self, "Saved", f"Product '{cat}' saved.")

    def _deactivate(self) -> None:
        if not self._editing_id:
            QMessageBox.information(self, "Select", "Select a product first.")
            return
        reply = QMessageBox.warning(
            self, "Remove",
            "Remove this product? It won't appear in lookups.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._repo.soft_delete(self._editing_id)
            self._new_product()
            self.product_updated.emit()
            self.refresh()

    # ==================================================================
    # Custom Fields
    # ==================================================================
    def _sync_builtin_visibility(self) -> None:
        """Show/hide built-in form rows based on active_builtin_names."""
        cf_repo = CustomFieldRepo(self.conn)
        active = cf_repo.active_builtin_names("product")
        for fname, (lbl, inp) in self._builtin_widgets.items():
            visible = fname in active
            lbl.setVisible(visible)
            inp.setVisible(visible)

    def _rebuild_custom_fields(self) -> None:
        """Remove old custom field rows from the form and re-create them."""
        # Remove existing custom input rows
        for widget in self._custom_inputs.values():
            idx = self._detail_form.indexOf(widget)
            if idx >= 0:
                row, _ = self._detail_form.getWidgetPosition(widget)
                if row >= 0:
                    self._detail_form.removeRow(row)
        self._custom_inputs = build_custom_inputs(
            self.conn, "product", self._detail_form,
        )

    def _manage_fields(self) -> None:
        """Open the Manage Fields dialog then rebuild the form."""
        dlg = ManageFieldsDialog(
            self.conn, "product", "Product", parent=self,
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
            self, "Export Sample Import File", "product_import_sample.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        sample = [{
            "category_name": "Example Product",
            "hsn_code": "9983",
            "gst_rate": 18.0,
            "default_rate": 1000.00,
        }]
        export_to_excel(
            sample, path,
            sheet_name="Products",
            title="Product Import Sample",
            money_columns=("default_rate",),
        )
        QMessageBox.information(
            self, "Sample Exported",
            f"Sample import file saved to:\n{path}\n\n"
            "Fill in your data following this template and use 'Import from Excel' to load it.",
        )

    def _export_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Products to Excel", "products.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        prods = self._repo.list_all(active_only=False)
        rows = dataclass_list_to_dicts(prods, exclude_fields=("created_at", "custom_fields"))
        # Merge custom_fields JSON into flat columns
        for prod, row_dict in zip(prods, rows):
            try:
                cf = json.loads(prod.custom_fields) if prod.custom_fields else {}
            except (json.JSONDecodeError, TypeError):
                cf = {}
            row_dict.update(cf)
        export_to_excel(
            rows, path,
            sheet_name="Products",
            title="Product Master",
            money_columns=("default_rate",),
        )
        QMessageBox.information(self, "Exported", f"Exported {len(rows)} products.")

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Products from Excel", "",
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
                raw_headers, PRODUCT_ALIASES,
                required_fields=["category_name"],
            )
            if col_map.missing_required:
                QMessageBox.warning(
                    self, "Missing Columns",
                    "Could not find required column(s):\n"
                    + ", ".join(col_map.missing_required)
                    + "\n\nAccepted names for Category: "
                    + ", ".join(PRODUCT_ALIASES["category_name"])
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
                if fname and fname not in ("id", "is_active", "created_at"):
                    cf_repo.ensure_field("product", fname, orig)
                    extra_field_names.append(fname)

            imported = 0
            for r in rows:
                mapped = remap_row(r, col_map)
                cat = str(mapped.get("category_name", "")).strip()
                if not cat:
                    continue

                # Rate — smart detection: paise vs rupees
                raw_rate = mapped.get("default_rate", 0) or 0
                try:
                    rate_val = float(raw_rate)
                except (ValueError, TypeError):
                    rate_val = 0.0
                # If the value looks like rupees (has decimals or < 100), convert
                if 0 < rate_val < 100_000:
                    rate_paise = rupees_to_paise(rate_val)
                else:
                    rate_paise = int(rate_val)

                gst = 18.0
                raw_gst = mapped.get("gst_rate")
                if raw_gst is not None and raw_gst != "":
                    try:
                        gst = float(raw_gst)
                    except (ValueError, TypeError):
                        pass

                # Collect extra column values into custom_fields JSON
                cf_data: dict = {}
                for orig in col_map.unmapped:
                    fname = CustomFieldRepo.to_field_name(orig)
                    snake_key = CustomFieldRepo.to_field_name(orig)
                    if fname and snake_key in r:
                        val = r[snake_key]
                        if val is not None and str(val).strip():
                            cf_data[fname] = val

                prod = Product(
                    category_name=cat,
                    hsn_code=str(mapped.get("hsn_code", "")).strip() or None,
                    gst_rate=gst,
                    default_rate=rate_paise,
                    custom_fields=json.dumps(cf_data, ensure_ascii=False) if cf_data else "{}",
                )
                self._repo.insert(prod)
                imported += 1

            # Rebuild form to show any new custom fields
            self._rebuild_custom_fields()
            self.product_updated.emit()
            self.refresh()
            extra_msg = ""
            if extra_field_names:
                extra_msg = f"\n\nCustom fields auto-created: {', '.join(extra_field_names)}"
            QMessageBox.information(
                self, "Imported",
                f"Successfully imported {imported} products from {len(rows)} rows."
                + extra_msg,
            )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))
