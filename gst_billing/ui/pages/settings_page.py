"""
Full Settings Page — 7 tabbed sections covering all application configuration.

Tabs: Company Profile | Bank Details | Terms & Conditions | Document Types |
      Invoice Layout | Theme | Data & Backup (incl. Factory Reset)
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QAbstractItemView, QColorDialog,
)

from config import DATA_DIR, BACKUP_DIR, ASSETS_DIR
from models.company import CompanyProfile
from repositories.company_repo import CompanyRepo
from repositories.settings_repo import (
    AppSettingsRepo, DocTypeConfigRepo, PdfTemplateRepo,
    PurchaseCategoryRepo, StateMasterRepo, TermsConditionsRepo,
)
from services.validator import (
    validate_gstin, validate_pan, validate_email, validate_ifsc, validate_mobile,
)


class SettingsPage(QWidget):
    """Full settings page with 7 tabs."""

    reset_requested = pyqtSignal()

    def __init__(self, conn: sqlite3.Connection | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conn = conn
        self._build_ui()
        if conn:
            self._load_all()

    # ==================================================================
    # Build
    # ==================================================================
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 8)

        hdr = QHBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("heading")
        hdr.addWidget(title)
        hdr.addStretch()
        outer.addLayout(hdr)

        self._tabs = QTabWidget()
        # Ensure tab labels show full text without truncation
        self._tabs.setUsesScrollButtons(False)
        self._tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self._tabs.setStyleSheet(
            "QTabBar::tab { min-width: 100px; padding: 6px 14px; }"
        )
        outer.addWidget(self._tabs, 1)

        self._build_company_tab()
        self._build_bank_tab()
        self._build_tc_tab()
        self._build_doc_types_tab()
        self._build_layout_tab()
        self._build_theme_tab()
        self._build_data_tab()

    # ── Tab 1: Company Profile ────────────────────────────────────
    def _build_company_tab(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._c_name = QLineEdit()
        self._c_name.setMinimumWidth(300)
        form.addRow("Business Name *", self._c_name)
        self._c_gstin = QLineEdit()
        self._c_gstin.setPlaceholderText("15-char GSTIN")
        form.addRow("GSTIN", self._c_gstin)
        self._c_pan = QLineEdit()
        form.addRow("PAN", self._c_pan)
        self._c_cin = QLineEdit()
        form.addRow("CIN (optional)", self._c_cin)
        self._c_addr1 = QLineEdit()
        form.addRow("Address Line 1", self._c_addr1)
        self._c_addr2 = QLineEdit()
        form.addRow("Address Line 2", self._c_addr2)
        self._c_phone = QLineEdit()
        form.addRow("Phone", self._c_phone)
        self._c_email = QLineEdit()
        form.addRow("Email", self._c_email)
        self._c_website = QLineEdit()
        form.addRow("Website", self._c_website)

        # State picker
        self._c_state = QComboBox()
        self._c_state.addItem("-- Select State --", "")
        form.addRow("State", self._c_state)

        self._c_sig_label = QLineEdit()
        self._c_sig_label.setPlaceholderText("Authorised Signatory")
        form.addRow("Signature Label", self._c_sig_label)

        self._c_currency = QLineEdit()
        self._c_currency.setMaximumWidth(60)
        form.addRow("Currency Symbol", self._c_currency)

        self._c_fy_start = QComboBox()
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        for i, m in enumerate(months, 1):
            self._c_fy_start.addItem(m, i)
        form.addRow("Financial Year Starts", self._c_fy_start)

        # Logo / stamp
        logo_row = QHBoxLayout()
        self._c_logo_path = QLineEdit()
        self._c_logo_path.setReadOnly(True)
        self._c_logo_path.setPlaceholderText("No logo selected")
        logo_row.addWidget(self._c_logo_path, 1)
        btn_logo = QPushButton("Browse…")
        btn_logo.setProperty("secondary", True)
        btn_logo.clicked.connect(lambda: self._browse_image(self._c_logo_path))
        logo_row.addWidget(btn_logo)
        form.addRow("Company Logo", logo_row)

        stamp_row = QHBoxLayout()
        self._c_stamp_path = QLineEdit()
        self._c_stamp_path.setReadOnly(True)
        self._c_stamp_path.setPlaceholderText("No stamp/seal selected")
        stamp_row.addWidget(self._c_stamp_path, 1)
        btn_stamp = QPushButton("Browse…")
        btn_stamp.setProperty("secondary", True)
        btn_stamp.clicked.connect(lambda: self._browse_image(self._c_stamp_path))
        stamp_row.addWidget(btn_stamp)
        form.addRow("Stamp / Seal", stamp_row)

        btn_save = QPushButton("💾  Save Company Profile")
        btn_save.clicked.connect(self._save_company)
        form.addRow("", btn_save)

        scroll.setWidget(w)
        self._tabs.addTab(scroll, "Company Profile")

    # ── Tab 2: Bank Details ───────────────────────────────────────
    def _build_bank_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._b_bank = QLineEdit()
        form.addRow("Bank Name", self._b_bank)
        self._b_branch = QLineEdit()
        form.addRow("Branch", self._b_branch)
        self._b_acno = QLineEdit()
        form.addRow("Account No", self._b_acno)
        self._b_type = QComboBox()
        self._b_type.addItems(["Current", "Savings"])
        form.addRow("Account Type", self._b_type)
        self._b_ifsc = QLineEdit()
        self._b_ifsc.setPlaceholderText("e.g. SBIN0001234")
        form.addRow("IFSC Code", self._b_ifsc)

        btn_save = QPushButton("💾  Save Bank Details")
        btn_save.clicked.connect(self._save_bank)
        form.addRow("", btn_save)

        self._tabs.addTab(w, "Bank Details")

    # ── Tab 3: Terms & Conditions ─────────────────────────────────
    def _build_tc_tab(self) -> None:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(QLabel("Document Type:"))
        self._tc_type = QComboBox()
        top.addWidget(self._tc_type, 1)
        top.addStretch()
        layout.addLayout(top)

        self._tc_edit = QPlainTextEdit()
        self._tc_edit.setPlaceholderText("Enter terms & conditions (one per line)…")
        layout.addWidget(self._tc_edit, 1)

        self._tc_enabled = QCheckBox("Enable T&C on this document type")
        self._tc_enabled.setChecked(True)
        layout.addWidget(self._tc_enabled)

        btns = QHBoxLayout()
        btn_save = QPushButton("💾  Save for This Type")
        btn_save.clicked.connect(self._save_tc)
        btns.addWidget(btn_save)

        btn_copy = QPushButton("Copy to All Types")
        btn_copy.setProperty("secondary", True)
        btn_copy.clicked.connect(self._copy_tc_all)
        btns.addWidget(btn_copy)
        btns.addStretch()
        layout.addLayout(btns)

        self._tc_type.currentIndexChanged.connect(self._load_tc_for_current)

        self._tabs.addTab(w, "Terms & Conditions")

    # ── Tab 4: Document Types ─────────────────────────────────────
    def _build_doc_types_tab(self) -> None:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self._dt_table = QTableWidget()
        self._dt_table.setColumnCount(6)
        self._dt_table.setHorizontalHeaderLabels([
            "Code", "Display Name", "Prefix", "Number Format", "Padding", "Active",
        ])
        h = self._dt_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setMinimumSectionSize(60)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._dt_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._dt_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked
        )
        self._dt_table.setAlternatingRowColors(True)
        self._dt_table.verticalHeader().setVisible(False)
        self._dt_table.verticalHeader().setDefaultSectionSize(38)
        self._dt_table.setShowGrid(False)
        layout.addWidget(self._dt_table, 1)

        info = QLabel(
            "Format tokens: {YYYY} {YY} {FY} {PREFIX} {NNNN} {N2}–{N7} {MM}"
        )
        info.setObjectName("subheading")
        info.setWordWrap(True)
        layout.addWidget(info)

        btns = QHBoxLayout()
        btn_save = QPushButton("💾  Save Changes")
        btn_save.clicked.connect(self._save_doc_types)
        btns.addWidget(btn_save)
        btns.addStretch()
        layout.addLayout(btns)

        self._tabs.addTab(w, "Document Types")

    # ── Tab 5: Invoice Layout ─────────────────────────────────────
    def _build_layout_tab(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header settings
        g1 = QGroupBox("Header Settings")
        f1 = QFormLayout(g1)
        self._l_show_logo = QCheckBox("Show Logo")
        self._l_show_logo.setChecked(True)
        f1.addRow(self._l_show_logo)
        self._l_logo_pos = QComboBox()
        self._l_logo_pos.addItems(["left", "center", "right"])
        f1.addRow("Logo Position", self._l_logo_pos)
        self._l_logo_width = QDoubleSpinBox()
        self._l_logo_width.setRange(10, 60)
        self._l_logo_width.setValue(25)
        self._l_logo_width.setSuffix(" mm")
        f1.addRow("Logo Width", self._l_logo_width)
        self._l_show_cin = QCheckBox("Show CIN")
        self._l_show_cin.setChecked(True)
        f1.addRow(self._l_show_cin)
        self._l_show_website = QCheckBox("Show Website")
        self._l_show_website.setChecked(True)
        f1.addRow(self._l_show_website)
        self._l_show_stamp = QCheckBox("Show Stamp / Seal")
        self._l_show_stamp.setChecked(True)
        f1.addRow(self._l_show_stamp)

        self._l_header_color = QLineEdit("#000000")
        self._l_header_color.setMaximumWidth(100)
        color_row = QHBoxLayout()
        color_row.addWidget(self._l_header_color)
        btn_pick = QPushButton("Pick…")
        btn_pick.setProperty("secondary", True)
        btn_pick.setMaximumWidth(60)
        btn_pick.clicked.connect(self._pick_header_color)
        color_row.addWidget(btn_pick)
        color_row.addStretch()
        f1.addRow("Header Color", color_row)
        layout.addWidget(g1)

        # Field visibility
        g2 = QGroupBox("Document Field Visibility")
        g2l = QVBoxLayout(g2)
        self._vis_checks: dict[str, QCheckBox] = {}
        vis_fields = [
            ("show_vehicle_no", "Vehicle Number"),
            ("show_gr_lr_no", "GR / LR Number"),
            ("show_po_field", "PO No & Date"),
            ("show_vendor_code", "Vendor Code"),
            ("show_dsr_number", "DSR Number"),
            ("show_supply_date", "Supply Date"),
            ("show_place_of_supply", "Place of Supply"),
        ]
        row_l = QHBoxLayout()
        for i, (key, label) in enumerate(vis_fields):
            cb = QCheckBox(label)
            cb.setChecked(True)
            self._vis_checks[key] = cb
            row_l.addWidget(cb)
            if (i + 1) % 3 == 0:
                g2l.addLayout(row_l)
                row_l = QHBoxLayout()
        if row_l.count():
            g2l.addLayout(row_l)
        layout.addWidget(g2)

        # Item table columns
        g3 = QGroupBox("Item Table Columns")
        g3l = QHBoxLayout(g3)
        self._l_show_discount = QCheckBox("Discount %")
        self._l_show_discount.setChecked(True)
        g3l.addWidget(self._l_show_discount)
        self._l_show_hsn = QCheckBox("HSN / SAC Code")
        self._l_show_hsn.setChecked(True)
        g3l.addWidget(self._l_show_hsn)
        g3l.addStretch()
        layout.addWidget(g3)

        # Footer settings
        g4 = QGroupBox("Footer Settings")
        f4 = QFormLayout(g4)
        self._l_show_bank = QCheckBox("Show Bank Details")
        self._l_show_bank.setChecked(True)
        f4.addRow(self._l_show_bank)
        self._l_show_words = QCheckBox("Amount in Words")
        self._l_show_words.setChecked(True)
        f4.addRow(self._l_show_words)
        self._l_show_tc = QCheckBox("Show Terms & Conditions")
        self._l_show_tc.setChecked(True)
        f4.addRow(self._l_show_tc)
        self._l_footer_note = QLineEdit()
        self._l_footer_note.setPlaceholderText("This is a Computer Generated Invoice")
        f4.addRow("Footer Note", self._l_footer_note)
        layout.addWidget(g4)

        # Copy types
        g5 = QGroupBox("Copy Types (printed on each page)")
        g5l = QVBoxLayout(g5)
        self._l_copy_types = QPlainTextEdit()
        self._l_copy_types.setMaximumHeight(80)
        self._l_copy_types.setPlaceholderText("One per line: Original for Recipient\nDuplicate for Transporter")
        g5l.addWidget(self._l_copy_types)
        layout.addWidget(g5)

        # Font
        g6 = QGroupBox("Font & Style")
        f6 = QFormLayout(g6)
        self._l_font = QComboBox()
        self._l_font.addItems(["Helvetica", "Times-Roman", "Courier"])
        f6.addRow("Font Family", self._l_font)
        self._l_font_size = QDoubleSpinBox()
        self._l_font_size.setRange(6, 14)
        self._l_font_size.setValue(8)
        self._l_font_size.setSuffix(" pt")
        f6.addRow("Base Font Size", self._l_font_size)
        layout.addWidget(g6)

        btn_save = QPushButton("💾  Save Invoice Layout")
        btn_save.clicked.connect(self._save_layout)
        layout.addWidget(btn_save)
        layout.addStretch()

        scroll.setWidget(w)
        self._tabs.addTab(scroll, "Invoice Layout")

    # ── Tab 6: Theme ──────────────────────────────────────────────
    def _build_theme_tab(self) -> None:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(24, 20, 24, 20)
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._t_theme = QComboBox()
        self._t_theme.addItems(["light", "dark"])
        form.addRow("App Theme", self._t_theme)

        color_row = QHBoxLayout()
        self._t_accent = QLineEdit("#1565C0")
        self._t_accent.setMaximumWidth(120)
        color_row.addWidget(self._t_accent)
        btn_pick = QPushButton("Pick…")
        btn_pick.setProperty("secondary", True)
        btn_pick.setMaximumWidth(60)
        btn_pick.clicked.connect(self._pick_accent_color)
        color_row.addWidget(btn_pick)
        color_row.addStretch()
        form.addRow("Accent Color", color_row)

        btn_apply = QPushButton("🎨  Apply Theme")
        btn_apply.clicked.connect(self._apply_theme)
        form.addRow("", btn_apply)

        note = QLabel("Theme changes take effect immediately.\nRestart for best results.")
        note.setObjectName("subheading")
        note.setWordWrap(True)
        form.addRow("", note)

        self._tabs.addTab(w, "Theme")

    # ── Tab 7: Data & Backup ──────────────────────────────────────
    def _build_data_tab(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        # Backup section
        g1 = QGroupBox("Backup & Restore")
        g1l = QVBoxLayout(g1)

        # Backup frequency
        freq_row = QFormLayout()
        freq_row.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._cmb_backup_freq = QComboBox()
        self._cmb_backup_freq.addItems([
            "Never", "Per Invoice", "Every 5 Invoices",
            "Every 10 Invoices", "Daily", "Monthly",
        ])
        freq_row.addRow("Auto Backup:", self._cmb_backup_freq)
        g1l.addLayout(freq_row)

        btn_row = QHBoxLayout()
        btn_backup = QPushButton("💾  Backup Now")
        btn_backup.clicked.connect(self._backup_now)
        btn_row.addWidget(btn_backup)
        btn_restore = QPushButton("📂  Restore from Backup")
        btn_restore.setProperty("secondary", True)
        btn_restore.clicked.connect(self._restore_backup)
        btn_row.addWidget(btn_restore)
        btn_row.addStretch()
        g1l.addLayout(btn_row)
        self._lbl_backup_info = QLabel(f"Backup folder: {BACKUP_DIR}")
        self._lbl_backup_info.setObjectName("subheading")
        self._lbl_backup_info.setWordWrap(True)
        g1l.addWidget(self._lbl_backup_info)
        layout.addWidget(g1)

        # PDF save path
        g_pdf = QGroupBox("PDF Settings")
        g_pdf_l = QFormLayout(g_pdf)
        g_pdf_l.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        pdf_row = QHBoxLayout()
        self._txt_pdf_path = QLineEdit()
        self._txt_pdf_path.setPlaceholderText("Default: same as database folder")
        pdf_row.addWidget(self._txt_pdf_path, 1)
        btn_pdf_browse = QPushButton("Browse…")
        btn_pdf_browse.setProperty("secondary", True)
        btn_pdf_browse.clicked.connect(self._browse_pdf_path)
        pdf_row.addWidget(btn_pdf_browse)
        g_pdf_l.addRow("Default PDF Save Path:", pdf_row)

        btn_save_pdf = QPushButton("💾 Save PDF Settings")
        btn_save_pdf.clicked.connect(self._save_pdf_settings)
        g_pdf_l.addRow("", btn_save_pdf)
        layout.addWidget(g_pdf)

        # Import / Export
        g2 = QGroupBox("Data Import / Export")
        g2l = QVBoxLayout(g2)
        btn_row2 = QHBoxLayout()
        btn_exp_all = QPushButton("📤  Export All Data to Excel")
        btn_exp_all.setProperty("secondary", True)
        btn_exp_all.clicked.connect(self._export_all_data)
        btn_row2.addWidget(btn_exp_all)
        btn_exp_db = QPushButton("📤  Export Database (.db)")
        btn_exp_db.setProperty("secondary", True)
        btn_exp_db.clicked.connect(self._export_db_copy)
        btn_row2.addWidget(btn_exp_db)
        btn_row2.addStretch()
        g2l.addLayout(btn_row2)
        layout.addWidget(g2)

        # Danger zone
        danger = QGroupBox("⚠️  Danger Zone")
        danger.setStyleSheet(
            "QGroupBox { border: 2px solid #E53935; border-radius: 6px; "
            "margin-top: 12px; padding: 16px; } "
            "QGroupBox::title { color: #E53935; padding: 0 8px; }"
        )
        dl = QVBoxLayout(danger)
        desc = QLabel(
            "Reset to Factory Defaults will <b>delete ALL data</b> — "
            "company profile, customers, products, documents, purchases, "
            "counters, and settings — then re-seed the database and show "
            "the first-run wizard.\n\nThis cannot be undone."
        )
        desc.setWordWrap(True)
        dl.addWidget(desc)
        btn_row3 = QHBoxLayout()
        btn_row3.addStretch()
        btn_reset = QPushButton("🗑️  Reset to Factory Defaults")
        btn_reset.setStyleSheet(
            "QPushButton { background: #E53935; color: white; "
            "font-weight: bold; padding: 10px 24px; border-radius: 4px; } "
            "QPushButton:hover { background: #C62828; }"
        )
        btn_reset.clicked.connect(self._on_reset_clicked)
        btn_row3.addWidget(btn_reset)
        btn_row3.addStretch()
        dl.addLayout(btn_row3)
        layout.addWidget(danger)

        layout.addStretch()
        scroll.setWidget(w)
        self._tabs.addTab(scroll, "Data & Backup")

    # ==================================================================
    # Load all data
    # ==================================================================
    def _load_all(self) -> None:
        if not self.conn:
            return
        self._load_company()
        self._load_bank()
        self._load_states()
        self._load_tc()
        self._load_doc_types()
        self._load_layout()
        self._load_theme()

    def _load_states(self) -> None:
        repo = StateMasterRepo(self.conn)
        for s in repo.list_all():
            self._c_state.addItem(f"{s.state_name} ({s.code})", s.code)

    def _load_company(self) -> None:
        p = CompanyRepo(self.conn).get()
        self._c_name.setText(p.name)
        self._c_gstin.setText(p.gstin)
        self._c_pan.setText(p.pan)
        self._c_cin.setText(p.cin)
        self._c_addr1.setText(p.address_line1)
        self._c_addr2.setText(p.address_line2)
        self._c_phone.setText(p.phone)
        self._c_email.setText(p.email)
        self._c_website.setText(p.website)
        self._c_sig_label.setText(p.signature_label)
        self._c_currency.setText(p.currency_symbol)
        self._c_logo_path.setText(p.logo_path)
        self._c_stamp_path.setText(p.stamp_path)
        # Select state
        idx = self._c_state.findData(p.state_code)
        if idx >= 0:
            self._c_state.setCurrentIndex(idx)
        # FY start
        fy_idx = self._c_fy_start.findData(p.financial_year_start)
        if fy_idx >= 0:
            self._c_fy_start.setCurrentIndex(fy_idx)

    def _load_bank(self) -> None:
        p = CompanyRepo(self.conn).get()
        self._b_bank.setText(p.bank_name)
        self._b_branch.setText(p.bank_branch)
        self._b_acno.setText(p.account_no)
        idx = self._b_type.findText(p.account_type)
        if idx >= 0:
            self._b_type.setCurrentIndex(idx)
        self._b_ifsc.setText(p.ifsc_code)

    def _load_tc(self) -> None:
        self._tc_type.clear()
        repo = DocTypeConfigRepo(self.conn)
        for dt in repo.list_all():
            self._tc_type.addItem(dt["display_name"], dt["code"])
        if self._tc_type.count():
            self._load_tc_for_current()

    def _load_tc_for_current(self) -> None:
        code = self._tc_type.currentData()
        if not code:
            return
        tc_text, enabled = TermsConditionsRepo(self.conn).get_for_type(code)
        self._tc_edit.setPlainText(tc_text)
        self._tc_enabled.setChecked(enabled)

    def _load_doc_types(self) -> None:
        repo = DocTypeConfigRepo(self.conn)
        types = repo.list_all()
        self._dt_table.setRowCount(0)
        for dt in types:
            row = self._dt_table.rowCount()
            self._dt_table.insertRow(row)
            code_item = QTableWidgetItem(dt["code"])
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._dt_table.setItem(row, 0, code_item)
            self._dt_table.setItem(row, 1, QTableWidgetItem(dt["display_name"]))
            self._dt_table.setItem(row, 2, QTableWidgetItem(dt["prefix"]))
            self._dt_table.setItem(row, 3, QTableWidgetItem(dt.get("number_format", "")))
            self._dt_table.setItem(row, 4, QTableWidgetItem(str(dt.get("padding_digits", 4))))
            active = QTableWidgetItem()
            active.setCheckState(
                Qt.CheckState.Checked if dt.get("is_enabled", 1)
                else Qt.CheckState.Unchecked
            )
            self._dt_table.setItem(row, 5, active)

    def _load_layout(self) -> None:
        data = PdfTemplateRepo(self.conn).get()
        if not data:
            return
        self._l_show_logo.setChecked(bool(data.get("show_logo", 1)))
        idx = self._l_logo_pos.findText(data.get("logo_position", "left"))
        if idx >= 0:
            self._l_logo_pos.setCurrentIndex(idx)
        self._l_logo_width.setValue(data.get("logo_width_mm", 25))
        self._l_show_cin.setChecked(bool(data.get("show_cin", 1)))
        self._l_show_website.setChecked(bool(data.get("show_website", 1)))
        self._l_show_stamp.setChecked(bool(data.get("show_stamp", 1)))
        self._l_header_color.setText(data.get("header_color_hex", "#000000"))

        for key, cb in self._vis_checks.items():
            cb.setChecked(bool(data.get(key, 1)))

        self._l_show_discount.setChecked(bool(data.get("show_discount_col", 1)))
        self._l_show_hsn.setChecked(bool(data.get("show_hsn_col", 1)))
        self._l_show_bank.setChecked(bool(data.get("show_bank_details", 1)))
        self._l_show_words.setChecked(bool(data.get("show_amount_in_words", 1)))
        self._l_show_tc.setChecked(bool(data.get("show_tc", 1)))
        self._l_footer_note.setText(data.get("footer_note", ""))

        # Copy types
        try:
            copies = json.loads(data.get("copy_types_json", "[]"))
            self._l_copy_types.setPlainText("\n".join(copies))
        except Exception:
            pass

        idx2 = self._l_font.findText(data.get("font_family", "Helvetica"))
        if idx2 >= 0:
            self._l_font.setCurrentIndex(idx2)
        self._l_font_size.setValue(data.get("base_font_size", 8))

    def _load_theme(self) -> None:
        repo = AppSettingsRepo(self.conn)
        theme = repo.get("theme", "light")
        idx = self._t_theme.findText(theme)
        if idx >= 0:
            self._t_theme.setCurrentIndex(idx)
        self._t_accent.setText(repo.get("accent_color", "#1565C0"))

        # Load PDF / backup settings
        self._txt_pdf_path.setText(repo.get("pdf_save_path", ""))
        freq = repo.get("backup_frequency", "Never")
        freq_idx = self._cmb_backup_freq.findText(freq)
        if freq_idx >= 0:
            self._cmb_backup_freq.setCurrentIndex(freq_idx)

    # ==================================================================
    # Save handlers
    # ==================================================================
    def _save_company(self) -> None:
        name = self._c_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Business Name is required.")
            return
        gstin = self._c_gstin.text().strip().upper()
        if gstin:
            ok, msg = validate_gstin(gstin)
            if not ok:
                QMessageBox.warning(self, "Invalid GSTIN", msg)
                return
        email = self._c_email.text().strip()
        if email:
            ok, msg = validate_email(email)
            if not ok:
                QMessageBox.warning(self, "Invalid Email", msg)
                return

        state_code = self._c_state.currentData() or ""
        state_name = ""
        if state_code:
            state_name = StateMasterRepo(self.conn).get_name(state_code)

        p = CompanyRepo(self.conn).get()
        p.name = name
        p.gstin = gstin
        p.pan = self._c_pan.text().strip().upper()
        p.cin = self._c_cin.text().strip()
        p.address_line1 = self._c_addr1.text().strip()
        p.address_line2 = self._c_addr2.text().strip()
        p.phone = self._c_phone.text().strip()
        p.email = email
        p.website = self._c_website.text().strip()
        p.state_code = state_code
        p.state_name = state_name
        p.signature_label = self._c_sig_label.text().strip() or "Authorised Signatory"
        p.currency_symbol = self._c_currency.text().strip() or "₹"
        p.financial_year_start = self._c_fy_start.currentData() or 4
        p.logo_path = self._c_logo_path.text().strip()
        p.stamp_path = self._c_stamp_path.text().strip()
        p.is_setup_complete = 1

        CompanyRepo(self.conn).save(p)
        QMessageBox.information(self, "Saved", "Company profile updated.")

    def _save_bank(self) -> None:
        ifsc = self._b_ifsc.text().strip().upper()
        if ifsc:
            ok, msg = validate_ifsc(ifsc)
            if not ok:
                QMessageBox.warning(self, "Invalid IFSC", msg)
                return

        p = CompanyRepo(self.conn).get()
        p.bank_name = self._b_bank.text().strip()
        p.bank_branch = self._b_branch.text().strip()
        p.account_no = self._b_acno.text().strip()
        p.account_type = self._b_type.currentText()
        p.ifsc_code = ifsc
        CompanyRepo(self.conn).save(p)
        QMessageBox.information(self, "Saved", "Bank details updated.")

    def _save_tc(self) -> None:
        code = self._tc_type.currentData()
        if not code:
            return
        text = self._tc_edit.toPlainText()
        enabled = self._tc_enabled.isChecked()
        TermsConditionsRepo(self.conn).save(code, text, enabled)
        QMessageBox.information(self, "Saved", f"Terms & Conditions saved for {code}.")

    def _copy_tc_all(self) -> None:
        text = self._tc_edit.toPlainText()
        enabled = self._tc_enabled.isChecked()
        repo = TermsConditionsRepo(self.conn)
        dtc = DocTypeConfigRepo(self.conn)
        for dt in dtc.list_all():
            repo.save(dt["code"], text, enabled)
        QMessageBox.information(self, "Copied", "Terms & Conditions copied to all document types.")

    def _save_doc_types(self) -> None:
        repo = DocTypeConfigRepo(self.conn)
        for row in range(self._dt_table.rowCount()):
            code = self._dt_table.item(row, 0).text()
            data = {
                "code": code,
                "display_name": self._dt_table.item(row, 1).text(),
                "prefix": self._dt_table.item(row, 2).text(),
                "number_format": self._dt_table.item(row, 3).text(),
                "padding_digits": int(self._dt_table.item(row, 4).text() or 4),
                "is_enabled": 1 if self._dt_table.item(row, 5).checkState() == Qt.CheckState.Checked else 0,
            }
            repo.save(data)
        QMessageBox.information(self, "Saved", "Document type configuration saved.")

    def _save_layout(self) -> None:
        data = {
            "show_logo": int(self._l_show_logo.isChecked()),
            "logo_position": self._l_logo_pos.currentText(),
            "logo_width_mm": self._l_logo_width.value(),
            "show_stamp": int(self._l_show_stamp.isChecked()),
            "show_cin": int(self._l_show_cin.isChecked()),
            "show_website": int(self._l_show_website.isChecked()),
            "header_color_hex": self._l_header_color.text().strip() or "#000000",
            "show_discount_col": int(self._l_show_discount.isChecked()),
            "show_hsn_col": int(self._l_show_hsn.isChecked()),
            "show_bank_details": int(self._l_show_bank.isChecked()),
            "show_amount_in_words": int(self._l_show_words.isChecked()),
            "show_tc": int(self._l_show_tc.isChecked()),
            "footer_note": self._l_footer_note.text().strip(),
            "font_family": self._l_font.currentText(),
            "base_font_size": self._l_font_size.value(),
        }
        # Visibility checks
        for key, cb in self._vis_checks.items():
            data[key] = int(cb.isChecked())

        # Copy types
        lines = [l.strip() for l in self._l_copy_types.toPlainText().split("\n") if l.strip()]
        data["copy_types_json"] = json.dumps(lines) if lines else '["Original for Recipient"]'

        PdfTemplateRepo(self.conn).save(data)
        QMessageBox.information(self, "Saved", "Invoice layout settings saved.")

    def _apply_theme(self) -> None:
        repo = AppSettingsRepo(self.conn)
        theme = self._t_theme.currentText()
        accent = self._t_accent.text().strip() or "#1565C0"
        repo.set("theme", theme)
        repo.set("accent_color", accent)

        # Apply live
        from ui.styles import get_stylesheet
        app = self.window()
        if app:
            qapp = app.windowHandle()
        # Apply to QApplication
        from PyQt6.QtWidgets import QApplication
        inst = QApplication.instance()
        if inst:
            inst.setStyleSheet(get_stylesheet(theme, accent))
        QMessageBox.information(self, "Applied", "Theme updated. Some changes may need a restart.")

    # ==================================================================
    # Helpers
    # ==================================================================
    def _browse_image(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if path:
            # Copy to assets
            dest = Path(ASSETS_DIR) / Path(path).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            target.setText(str(dest))

    def _pick_header_color(self) -> None:
        from PyQt6.QtGui import QColor as QC
        color = QColorDialog.getColor(QC(self._l_header_color.text()), self, "Header Color")
        if color.isValid():
            self._l_header_color.setText(color.name())

    def _pick_accent_color(self) -> None:
        from PyQt6.QtGui import QColor as QC
        color = QColorDialog.getColor(QC(self._t_accent.text()), self, "Accent Color")
        if color.isValid():
            self._t_accent.setText(color.name())

    def _browse_pdf_path(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Default PDF Save Folder",
        )
        if folder:
            self._txt_pdf_path.setText(folder)

    def _save_pdf_settings(self) -> None:
        repo = AppSettingsRepo(self.conn)
        repo.set("pdf_save_path", self._txt_pdf_path.text().strip())
        repo.set("backup_frequency", self._cmb_backup_freq.currentText())
        QMessageBox.information(self, "Saved", "PDF and backup settings saved.")

    # ── Data & Backup ─────────────────────────────────────────────
    def _backup_now(self) -> None:
        backup_dir = Path(BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)
        db_path = Path(DATA_DIR) / "billing.db"
        if not db_path.exists():
            QMessageBox.warning(self, "Error", "Database file not found.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = backup_dir / f"billing_backup_{ts}.db"
        shutil.copy2(db_path, dest)
        self._lbl_backup_info.setText(f"Last backup: {dest.name}\nFolder: {backup_dir}")
        QMessageBox.information(self, "Backup Complete", f"Saved to:\n{dest}")

    def _restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", str(BACKUP_DIR),
            "Database (*.db)",
        )
        if not path:
            return
        reply = QMessageBox.warning(
            self, "Restore Backup",
            "This will REPLACE all current data with the backup.\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        db_path = Path(DATA_DIR) / "billing.db"
        shutil.copy2(path, db_path)
        QMessageBox.information(
            self, "Restored",
            "Backup restored. Please restart the application.",
        )

    def _export_all_data(self) -> None:
        from services.excel_io import export_to_excel
        from repositories.customer_repo import CustomerRepo
        from repositories.product_repo import ProductRepo
        from repositories.purchase_repo import PurchaseRepo
        from services.excel_io import dataclass_list_to_dicts

        path, _ = QFileDialog.getSaveFileName(
            self, "Export All Data", "gst_billing_export.xlsx",
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        # Customers
        custs = CustomerRepo(self.conn).list_all(active_only=False)
        cust_rows = dataclass_list_to_dicts(custs)
        # Products
        prods = ProductRepo(self.conn).list_all(active_only=False)
        prod_rows = dataclass_list_to_dicts(prods)
        # Purchases
        purch = PurchaseRepo(self.conn).list_filtered(limit=99999)
        purch_rows = dataclass_list_to_dicts(purch)

        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Info"
        ws["A1"] = "GST Billing Suite — Full Export"
        ws["A2"] = f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        for sheet_name, rows in [("Customers", cust_rows), ("Products", prod_rows), ("Purchases", purch_rows)]:
            if not rows:
                continue
            ws2 = wb.create_sheet(sheet_name)
            headers = list(rows[0].keys())
            for c, h in enumerate(headers, 1):
                ws2.cell(1, c, h)
            for r, row_data in enumerate(rows, 2):
                for c, h in enumerate(headers, 1):
                    ws2.cell(r, c, row_data.get(h))
        wb.save(path)
        QMessageBox.information(self, "Exported", f"All data exported to:\n{path}")

    def _export_db_copy(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Database Copy", "billing_copy.db",
            "Database (*.db)",
        )
        if not path:
            return
        db_path = Path(DATA_DIR) / "billing.db"
        shutil.copy2(db_path, path)
        QMessageBox.information(self, "Exported", f"Database copy saved to:\n{path}")

    # ── Factory Reset ─────────────────────────────────────────────
    def _on_reset_clicked(self) -> None:
        reply = QMessageBox.warning(
            self, "Confirm Factory Reset",
            "This will DELETE all your data and restart the setup wizard.\n\n"
            "Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        reply2 = QMessageBox.critical(
            self, "Final Confirmation",
            "LAST CHANCE — all invoices, customers, products and settings "
            "will be permanently erased.\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply2 != QMessageBox.StandardButton.Yes:
            return
        if not self.conn:
            QMessageBox.critical(self, "Error", "No database connection.")
            return
        self._do_factory_reset()

    def _do_factory_reset(self) -> None:
        from database.seed_data import seed_all
        tables = [
            "document_items", "documents", "customers", "products",
            "purchases", "invoice_counter", "terms_conditions",
            "app_settings", "pdf_template_settings", "doc_type_config",
            "purchase_categories", "state_master", "company_profile",
        ]
        try:
            for tbl in tables:
                self.conn.execute(f"DELETE FROM {tbl}")
            self.conn.commit()
            seed_all(self.conn)
            QMessageBox.information(
                self, "Reset Complete",
                "All data erased and defaults restored.\nThe setup wizard will now appear.",
            )
            self.reset_requested.emit()
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Reset Failed", str(e))
