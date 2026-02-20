"""Reusable search bar with clear button."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QLineEdit, QHBoxLayout, QPushButton, QWidget


class SearchBar(QWidget):
    """Search bar that emits *search_changed* after a short debounce."""

    search_changed = pyqtSignal(str)

    def __init__(
        self,
        placeholder: str = "Search…",
        debounce_ms: int = 300,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(debounce_ms)
        self._debounce.timeout.connect(self._emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(f"🔍 {placeholder}")
        self._edit.setClearButtonEnabled(True)
        self._edit.textChanged.connect(lambda _: self._debounce.start())
        layout.addWidget(self._edit)

    # ------------------------------------------------------------------
    def _emit(self) -> None:
        self.search_changed.emit(self._edit.text().strip())

    def text(self) -> str:
        return self._edit.text().strip()

    def clear(self) -> None:
        self._edit.clear()
