"""
Document Editor Page — the core invoice/quotation creation and editing page.

Handles:
  • Doc type selection + auto-generated number
  • Seller (auto-fill from company_profile) / Buyer (customer picker)
  • Logistics fields (visibility from customization_engine)
  • ItemGrid with live calculation
  • Totals panel, amount-in-words, bank details
  • Save / PDF / Export actions
"""

from __future__ import annotations

import sqlite3
from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget,
)

from models.company import CompanyProfile
from models.customer import Customer
from models.document import Document, DocumentItem
from models.product import Product

from repositories.company_repo import CompanyRepo
from repositories.customer_repo import CustomerRepo
from repositories.document_repo import DocumentRepo
from repositories.product_repo import ProductRepo
from repositories.settings_repo import (
    DocTypeConfigRepo,
    PdfTemplateRepo,
    StateMasterRepo,
    TermsConditionsRepo,
)

from services.calculator import (
    LineResult,
    compute_doc_totals,
    compute_line_item,
    format_currency,
    rupees_to_paise,
)
from services.customization_engine import VisibilityConfig, load_visibility_config
from services.gst_engine import determine_supply_type, extract_state_code_from_gstin
from services.num_to_words import paise_to_words
from services.number_generator import generate_document_number, peek_next_number
from services.validator import validate_gstin

from ui.dialogs.customer_picker import CustomerPickerDialog
from ui.widgets.date_picker import DatePicker
from ui.widgets.gstin_input import GSTINInput
from ui.widgets.item_grid import ItemGrid
from ui.widgets.status_badge import StatusBadge


