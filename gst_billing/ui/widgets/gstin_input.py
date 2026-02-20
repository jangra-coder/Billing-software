"""GSTIN input with live formatting and validation badge."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLineEdit, QHBoxLayout, QLabel, QWidget

from services.validator import validate_gstin
from services.gst_engine import extract_state_code_from_gstin


class GSTINInput(QWidget):
    """Line-edit that validates GSTIN format and emits state code."""

    gstin_changed = pyqtSignal(str)        # cleaned GSTIN
    state_code_detected = pyqtSignal(str)  # 2-char code

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("15-character GSTIN")
        self._edit.setMaxLength(15)
        layout.addWidget(self._edit)

        self._badge = QLabel()
        self._badge.setFixedWidth(28)
        layout.addWidget(self._badge)

        self._edit.textChanged.connect(self._on_text_changed)

    # ------------------------------------------------------------------
    def _on_text_changed(self, text: str) -> None:
        clean = text.strip().upper()
        if clean != text:
            self._edit.blockSignals(True)
            self._edit.setText(clean)
            self._edit.blockSignals(False)

        if not clean:
            self._badge.setText("")
            self.gstin_changed.emit("")
            return

        ok, _ = validate_gstin(clean)
        self._badge.setText("✅" if ok else "❌")
        self.gstin_changed.emit(clean)

        if ok:
            code = extract_state_code_from_gstin(clean)
            if code:
                self.state_code_detected.emit(code)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def text(self) -> str:
        return self._edit.text().strip().upper()

    def setText(self, t: str) -> None:
        self._edit.setText(t)

    def clear(self) -> None:
        self._edit.clear()
