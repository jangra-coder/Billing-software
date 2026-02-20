"""Purchase repository — expense register CRUD + filtering."""

from __future__ import annotations

import sqlite3

from models.purchase import Purchase
from repositories.base_repo import BaseRepository


class PurchaseRepo(BaseRepository):
    TABLE = "purchases"
    MODEL = Purchase

    def list_filtered(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        vendor: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Purchase]:
        sql = "SELECT * FROM purchases WHERE 1=1"
        params: list = []

        if date_from:
            sql += " AND purchase_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND purchase_date <= ?"
            params.append(date_to)
        if vendor:
            sql += " AND vendor_name LIKE ?"
            params.append(f"%{vendor}%")
        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY purchase_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_model(r) for r in rows]

    def sum_filtered(self, **kwargs) -> int:
        """Total amount (paise) matching the same filters as list_filtered."""
        sql = "SELECT COALESCE(SUM(amount), 0) FROM purchases WHERE 1=1"
        params: list = []
        for key, col in (("date_from", "purchase_date"), ("date_to", "purchase_date"),
                         ("vendor", "vendor_name"), ("category", "category")):
            val = kwargs.get(key)
            if val:
                if key == "date_from":
                    sql += f" AND {col} >= ?"
                elif key == "date_to":
                    sql += f" AND {col} <= ?"
                elif key == "vendor":
                    sql += f" AND {col} LIKE ?"
                    val = f"%{val}%"
                else:
                    sql += f" AND {col} = ?"
                params.append(val)
        row = self.conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    def distinct_vendors(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT vendor_name FROM purchases "
            "WHERE vendor_name != '' ORDER BY vendor_name"
        ).fetchall()
        return [r[0] for r in rows]

    def sum_by_category(
        self, date_from: str | None = None, date_to: str | None = None
    ) -> list[tuple[str, int]]:
        """Return [(category, total_paise), ...] for the period."""
        sql = (
            "SELECT category, COALESCE(SUM(amount), 0) "
            "FROM purchases WHERE 1=1"
        )
        params: list = []
        if date_from:
            sql += " AND purchase_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND purchase_date <= ?"
            params.append(date_to)
        sql += " GROUP BY category ORDER BY SUM(amount) DESC"
        return self.conn.execute(sql, params).fetchall()
