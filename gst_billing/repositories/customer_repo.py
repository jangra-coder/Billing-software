"""Customer repository — full CRUD + search."""

from __future__ import annotations

import sqlite3

from models.customer import Customer
from repositories.base_repo import BaseRepository


class CustomerRepo(BaseRepository):
    TABLE = "customers"
    MODEL = Customer

    def search(self, query: str, active_only: bool = True) -> list[Customer]:
        """Case-insensitive search across name, company_name, gstin, mobile."""
        pattern = f"%{query}%"
        sql = """
            SELECT * FROM customers
            WHERE (name LIKE ? OR company_name LIKE ?
                   OR gstin LIKE ? OR mobile LIKE ?)
        """
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY name LIMIT 50"
        rows = self.conn.execute(
            sql, (pattern, pattern, pattern, pattern)
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def find_by_gstin(self, gstin: str) -> Customer | None:
        row = self.conn.execute(
            "SELECT * FROM customers WHERE gstin = ? AND is_active = 1",
            (gstin,),
        ).fetchone()
        return self._row_to_model(row) if row else None

    def soft_delete(self, customer_id: int) -> None:
        self.conn.execute(
            "UPDATE customers SET is_active = 0, "
            "updated_at = datetime('now') WHERE id = ?",
            (customer_id,),
        )
        self.conn.commit()
