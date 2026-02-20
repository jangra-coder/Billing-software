"""Indian date picker — displays DD/MM/YYYY, stores ISO internally."""

from __future__ import annotations

from datetime import date, datetime
from PyQt6.QtCore import pyqtSignal, QDate
from PyQt6.QtWidgets import QDateEdit, QWidget


class DatePicker(QDateEdit):
    """Wraps QDateEdit with DD/MM/YYYY display format and ISO helpers."""

    date_changed_iso = pyqtSignal(str)   # emits 'YYYY-MM-DD'

    def __init__(
        self,
        initial: date | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("dd/MM/yyyy")
        if initial:
            self.set_date(initial)
        else:
            self.setDate(QDate.currentDate())

        self.dateChanged.connect(self._on_changed)

    # ------------------------------------------------------------------
    def _on_changed(self, qdate: QDate) -> None:
        self.date_changed_iso.emit(qdate.toString("yyyy-MM-dd"))

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def set_date(self, d: date | str) -> None:
        if isinstance(d, str):
            if d:
                d = datetime.strptime(d, "%Y-%m-%d").date()
            else:
                d = date.today()
        self.setDate(QDate(d.year, d.month, d.day))

    def iso_date(self) -> str:
        """Return current date as 'YYYY-MM-DD'."""
        return self.date().toString("yyyy-MM-dd")
