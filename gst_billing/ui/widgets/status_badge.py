"""Colour-coded status badge label."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QWidget


_COLOURS = {
    "draft":     ("#FFF3E0", "#E65100"),
    "saved":     ("#E8F5E9", "#2E7D32"),
    "exported":  ("#E3F2FD", "#1565C0"),
    "cancelled": ("#FFEBEE", "#C62828"),
}


class StatusBadge(QLabel):
    """Small label with background tint matching document status."""

    def __init__(self, status: str = "draft", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        bg, fg = _COLOURS.get(status, ("#F5F5F5", "#212121"))
        self.setText(f" {status.upper()} ")
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            f"font-weight: bold; font-size: 11px; "
            f"border-radius: 4px; padding: 2px 8px;"
        )
