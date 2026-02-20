"""
First-Run Wizard — 4-step onboarding for new businesses.

Step 1: Business Identity (name, GSTIN, PAN, address, state)
Step 2: Bank Details
Step 3: Branding (logo, stamp, signature label)
Step 4: Preferences (default GST rate, theme)

On completion: company_profile.is_setup_complete = 1
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QMessageBox,
)

from models.company import CompanyProfile
from repositories.company_repo import CompanyRepo
from repositories.settings_repo import StateMasterRepo
from services.gst_engine import extract_state_code_from_gstin
from services.validator import validate_gstin, extract_pan_from_gstin


class FirstRunWizard(QDialog):
    """Modal 4-step wizard shown on first launch."""

    setup_complete = pyqtSignal()

    def __init__(
        self,
        conn: sqlite3.Connection,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.conn = conn
        self.profile = CompanyRepo(conn).get()
        self.setWindowTitle("Welcome — GST Billing Suite Setup")
        self.setMinimumSize(640, 540)
        self.setModal(True)
        self._current_step = 0
        self._build_ui()

    # ==================================================================
    # Build
    # ==================================================================
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        # Title
        title = QLabel("Welcome to GST Billing Suite")
        title.setObjectName("heading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

        sub = QLabel("Let's set up your business in 4 simple steps.")
        sub.setObjectName("subheading")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(sub)
        outer.addSpacing(8)

        # Steps indicator
        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._step_label)
        outer.addSpacing(4)

        # Stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step3())
        self._stack.addWidget(self._build_step4())
        outer.addWidget(self._stack, 1)

        # Navigation buttons
        nav = QHBoxLayout()
        self._btn_skip = QPushButton("Skip Setup — I'll configure later")
        self._btn_skip.setProperty("flat", True)
        self._btn_skip.clicked.connect(self._skip)
        nav.addWidget(self._btn_skip)
        nav.addStretch()

        self._btn_back = QPushButton("← Back")
        self._btn_back.setProperty("flat", True)
        self._btn_back.clicked.connect(self._go_back)
        nav.addWidget(self._btn_back)

        self._btn_next = QPushButton("Next →")
        self._btn_next.clicked.connect(self._go_next)
        nav.addWidget(self._btn_next)

        outer.addLayout(nav)
        self._update_nav()

    # ------------------------------------------------------------------
    # Step 1 — Business Identity
    # ------------------------------------------------------------------
    def _build_step1(self) -> QWidget:
        page = QWidget()
        page.setObjectName("wizardPage")
        form = QFormLayout(page)
        form.setSpacing(12)
        form.setContentsMargins(20, 16, 20, 16)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.w_name = QLineEdit(self.profile.name)
        form.addRow("Business Name *:", self.w_name)

        self.w_gstin = QLineEdit(self.profile.gstin)
        self.w_gstin.setMaxLength(15)
        self.w_gstin.textChanged.connect(self._on_gstin_changed)
        form.addRow("GSTIN:", self.w_gstin)

        self.w_pan = QLineEdit(self.profile.pan)
        self.w_pan.setMaxLength(10)
        form.addRow("PAN:", self.w_pan)

        self.w_cin = QLineEdit(self.profile.cin)
        form.addRow("CIN (optional):", self.w_cin)

        self.w_addr1 = QLineEdit(self.profile.address_line1)
        form.addRow("Address Line 1:", self.w_addr1)

        self.w_addr2 = QLineEdit(self.profile.address_line2)
        form.addRow("Address Line 2:", self.w_addr2)

        self.w_state = QComboBox()
        state_repo = StateMasterRepo(self.conn)
        self._states = state_repo.list_all()
        self.w_state.addItem("-- Select State --", "")
        for s in self._states:
            self.w_state.addItem(f"{s.state_name} ({s.code})", s.code)
        # Pre-select
        if self.profile.state_code:
            for i in range(self.w_state.count()):
                if self.w_state.itemData(i) == self.profile.state_code:
                    self.w_state.setCurrentIndex(i)
                    break
        form.addRow("State *:", self.w_state)

        self.w_phone = QLineEdit(self.profile.phone)
        form.addRow("Phone:", self.w_phone)

        self.w_email = QLineEdit(self.profile.email)
        form.addRow("Email:", self.w_email)

        self.w_website = QLineEdit(self.profile.website)
        form.addRow("Website:", self.w_website)

        return page

    def _on_gstin_changed(self, text: str) -> None:
        clean = text.strip().upper()
        ok, _ = validate_gstin(clean)
        if ok and len(clean) == 15:
            pan = extract_pan_from_gstin(clean)
            if pan:
                self.w_pan.setText(pan)
            code = extract_state_code_from_gstin(clean)
            if code:
                for i in range(self.w_state.count()):
                    if self.w_state.itemData(i) == code:
                        self.w_state.setCurrentIndex(i)
                        break

    # ------------------------------------------------------------------
    # Step 2 — Bank Details
    # ------------------------------------------------------------------
    def _build_step2(self) -> QWidget:
        page = QWidget()
        page.setObjectName("wizardPage")
        form = QFormLayout(page)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.w_bank_name = QLineEdit(self.profile.bank_name)
        form.addRow("Bank Name:", self.w_bank_name)

        self.w_bank_branch = QLineEdit(self.profile.bank_branch)
        form.addRow("Branch:", self.w_bank_branch)

        self.w_account_no = QLineEdit(self.profile.account_no)
        form.addRow("Account No:", self.w_account_no)

        self.w_account_type = QComboBox()
        self.w_account_type.addItems(["Current", "Savings", "OD", "CC"])
        idx = self.w_account_type.findText(self.profile.account_type)
        if idx >= 0:
            self.w_account_type.setCurrentIndex(idx)
        form.addRow("Account Type:", self.w_account_type)

        self.w_ifsc = QLineEdit(self.profile.ifsc_code)
        self.w_ifsc.setMaxLength(11)
        form.addRow("IFSC Code:", self.w_ifsc)

        return page

    # ------------------------------------------------------------------
    # Step 3 — Branding
    # ------------------------------------------------------------------
    def _build_step3(self) -> QWidget:
        page = QWidget()
        page.setObjectName("wizardPage")
        layout = QVBoxLayout(page)

        # Logo
        logo_grp = QGroupBox("Company Logo")
        logo_lay = QHBoxLayout(logo_grp)
        self.w_logo_path = QLineEdit(self.profile.logo_path)
        self.w_logo_path.setReadOnly(True)
        logo_lay.addWidget(self.w_logo_path)
        btn_logo = QPushButton("Browse…")
        btn_logo.clicked.connect(lambda: self._pick_image(self.w_logo_path))
        logo_lay.addWidget(btn_logo)
        layout.addWidget(logo_grp)

        # Stamp
        stamp_grp = QGroupBox("Stamp / Seal")
        stamp_lay = QHBoxLayout(stamp_grp)
        self.w_stamp_path = QLineEdit(self.profile.stamp_path)
        self.w_stamp_path.setReadOnly(True)
        stamp_lay.addWidget(self.w_stamp_path)
        btn_stamp = QPushButton("Browse…")
        btn_stamp.clicked.connect(lambda: self._pick_image(self.w_stamp_path))
        stamp_lay.addWidget(btn_stamp)
        layout.addWidget(stamp_grp)

        # Signature label
        form = QFormLayout()
        self.w_sig = QLineEdit(self.profile.signature_label)
        form.addRow("Signature Label:", self.w_sig)

        self.w_currency = QLineEdit(self.profile.currency_symbol)
        self.w_currency.setMaxLength(3)
        form.addRow("Currency Symbol:", self.w_currency)
        layout.addLayout(form)

        layout.addStretch()
        return page

    def _pick_image(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.svg)",
        )
        if path:
            target.setText(path)

    # ------------------------------------------------------------------
    # Step 4 — Preferences
    # ------------------------------------------------------------------
    def _build_step4(self) -> QWidget:
        page = QWidget()
        page.setObjectName("wizardPage")
        form = QFormLayout(page)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.w_fy_start = QComboBox()
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        for i, m in enumerate(months, 1):
            self.w_fy_start.addItem(m, i)
        idx = self.w_fy_start.findData(self.profile.financial_year_start)
        if idx >= 0:
            self.w_fy_start.setCurrentIndex(idx)
        form.addRow("Financial Year Starts:", self.w_fy_start)

        info = QLabel(
            "🎉 You're all set! Click Finish to start using the app.\n\n"
            "You can change all these settings later from the Settings page."
        )
        info.setWordWrap(True)
        form.addRow(info)

        return page

    # ==================================================================
    # Navigation
    # ==================================================================
    def _update_nav(self) -> None:
        step = self._current_step
        total = self._stack.count()
        self._step_label.setText(
            f"Step {step + 1} of {total}: "
            f"{['Business Identity', 'Bank Details', 'Branding', 'Preferences'][step]}"
        )
        self._btn_back.setVisible(step > 0)
        self._btn_next.setText("Finish ✓" if step == total - 1 else "Next →")
        self._stack.setCurrentIndex(step)

    def _go_next(self) -> None:
        if self._current_step == 0:
            if not self._validate_step1():
                return
        if self._current_step >= self._stack.count() - 1:
            self._finish()
        else:
            self._current_step += 1
            self._update_nav()

    def _go_back(self) -> None:
        if self._current_step > 0:
            self._current_step -= 1
            self._update_nav()

    def _validate_step1(self) -> bool:
        if not self.w_name.text().strip():
            QMessageBox.warning(self, "Required", "Business name is required.")
            self.w_name.setFocus()
            return False
        if not self.w_state.currentData():
            QMessageBox.warning(self, "Required", "Please select your state.")
            self.w_state.setFocus()
            return False
        return True

    # ==================================================================
    # Finish / Skip
    # ==================================================================
    def _collect_profile(self) -> CompanyProfile:
        state_code = self.w_state.currentData() or ""
        state_name = ""
        for s in self._states:
            if s.code == state_code:
                state_name = s.state_name
                break
        return CompanyProfile(
            name=self.w_name.text().strip(),
            gstin=self.w_gstin.text().strip().upper(),
            pan=self.w_pan.text().strip().upper(),
            cin=self.w_cin.text().strip(),
            address_line1=self.w_addr1.text().strip(),
            address_line2=self.w_addr2.text().strip(),
            state_code=state_code,
            state_name=state_name,
            phone=self.w_phone.text().strip(),
            email=self.w_email.text().strip(),
            website=self.w_website.text().strip(),
            bank_name=self.w_bank_name.text().strip(),
            bank_branch=self.w_bank_branch.text().strip(),
            account_no=self.w_account_no.text().strip(),
            account_type=self.w_account_type.currentText(),
            ifsc_code=self.w_ifsc.text().strip().upper(),
            logo_path=self.w_logo_path.text().strip(),
            stamp_path=self.w_stamp_path.text().strip(),
            signature_label=self.w_sig.text().strip() or "Authorised Signatory",
            currency_symbol=self.w_currency.text().strip() or "₹",
            financial_year_start=self.w_fy_start.currentData() or 4,
            is_setup_complete=1,
        )

    def _finish(self) -> None:
        profile = self._collect_profile()
        CompanyRepo(self.conn).save(profile)
        self.setup_complete.emit()
        self.accept()

    def _skip(self) -> None:
        reply = QMessageBox.question(
            self,
            "Skip Setup?",
            "You can configure everything later from Settings.\nSkip for now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Mark as complete so wizard doesn't show again
            self.conn.execute(
                "UPDATE company_profile SET is_setup_complete = 1 WHERE id = 1"
            )
            self.conn.commit()
            self.setup_complete.emit()
            self.accept()