class DocumentEditor(QWidget):
    """Full-page document editor (invoice / quotation / etc.)."""

    document_saved = pyqtSignal(int)   # emits doc id

    def __init__(
        self,
        conn: sqlite3.Connection,
        doc_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self._doc_id = doc_id
        self._is_edit = doc_id is not None

        # Repositories
        self._doc_repo = DocumentRepo(conn)
        self._company_repo = CompanyRepo(conn)
        self._customer_repo = CustomerRepo(conn)
        self._product_repo = ProductRepo(conn)
        self._doc_type_repo = DocTypeConfigRepo(conn)
        self._template_repo = PdfTemplateRepo(conn)
        self._state_repo = StateMasterRepo(conn)
        self._tc_repo = TermsConditionsRepo(conn)

        # Data
        self._company: CompanyProfile = self._company_repo.get()
        self._products: list[Product] = self._product_repo.list_all()
        self._vis: VisibilityConfig = load_visibility_config(conn)
        self._doc_types = self._doc_type_repo.list_enabled()
        self._states = self._state_repo.list_all()
        self._selected_customer: Customer | None = None

        # Current line results (kept for totals recompute)
        self._line_results: list[LineResult] = []

        self._build_ui()
        self._apply_visibility()
        self._connect_signals()

        if self._is_edit:
            self._load_document(doc_id)
        else:
            self._new_document()

    # ==================================================================
    # Build UI
    # ==================================================================
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # -- Top bar: title + action buttons
        top = QHBoxLayout()
        self._lbl_title = QLabel("NEW DOCUMENT")
        self._lbl_title.setObjectName("heading")
        top.addWidget(self._lbl_title)
        top.addStretch()

        self._status_badge = StatusBadge("draft")
        top.addWidget(self._status_badge)

        self._btn_clear = QPushButton("🧹 Clear")
        self._btn_clear.setProperty("secondary", True)
        self._btn_clear.clicked.connect(self.reset_new)
        top.addWidget(self._btn_clear)

        self._btn_save = QPushButton("💾 Save")
        self._btn_save.clicked.connect(self._save_document)
        top.addWidget(self._btn_save)

        self._btn_pdf = QPushButton("📄 PDF")
        self._btn_pdf.clicked.connect(self._generate_pdf)
        top.addWidget(self._btn_pdf)

        self._btn_print = QPushButton("🖨️ Print")
        self._btn_print.clicked.connect(self._print_document)
        top.addWidget(self._btn_print)

        outer.addLayout(top)

        # -- Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(16, 12, 16, 12)
        self._body_layout.setSpacing(10)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._build_header_section()
        self._build_seller_buyer_section()
        self._build_logistics_section()
        self._build_items_section()
        self._build_totals_section()
        self._build_footer_section()

    # ------------------------------------------------------------------
    # Header: doc type, number, copy type, dates
    # ------------------------------------------------------------------
    def _build_header_section(self) -> None:
        grp = QGroupBox("Document Details")
        layout = QHBoxLayout(grp)
        layout.setSpacing(24)

        # Doc type combo
        form1 = QFormLayout()
        form1.setSpacing(10)
        form1.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._cmb_doc_type = QComboBox()
        for dt in self._doc_types:
            self._cmb_doc_type.addItem(dt["display_name"], dt["code"])
        form1.addRow("Doc Type:", self._cmb_doc_type)

        self._lbl_doc_number = QLineEdit()
        self._lbl_doc_number.setReadOnly(True)
        self._lbl_doc_number.setPlaceholderText("(auto-generated)")
        form1.addRow("Doc No:", self._lbl_doc_number)
        layout.addLayout(form1)

        # Copy type + dates
        form2 = QFormLayout()
        form2.setSpacing(10)
        form2.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._cmb_copy_type = QComboBox()
        self._cmb_copy_type.addItems(self._vis.copy_types)
        form2.addRow("Copy:", self._cmb_copy_type)

        self._dt_doc_date = DatePicker()
        form2.addRow("Date:", self._dt_doc_date)

        self._dt_supply_date = DatePicker()
        form2.addRow("Supply Date:", self._dt_supply_date)
        layout.addLayout(form2)

        self._body_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Seller / Buyer
    # ------------------------------------------------------------------
    def _build_seller_buyer_section(self) -> None:
        row = QHBoxLayout()

        # ---- Seller (read-only, from company_profile) ----
        seller_grp = QGroupBox("SELLER (Your Business)")
        sf = QFormLayout(seller_grp)
        sf.setSpacing(8)
        sf.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._lbl_seller_name = QLabel(self._company.name or "—")
        self._lbl_seller_name.setObjectName("subheading")
        sf.addRow(self._lbl_seller_name)

        self._lbl_seller_addr = QLabel(
            "\n".join(
                filter(None, [self._company.address_line1, self._company.address_line2])
            ) or "—"
        )
        self._lbl_seller_addr.setWordWrap(True)
        sf.addRow("Address:", self._lbl_seller_addr)

        self._lbl_seller_gstin = QLabel(self._company.gstin or "—")
        sf.addRow("GSTIN:", self._lbl_seller_gstin)

        if self._vis.show_cin and self._company.cin:
            sf.addRow("CIN:", QLabel(self._company.cin))

        self._lbl_seller_state = QLabel(
            f"{self._company.state_name} ({self._company.state_code})"
            if self._company.state_code else "—"
        )
        sf.addRow("State:", self._lbl_seller_state)
        row.addWidget(seller_grp)

        # ---- Buyer ----
        buyer_grp = QGroupBox("BUYER (Customer)")
        bf = QFormLayout(buyer_grp)
        bf.setSpacing(8)
        bf.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        # Customer picker button
        pick_row = QHBoxLayout()
        self._txt_customer = QLineEdit()
        self._txt_customer.setReadOnly(True)
        self._txt_customer.setPlaceholderText("Select customer…")
        pick_row.addWidget(self._txt_customer)
        self._btn_pick_customer = QPushButton("🔍")
        self._btn_pick_customer.setFixedWidth(36)
        self._btn_pick_customer.clicked.connect(self._pick_customer)
        pick_row.addWidget(self._btn_pick_customer)
        bf.addRow("Customer:", pick_row)

        self._txt_buyer_name = QLineEdit()
        self._txt_buyer_name.setPlaceholderText("Customer / Company Name")
        bf.addRow("Name:", self._txt_buyer_name)

        self._txt_buyer_addr1 = QLineEdit()
        bf.addRow("Address 1:", self._txt_buyer_addr1)

        self._txt_buyer_addr2 = QLineEdit()
        bf.addRow("Address 2:", self._txt_buyer_addr2)

        self._txt_buyer_addr3 = QLineEdit()
        bf.addRow("Address 3:", self._txt_buyer_addr3)

        self._txt_buyer_gstin = GSTINInput()
        self._txt_buyer_gstin.state_code_detected.connect(self._on_buyer_state_detected)
        bf.addRow("GSTIN:", self._txt_buyer_gstin)

        self._cmb_buyer_state = QComboBox()
        self._cmb_buyer_state.addItem("-- Select State --", "")
        for s in self._states:
            self._cmb_buyer_state.addItem(f"{s.state_name} ({s.code})", s.code)
        bf.addRow("State:", self._cmb_buyer_state)

        self._txt_buyer_pan = QLineEdit()
        self._txt_buyer_pan.setMaxLength(10)
        bf.addRow("PAN:", self._txt_buyer_pan)

        row.addWidget(buyer_grp)
        self._body_layout.addLayout(row)

    # ------------------------------------------------------------------
    # Logistics fields (conditionally shown)
    # ------------------------------------------------------------------
    def _build_logistics_section(self) -> None:
        self._logistics_grp = QGroupBox("Logistics / References")
        form = QFormLayout(self._logistics_grp)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        row1 = QHBoxLayout()

        self._txt_place_of_supply = QComboBox()
        self._txt_place_of_supply.addItem("", "")
        for s in self._states:
            self._txt_place_of_supply.addItem(s.state_name, s.code)
        lbl_pos = QLabel("Place of Supply:")
        self._lbl_place_of_supply = lbl_pos
        row1.addWidget(lbl_pos)
        row1.addWidget(self._txt_place_of_supply)

        self._txt_vehicle_no = QLineEdit()
        self._txt_vehicle_no.setPlaceholderText("Vehicle No")
        self._lbl_vehicle_no = QLabel("Vehicle No:")
        row1.addWidget(self._lbl_vehicle_no)
        row1.addWidget(self._txt_vehicle_no)

        self._txt_gr_lr = QLineEdit()
        self._txt_gr_lr.setPlaceholderText("GR/LR No")
        self._lbl_gr_lr = QLabel("GR/LR No:")
        row1.addWidget(self._lbl_gr_lr)
        row1.addWidget(self._txt_gr_lr)

        form.addRow(row1)

        row2 = QHBoxLayout()

        self._txt_po_no = QLineEdit()
        self._txt_po_no.setPlaceholderText("PO No & Date")
        self._lbl_po_no = QLabel("PO No/Date:")
        row2.addWidget(self._lbl_po_no)
        row2.addWidget(self._txt_po_no)

        self._txt_vendor_code = QLineEdit()
        self._txt_vendor_code.setPlaceholderText("Vendor Code")
        self._lbl_vendor_code = QLabel("Vendor Code:")
        row2.addWidget(self._lbl_vendor_code)
        row2.addWidget(self._txt_vendor_code)

        self._txt_dsr = QLineEdit()
        self._txt_dsr.setPlaceholderText("DSR Number")
        self._lbl_dsr = QLabel("DSR No:")
        row2.addWidget(self._lbl_dsr)
        row2.addWidget(self._txt_dsr)

        form.addRow(row2)

        self._body_layout.addWidget(self._logistics_grp)

    # ------------------------------------------------------------------
    # Items table
    # ------------------------------------------------------------------
    def _build_items_section(self) -> None:
        grp = QGroupBox("Line Items")
        layout = QVBoxLayout(grp)

        self._item_grid = ItemGrid()
        self._item_grid.set_products(self._products)
        self._item_grid.set_column_visibility(
            show_discount=self._vis.show_discount_col,
            show_hsn=self._vis.show_hsn_col,
        )
        layout.addWidget(self._item_grid)

        self._body_layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Totals + Bank
    # ------------------------------------------------------------------
    def _build_totals_section(self) -> None:
        row = QHBoxLayout()

        # Totals
        totals_grp = QGroupBox("Totals")
        totals_grp.setObjectName("totalsPanel")
        tf = QFormLayout(totals_grp)
        tf.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._lbl_taxable = QLabel("₹0.00")
        tf.addRow("Total Taxable:", self._lbl_taxable)

        self._lbl_cgst = QLabel("₹0.00")
        tf.addRow("CGST:", self._lbl_cgst)

        self._lbl_sgst = QLabel("₹0.00")
        tf.addRow("SGST:", self._lbl_sgst)

        self._lbl_igst = QLabel("₹0.00")
        tf.addRow("IGST:", self._lbl_igst)

        self._lbl_grand = QLabel("₹0.00")
        self._lbl_grand.setObjectName("heading")
        tf.addRow("GRAND TOTAL:", self._lbl_grand)

        self._lbl_words = QLabel("—")
        self._lbl_words.setWordWrap(True)
        self._lbl_words.setMinimumHeight(40)
        tf.addRow("In Words:", self._lbl_words)

        row.addWidget(totals_grp, 2)

        # Bank details
        if self._vis.show_bank_details:
            bank_grp = QGroupBox("Bank Details")
            bf = QFormLayout(bank_grp)
            bf.addRow("Bank:", QLabel(self._company.bank_name or "—"))
            bf.addRow("A/C:", QLabel(self._company.account_no or "—"))
            bf.addRow("IFSC:", QLabel(self._company.ifsc_code or "—"))
            bf.addRow("Branch:", QLabel(self._company.bank_branch or "—"))
            bf.addRow("Type:", QLabel(self._company.account_type or "—"))
            row.addWidget(bank_grp, 1)

        self._body_layout.addLayout(row)

    # ------------------------------------------------------------------
    # Footer: Remarks + T&C
    # ------------------------------------------------------------------
    def _build_footer_section(self) -> None:
        form = QFormLayout()
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._txt_remarks = QLineEdit()
        self._txt_remarks.setPlaceholderText("Optional remarks…")
        form.addRow("Remarks:", self._txt_remarks)

        self._txt_tc = QTextEdit()
        self._txt_tc.setMaximumHeight(80)
        self._txt_tc.setPlaceholderText("Terms & Conditions…")
        form.addRow("T&C:", self._txt_tc)

        self._body_layout.addLayout(form)

    # ==================================================================
    # Visibility
    # ==================================================================
    def _apply_visibility(self) -> None:
        vis = self._vis
        # Logistics fields
        self._lbl_vehicle_no.setVisible(vis.show_vehicle_no)
        self._txt_vehicle_no.setVisible(vis.show_vehicle_no)
        self._lbl_gr_lr.setVisible(vis.show_gr_lr_no)
        self._txt_gr_lr.setVisible(vis.show_gr_lr_no)
        self._lbl_po_no.setVisible(vis.show_po_field)
        self._txt_po_no.setVisible(vis.show_po_field)
        self._lbl_vendor_code.setVisible(vis.show_vendor_code)
        self._txt_vendor_code.setVisible(vis.show_vendor_code)
        self._lbl_dsr.setVisible(vis.show_dsr_number)
        self._txt_dsr.setVisible(vis.show_dsr_number)
        self._lbl_place_of_supply.setVisible(vis.show_place_of_supply)
        self._txt_place_of_supply.setVisible(vis.show_place_of_supply)
        self._dt_supply_date.setVisible(vis.show_supply_date)

        # Hide entire logistics group if nothing is visible
        any_logistics = any([
            vis.show_vehicle_no, vis.show_gr_lr_no, vis.show_po_field,
            vis.show_vendor_code, vis.show_dsr_number, vis.show_place_of_supply,
        ])
        self._logistics_grp.setVisible(any_logistics)

    # ==================================================================
    # Signals
    # ==================================================================
    def _connect_signals(self) -> None:
        self._cmb_doc_type.currentIndexChanged.connect(self._on_doc_type_changed)
        self._item_grid.items_changed.connect(self._recalculate)
        self._cmb_buyer_state.currentIndexChanged.connect(
            lambda: self._recalculate()
        )

    # ==================================================================
    # Doc type change
    # ==================================================================
    def _on_doc_type_changed(self) -> None:
        code = self._cmb_doc_type.currentData()
        if not code:
            return
        # Update title
        display = self._cmb_doc_type.currentText()
        prefix = "EDIT" if self._is_edit else "NEW"
        self._lbl_title.setText(f"{prefix} {display.upper()}")

        # Preview next doc number (non-atomic peek)
        dt_cfg = self._doc_type_repo.get(code) or {}
        preview = peek_next_number(
            self.conn,
            code,
            number_format=dt_cfg.get("number_format", "{YYYY}{PREFIX}{NNNN}"),
            prefix=dt_cfg.get("prefix", code),
            padding_digits=dt_cfg.get("padding_digits", 4),
        )
        if not self._is_edit:
            self._lbl_doc_number.setText(preview)

        # Load T&C for this doc type
        tc_text, tc_enabled = self._tc_repo.get_for_type(code)
        if tc_enabled and tc_text:
            self._txt_tc.setPlainText(tc_text)

        self._recalculate()

    # ==================================================================
    # Customer picker
    # ==================================================================
    def _pick_customer(self) -> None:
        dlg = CustomerPickerDialog(self.conn, self)
        if dlg.exec() and dlg.selected_customer:
            self._set_customer(dlg.selected_customer)

    def _set_customer(self, cust: Customer) -> None:
        self._selected_customer = cust
        self._txt_customer.setText(cust.name)
        self._txt_buyer_name.setText(cust.company_name or cust.name)
        self._txt_buyer_addr1.setText(cust.address_line1)
        self._txt_buyer_addr2.setText(cust.address_line2)
        self._txt_buyer_addr3.setText(cust.address_line3)
        self._txt_buyer_gstin.setText(cust.gstin)
        self._txt_buyer_pan.setText(cust.pan)

        # State
        if cust.state_code:
            for i in range(self._cmb_buyer_state.count()):
                if self._cmb_buyer_state.itemData(i) == cust.state_code:
                    self._cmb_buyer_state.setCurrentIndex(i)
                    break
        self._recalculate()

    def _clear_customer(self) -> None:
        self._selected_customer = None
        self._txt_customer.clear()
        self._txt_buyer_name.clear()
        self._txt_buyer_addr1.clear()
        self._txt_buyer_addr2.clear()
        self._txt_buyer_addr3.clear()
        self._txt_buyer_gstin.clear()
        self._txt_buyer_pan.clear()
        self._cmb_buyer_state.setCurrentIndex(0)
        self._recalculate()

    def _on_buyer_state_detected(self, code: str) -> None:
        for i in range(self._cmb_buyer_state.count()):
            if self._cmb_buyer_state.itemData(i) == code:
                self._cmb_buyer_state.setCurrentIndex(i)
                break

    # ==================================================================
    # Live Calculation (Task 2.12)
    # ==================================================================
    def _recalculate(self) -> None:
        """Recompute every line and update totals panel."""
        seller_state = self._company.state_code
        buyer_state = self._cmb_buyer_state.currentData() or ""

        # Default to intra-state (CGST+SGST) when buyer state is unknown
        if not buyer_state:
            is_intra = True
        else:
            is_intra = determine_supply_type(seller_state, buyer_state)

        self._line_results.clear()
        grid = self._item_grid

        for row in range(grid.row_count()):
            data = grid.get_row_data(row)
            gst_rate = grid._get_gst_rate_for_category(data["category"])
            rate_paise = rupees_to_paise(data["rate_rupees"])

            lr = compute_line_item(
                quantity=data["qty"],
                rate_paise=rate_paise,
                discount_pct=data["discount_pct"],
                gst_rate=gst_rate,
                is_intra_state=is_intra,
            )
            self._line_results.append(lr)

            # Push computed values back into grid
            grid.set_computed_values(
                row,
                taxable=format_currency(lr.taxable_amount),
                cgst_rate=lr.cgst_rate,
                cgst_amt=format_currency(lr.cgst_amount),
                sgst_rate=lr.sgst_rate,
                sgst_amt=format_currency(lr.sgst_amount),
                igst_rate=lr.igst_rate,
                igst_amt=format_currency(lr.igst_amount),
                total=format_currency(lr.line_total),
            )

        # Document totals
        if self._line_results:
            totals = compute_doc_totals(self._line_results)
            self._lbl_taxable.setText(format_currency(totals.total_taxable))
            self._lbl_cgst.setText(format_currency(totals.total_cgst))
            self._lbl_sgst.setText(format_currency(totals.total_sgst))
            self._lbl_igst.setText(format_currency(totals.total_igst))
            self._lbl_grand.setText(format_currency(totals.grand_total))
            self._lbl_words.setText(paise_to_words(totals.grand_total))
        else:
            for lbl in (
                self._lbl_taxable, self._lbl_cgst, self._lbl_sgst,
                self._lbl_igst, self._lbl_grand,
            ):
                lbl.setText("₹0.00")
            self._lbl_words.setText("—")

    # ==================================================================
    # New / Load
    # ==================================================================
    def _new_document(self) -> None:
        """Initialise UI for a brand-new document."""
        self._cmb_doc_type.setCurrentIndex(0)
        self._on_doc_type_changed()
        # Start with 7 blank rows for quick entry
        for _ in range(7):
            self._item_grid.add_row()

    def _load_document(self, doc_id: int) -> None:
        """Load an existing document for editing."""
        doc = self._doc_repo.get_with_items(doc_id)
        if doc is None:
            QMessageBox.warning(self, "Error", f"Document #{doc_id} not found.")
            return

        self._doc_id = doc.id
        self._lbl_title.setText(f"EDIT {doc.document_type}")
        self._status_badge.set_status(doc.status)

        # Doc type
        idx = self._cmb_doc_type.findData(doc.document_type)
        if idx >= 0:
            self._cmb_doc_type.setCurrentIndex(idx)

        self._lbl_doc_number.setText(doc.document_number)

        # Copy type
        ci = self._cmb_copy_type.findText(doc.copy_type, Qt.MatchFlag.MatchFixedString)
        if ci >= 0:
            self._cmb_copy_type.setCurrentIndex(ci)

        # Dates
        self._dt_doc_date.set_date(doc.document_date)
        if doc.supply_date:
            self._dt_supply_date.set_date(doc.supply_date)

        # Buyer
        self._txt_buyer_name.setText(doc.customer_name)
        self._txt_buyer_addr1.setText(doc.buyer_address1)
        self._txt_buyer_addr2.setText(doc.buyer_address2)
        self._txt_buyer_addr3.setText(doc.buyer_address3)
        self._txt_buyer_gstin.setText(doc.customer_gstin)
        self._txt_buyer_pan.setText(doc.buyer_pan)
        if doc.buyer_state_code:
            for i in range(self._cmb_buyer_state.count()):
                if self._cmb_buyer_state.itemData(i) == doc.buyer_state_code:
                    self._cmb_buyer_state.setCurrentIndex(i)
                    break
        if doc.customer_id:
            cust = self._customer_repo.get_by_id(doc.customer_id)
            if cust:
                self._selected_customer = cust
                self._txt_customer.setText(cust.name)

        # Logistics
        self._txt_vehicle_no.setText(doc.vehicle_no)
        self._txt_gr_lr.setText(doc.gr_lr_no)
        self._txt_po_no.setText(doc.po_no_date)
        self._txt_vendor_code.setText(doc.vendor_code)
        self._txt_dsr.setText(doc.dsr_number)
        if doc.place_of_supply:
            for i in range(self._txt_place_of_supply.count()):
                if self._txt_place_of_supply.itemData(i) == doc.place_of_supply:
                    self._txt_place_of_supply.setCurrentIndex(i)
                    break

        # Remarks & T&C
        self._txt_remarks.setText(doc.remarks)
        # T&C already loaded by doc type; override if doc had specific remarks

        # Items
        self._item_grid.load_items(doc.items)
        self._recalculate()

    # ==================================================================
    # Save
    # ==================================================================
    def _save_document(self) -> None:
        """Collect form data, build Document + items, persist."""
        doc_type = self._cmb_doc_type.currentData()
        if not doc_type:
            QMessageBox.warning(self, "Error", "Select a document type.")
            return

        buyer_name = self._txt_buyer_name.text().strip()

        # Generate real doc number for new documents
        if not self._is_edit:
            dt_cfg = self._doc_type_repo.get(doc_type) or {}
            doc_number = generate_document_number(
                self.conn,
                doc_type,
                number_format=dt_cfg.get("number_format", "{YYYY}{PREFIX}{NNNN}"),
                prefix=dt_cfg.get("prefix", doc_type),
                padding_digits=dt_cfg.get("padding_digits", 4),
                financial_year_start=self._company.financial_year_start,
            )
        else:
            doc_number = self._lbl_doc_number.text()

        buyer_state_code = self._cmb_buyer_state.currentData() or ""
        buyer_state_name = ""
        for s in self._states:
            if s.code == buyer_state_code:
                buyer_state_name = s.state_name
                break

        seller_state = self._company.state_code
        is_intra = determine_supply_type(seller_state, buyer_state_code)

        # Build line items
        items: list[DocumentItem] = []
        line_results: list[LineResult] = []

        for row in range(self._item_grid.row_count()):
            rd = self._item_grid.get_row_data(row)
            gst_rate = self._item_grid._get_gst_rate_for_category(rd["category"])
            rate_paise = rupees_to_paise(rd["rate_rupees"])

            lr = compute_line_item(
                quantity=rd["qty"],
                rate_paise=rate_paise,
                discount_pct=rd["discount_pct"],
                gst_rate=gst_rate,
                is_intra_state=is_intra,
            )
            line_results.append(lr)

            items.append(DocumentItem(
                category_name=rd["category"],
                item_name=rd["item_name"],
                hsn_code=rd["hsn"],
                quantity=rd["qty"],
                rate=rate_paise,
                discount_pct=rd["discount_pct"],
                taxable_amount=lr.taxable_amount,
                cgst_rate=lr.cgst_rate,
                cgst_amount=lr.cgst_amount,
                sgst_rate=lr.sgst_rate,
                sgst_amount=lr.sgst_amount,
                igst_rate=lr.igst_rate,
                igst_amount=lr.igst_amount,
            ))

        totals = compute_doc_totals(line_results) if line_results else None

        doc = Document(
            id=self._doc_id,
            document_number=doc_number,
            document_type=doc_type,
            document_date=self._dt_doc_date.iso_date(),
            supply_date=self._dt_supply_date.iso_date(),
            customer_id=self._selected_customer.id if self._selected_customer else None,
            customer_name=buyer_name,
            customer_gstin=self._txt_buyer_gstin.text().strip().upper(),
            buyer_address1=self._txt_buyer_addr1.text().strip(),
            buyer_address2=self._txt_buyer_addr2.text().strip(),
            buyer_address3=self._txt_buyer_addr3.text().strip(),
            buyer_state_code=buyer_state_code,
            buyer_state_name=buyer_state_name,
            buyer_pan=self._txt_buyer_pan.text().strip().upper(),
            vehicle_no=self._txt_vehicle_no.text().strip(),
            gr_lr_no=self._txt_gr_lr.text().strip(),
            place_of_supply=self._txt_place_of_supply.currentData() or "",
            po_no_date=self._txt_po_no.text().strip(),
            vendor_code=self._txt_vendor_code.text().strip(),
            dsr_number=self._txt_dsr.text().strip(),
            total_taxable=totals.total_taxable if totals else 0,
            total_cgst=totals.total_cgst if totals else 0,
            total_sgst=totals.total_sgst if totals else 0,
            total_igst=totals.total_igst if totals else 0,
            grand_total=totals.grand_total if totals else 0,
            amount_in_words=paise_to_words(totals.grand_total) if totals else "",
            copy_type=self._cmb_copy_type.currentText(),
            remarks=self._txt_remarks.text().strip(),
            status="saved",
            items=items,
        )

        try:
            saved_id = self._doc_repo.save_with_items(doc)
            self._doc_id = saved_id
            self._is_edit = True
            self._lbl_doc_number.setText(doc_number)
            self._status_badge.set_status("saved")
            self._lbl_title.setText(
                f"EDIT {self._cmb_doc_type.currentText().upper()}"
            )
            self.document_saved.emit(saved_id)
            QMessageBox.information(
                self, "Saved",
                f"Document {doc_number} saved successfully.",
            )
            # Prompt to generate PDF
            pdf_reply = QMessageBox.question(
                self, "Generate PDF?",
                f"Document {doc_number} saved.\n\nWould you like to generate a PDF?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if pdf_reply == QMessageBox.StandardButton.Yes:
                self._generate_pdf()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    # ==================================================================
    # Public API for MainWindow
    # ==================================================================
    def load_for_edit(self, doc_id: int) -> None:
        """Reset the editor and load a document by ID."""
        self._doc_id = doc_id
        self._is_edit = True
        self._item_grid.clear_all()
        self._load_document(doc_id)

    def reset_new(self) -> None:
        """Reset the editor for creating a new document."""
        self._doc_id = None
        self._is_edit = False
        self._selected_customer = None
        self._item_grid.clear_all()
        self._clear_customer()
        self._txt_buyer_addr3.clear()
        self._txt_vehicle_no.clear()
        self._txt_gr_lr.clear()
        self._txt_po_no.clear()
        self._txt_vendor_code.clear()
        self._txt_dsr.clear()
        self._txt_remarks.clear()
        self._status_badge.set_status("draft")
        self._new_document()

    def _generate_pdf(self) -> None:
        """Generate a PDF for the current saved document."""
        if not self._doc_id:
            QMessageBox.warning(
                self, "Save First",
                "Please save the document before generating a PDF.",
            )
            return

        # Load the saved document with items
        doc = self._doc_repo.get_with_items(self._doc_id)
        if not doc:
            QMessageBox.warning(self, "Error", "Could not load saved document.")
            return

        # Determine default save path
        from repositories.settings_repo import AppSettingsRepo
        settings = AppSettingsRepo(self.conn)
        default_dir = settings.get("pdf_save_path", "")
        if not default_dir:
            from config import DATA_DIR
            default_dir = str(DATA_DIR)

        import os
        default_name = f"{doc.document_number.replace('/', '-')}.pdf"
        default_path = os.path.join(default_dir, default_name)

        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", default_path,
            "PDF Files (*.pdf)",
        )
        if not path:
            return

        try:
            from services.pdf_generator import generate_invoice_pdf

            # Get T&C for this doc type
            tc_text, tc_enabled = self._tc_repo.get_for_type(doc.document_type)

            generate_invoice_pdf(
                doc=doc,
                company=self._company,
                output_path=path,
                bank_details=self._vis.show_bank_details,
                terms_text=tc_text if tc_enabled else "",
                copy_label=doc.copy_type,
            )

            # Remember the folder for next time
            settings.set("pdf_save_path", os.path.dirname(path))

            QMessageBox.information(
                self, "PDF Generated",
                f"PDF saved to:\n{path}",
            )

            # Try to open the PDF
            import subprocess, sys
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            elif sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])

        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed to generate PDF:\n{e}")

    def _print_document(self) -> None:
        """Print the document by generating a temporary PDF and sending to printer."""
        if not self._doc_id:
            QMessageBox.warning(
                self, "Save First",
                "Please save the document before printing.",
            )
            return

        import tempfile, os, subprocess, sys
        doc = self._doc_repo.get_with_items(self._doc_id)
        if not doc:
            QMessageBox.warning(self, "Error", "Could not load saved document.")
            return

        try:
            from services.pdf_generator import generate_invoice_pdf

            tc_text, tc_enabled = self._tc_repo.get_for_type(doc.document_type)
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", prefix=f"{doc.document_number}_",
                delete=False,
            )
            tmp_path = tmp.name
            tmp.close()

            generate_invoice_pdf(
                doc=doc,
                company=self._company,
                output_path=tmp_path,
                bank_details=self._vis.show_bank_details,
                terms_text=tc_text if tc_enabled else "",
                copy_label=doc.copy_type,
            )

            # Open PDF for printing
            if sys.platform == "darwin":
                subprocess.Popen(["open", tmp_path])
            elif sys.platform == "win32":
                os.startfile(tmp_path, "print")
            else:
                subprocess.Popen(["xdg-open", tmp_path])

        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to print:\n{e}")
