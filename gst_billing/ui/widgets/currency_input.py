"""Currency input widget — ₹ formatted, returns integer paise."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import QLineEdit, QWidget


class CurrencyInput(QLineEdit):
    """A line-edit that accepts decimal rupee values and emits integer paise."""

    value_changed = pyqtSignal(int)  # paise

    def __init__(
        self,
        symbol: str = "₹",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._symbol = symbol
        self.setPlaceholderText(f"{symbol}0.00")
        self.setAlignment(Qt.AlignmentFlag.AlignRight)

        validator = QDoubleValidator(0.0, 999_999_999.99, 2, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.setValidator(validator)

        self.editingFinished.connect(self._on_finished)

    # ------------------------------------------------------------------
    def _on_finished(self) -> None:
        paise = self.paise()
        self.value_changed.emit(paise)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def paise(self) -> int:
        """Return the current value as integer paise."""
        text = self.text().replace(self._symbol, "").replace(",", "").strip()
        if not text:
            return 0
        try:
            d = Decimal(text).quantize(Decimal("0.01"), ROUND_HALF_UP)
            return int(d * 100)
        except (InvalidOperation, ValueError):
            return 0

    def set_paise(self, paise: int) -> None:
        """Set the display from an integer paise value."""
        rupees = paise / 100
        self.setText(f"{rupees:.2f}")

    def set_rupees(self, rupees: float) -> None:
        self.setText(f"{rupees:.2f}")
