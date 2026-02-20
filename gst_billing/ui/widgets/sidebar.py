"""
Sidebar navigation widget — collapsible icon rail + expanded panel.

Supports expanded (icon + label) and collapsed (icon-only) modes.
A toggle button at the bottom controls the mode.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFrame, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy,
)


# (id, icon_char, label)
NAV_ITEMS: list[tuple[str, str, str]] = [
    ("dashboard",  "📊", "Dashboard"),
    ("new_doc",    "📝", "New Document"),
    ("documents",  "📋", "Documents"),
    ("customers",  "👥", "Customers"),
    ("products",   "📦", "Products"),
    ("purchases",  "🛒", "Purchases"),
    ("gstr1",      "📊", "GSTR-1"),
    ("reports",    "📈", "Reports"),
    ("settings",   "⚙️",  "Settings"),
]

BOTTOM_ITEMS: list[tuple[str, str, str]] = [
    ("backup",  "💾", "Backup"),
    ("about",   "ℹ️",  "About"),
]

EXPANDED_WIDTH = 210
COLLAPSED_WIDTH = 54


class Sidebar(QFrame):
    """Left-hand navigation sidebar with collapse / expand."""

    page_requested = pyqtSignal(str)      # emits page id
    collapsed_changed = pyqtSignal(bool)  # True when collapsed

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._buttons: dict[str, QPushButton] = {}
        self._labels: dict[str, str] = {}
        self._icons: dict[str, str] = {}
        self._active_id: str = ""
        self._expanded = True
        self.setFixedWidth(EXPANDED_WIDTH)
        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # App title
        self._title_label = QLabel("  GST Billing Suite")
        self._title_label.setObjectName("appTitle")
        self._layout.addWidget(self._title_label)

        self._add_separator()

        for page_id, icon, label in NAV_ITEMS:
            btn = self._make_button(page_id, icon, label)
            self._layout.addWidget(btn)

        self._layout.addStretch(1)
        self._add_separator()

        for page_id, icon, label in BOTTOM_ITEMS:
            btn = self._make_button(page_id, icon, label)
            self._layout.addWidget(btn)

        # Collapse / expand toggle
        self._btn_toggle = QPushButton("◀  Collapse")
        self._btn_toggle.setObjectName("sidebarToggle")
        self._btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_toggle.setToolTip("Collapse sidebar")
        self._btn_toggle.clicked.connect(self.toggle_collapse)
        self._layout.addWidget(self._btn_toggle)
        self._layout.addSpacing(4)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_button(self, page_id: str, icon: str, label: str) -> QPushButton:
        full = f" {icon}  {label}"
        btn = QPushButton(full)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setToolTip(label)
        btn.clicked.connect(lambda checked, pid=page_id: self._on_clicked(pid))
        self._buttons[page_id] = btn
        self._labels[page_id] = full
        self._icons[page_id] = f" {icon} "
        return btn

    def _add_separator(self) -> None:
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        self._layout.addWidget(sep)

    def _on_clicked(self, page_id: str) -> None:
        self.set_active(page_id)
        self.page_requested.emit(page_id)

    # ------------------------------------------------------------------
    # Collapse / Expand
    # ------------------------------------------------------------------
    def toggle_collapse(self) -> None:
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def collapse(self) -> None:
        self._expanded = False
        self.setFixedWidth(COLLAPSED_WIDTH)
        self._title_label.setText(" GST")
        self._btn_toggle.setText(" ▶ ")
        self._btn_toggle.setToolTip("Expand sidebar")
        for pid, btn in self._buttons.items():
            btn.setText(self._icons[pid])
        self.collapsed_changed.emit(True)

    def expand(self) -> None:
        self._expanded = True
        self.setFixedWidth(EXPANDED_WIDTH)
        self._title_label.setText("  GST Billing Suite")
        self._btn_toggle.setText("◀  Collapse")
        self._btn_toggle.setToolTip("Collapse sidebar")
        for pid, btn in self._buttons.items():
            btn.setText(self._labels[pid])
        self.collapsed_changed.emit(False)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_active(self, page_id: str) -> None:
        """Highlight the given button and de-highlight others."""
        self._active_id = page_id
        for pid, btn in self._buttons.items():
            btn.setChecked(pid == page_id)
