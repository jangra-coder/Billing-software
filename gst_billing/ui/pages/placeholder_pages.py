"""
Placeholder pages for Phase 2 — simple "Coming Soon" stubs.

These will be replaced with full implementations in later phases.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QWidget,
)


class PlaceholderPage(QWidget):
    """Generic placeholder with a title and coming-soon message."""

    def __init__(
        self,
        title: str,
        icon: str = "🚧",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("placeholderPage")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 48px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        heading = QLabel(title)
        heading.setObjectName("heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        sub = QLabel("Coming soon — this page will be built in a later phase.")
        sub.setObjectName("subheading")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)


# Concrete stubs for each sidebar entry

class DashboardPage(PlaceholderPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Dashboard", "📊", parent)


class DocumentListPage(PlaceholderPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Documents", "📋", parent)


class CustomerManagerPage(PlaceholderPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Customers", "👥", parent)


class ProductManagerPage(PlaceholderPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Products / Services", "📦", parent)


class PurchaseTrackerPage(PlaceholderPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Purchase Tracker", "🛒", parent)


class Gstr1Page(PlaceholderPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("GSTR-1 Prep", "📑", parent)


class ReportsPage(PlaceholderPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Reports", "📈", parent)
