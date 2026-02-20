"""
Reusable widgets for custom (dynamic) field management.

• ManageFieldsDialog   — modal dialog to add / remove / reorder ALL attributes
                         (both built-in and user-created custom fields)
• build_custom_inputs  — creates QLineEdit/QDoubleSpinBox for each active *custom* definition
• read_custom_inputs   — reads current widget values into a JSON-ready dict
• load_custom_inputs   — populates widgets from a JSON string
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from models.custom_field import CustomFieldDef
from repositories.custom_field_repo import CustomFieldRepo


# ======================================================================
# Manage Fields Dialog
# ======================================================================

class ManageFieldsDialog(QDialog):
    """Modal to add / remove attribute definitions for an entity type.

    Shows **all** fields — built-in (with 🔒 for required, 📌 for optional
    built-in) and user-created custom fields.  Required fields cannot be
    removed.  Optional built-in and custom fields can be toggled.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        entity_type: str,
        entity_label: str = "Entity",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Manage {entity_label} Fields")
        self.setMinimumSize(480, 440)
        self._repo = CustomFieldRepo(conn)
        self._entity_type = entity_type
        # Ensure built-in definitions exist
        self._repo.seed_builtins(entity_type)
        self._build_ui()
        self._load_fields()

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info = QLabel(
            "Toggle which fields appear on the form.\n"
            "🔒 Required fields cannot be removed.\n"
            "📌 Built-in fields can be hidden if not needed.\n"
            "Custom fields can be added or removed freely."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; margin-bottom: 4px;")
        layout.addWidget(info)

        # Current fields list
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list, 1)

        # Add custom field row
        add_row = QHBoxLayout()
        self._inp_label = QLineEdit()
        self._inp_label.setPlaceholderText("New custom field label, e.g. Color, Weight…")
        add_row.addWidget(self._inp_label, 1)

        self._cmb_type = QComboBox()
        self._cmb_type.addItems(["Text", "Number"])
        self._cmb_type.setFixedWidth(90)
        add_row.addWidget(self._cmb_type)

        btn_add = QPushButton("➕ Add")
        btn_add.clicked.connect(self._add_field)
        add_row.addWidget(btn_add)
        layout.addLayout(add_row)

        # Remove / Toggle buttons
        btn_row = QHBoxLayout()
        btn_toggle = QPushButton("👁️ Show / Hide Selected")
        btn_toggle.clicked.connect(self._toggle_field)
        btn_row.addWidget(btn_toggle)

        btn_remove = QPushButton("🗑️ Remove Custom Field")
        btn_remove.clicked.connect(self._remove_field)
        btn_row.addWidget(btn_remove)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Dialog buttons
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.accept)
        layout.addWidget(bb)

    # ── Logic ─────────────────────────────────────────────────────────
    def _load_fields(self) -> None:
        self._list.clear()
        # Show ALL definitions (active + inactive) for this entity type
        defs = self._repo.list_for_entity(self._entity_type, active_only=False)
        for d in defs:
            # Build display text
            if d.is_required:
                prefix = "🔒 "
                suffix = "  (required)"
            elif d.is_builtin:
                prefix = "📌 "
                suffix = "  (built-in)"
            else:
                prefix = "🔧 "
                suffix = f"  ({d.field_type})"

            active_tag = "" if d.is_active else "  [HIDDEN]"
            text = f"{prefix}{d.field_label}{suffix}{active_tag}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, d.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, d)

            # Grey out inactive fields
            if not d.is_active:
                item.setForeground(QColor("#999"))
                font = item.font()
                font.setItalic(True)
                item.setFont(font)

            self._list.addItem(item)

    def _add_field(self) -> None:
        label = self._inp_label.text().strip()
        if not label:
            QMessageBox.warning(self, "Required", "Enter a field label.")
            return
        fname = CustomFieldRepo.to_field_name(label)
        if not fname:
            QMessageBox.warning(self, "Invalid", "Label must contain at least one letter or number.")
            return
        ftype = "number" if self._cmb_type.currentText() == "Number" else "text"
        try:
            self._repo.ensure_field(self._entity_type, fname, label, ftype)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self._inp_label.clear()
        self._load_fields()

    def _toggle_field(self) -> None:
        """Toggle visibility of the selected field (show ↔ hide)."""
        item = self._list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Select a field to toggle.")
            return
        d: CustomFieldDef = item.data(Qt.ItemDataRole.UserRole + 1)
        if d.is_required:
            QMessageBox.information(
                self, "Required Field",
                f"'{d.field_label}' is required and cannot be hidden.",
            )
            return
        if d.is_active:
            # Hide it
            self._repo.deactivate(d.id)
        else:
            # Show it
            self.conn_execute_reactivate(d.id)
        self._load_fields()

    def conn_execute_reactivate(self, field_id: int) -> None:
        """Re-activate a field."""
        self._repo.conn.execute(
            "UPDATE custom_field_definitions SET is_active = 1 WHERE id = ?",
            (field_id,),
        )
        self._repo.conn.commit()

    def _remove_field(self) -> None:
        """Permanently deactivate a custom (non-built-in) field."""
        item = self._list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Select a field to remove.")
            return
        d: CustomFieldDef = item.data(Qt.ItemDataRole.UserRole + 1)
        if d.is_required:
            QMessageBox.information(
                self, "Required",
                f"'{d.field_label}' is required and cannot be removed.",
            )
            return
        if d.is_builtin:
            QMessageBox.information(
                self, "Built-in Field",
                f"'{d.field_label}' is a built-in field.\n"
                "Use 'Show / Hide' to toggle it instead of removing.",
            )
            return
        reply = QMessageBox.question(
            self, "Remove Field",
            f"Remove custom field '{d.field_label}'?\n\n"
            "Existing data for this field will be kept but hidden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._repo.deactivate(d.id)
            self._load_fields()


# ======================================================================
# Dynamic Form Helpers
# ======================================================================

def build_custom_inputs(
    conn: sqlite3.Connection,
    entity_type: str,
    form_layout: QFormLayout,
) -> dict[str, QLineEdit]:
    """Create and add QLineEdit widgets for each active *custom* (non-built-in) definition.

    Built-in fields are handled separately by each page's own form code.
    Returns a dict keyed by field_name → QLineEdit.
    """
    repo = CustomFieldRepo(conn)
    defs = repo.list_for_entity(entity_type)
    inputs: dict[str, QLineEdit] = {}
    for d in defs:
        if d.is_builtin:
            continue  # built-in fields are managed by the page's form
        inp = QLineEdit()
        inp.setPlaceholderText(f"Custom: {d.field_label}")
        inp.setProperty("custom_field_type", d.field_type)
        form_layout.addRow(d.field_label, inp)
        inputs[d.field_name] = inp
    return inputs


def read_custom_inputs(inputs: dict[str, QLineEdit]) -> str:
    """Read values from custom field widgets and return a JSON string."""
    data: dict[str, Any] = {}
    for fname, widget in inputs.items():
        val = widget.text().strip()
        if val:
            if widget.property("custom_field_type") == "number":
                try:
                    data[fname] = float(val)
                except ValueError:
                    data[fname] = val
            else:
                data[fname] = val
    return json.dumps(data, ensure_ascii=False)


def load_custom_inputs(inputs: dict[str, QLineEdit], json_str: str) -> None:
    """Populate custom field widgets from a JSON string."""
    try:
        data = json.loads(json_str) if json_str else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    for fname, widget in inputs.items():
        widget.setText(str(data.get(fname, "")))
