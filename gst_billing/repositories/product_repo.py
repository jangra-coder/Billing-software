"""Product repository — CRUD + search by category/HSN."""

from __future__ import annotations

import sqlite3

from models.product import Product
from repositories.base_repo import BaseRepository


class ProductRepo(BaseRepository):
    TABLE = "products"
    MODEL = Product

    def search(self, query: str, active_only: bool = True) -> list[Product]:
        pattern = f"%{query}%"
        sql = """
            SELECT * FROM products
            WHERE (category_name LIKE ? OR hsn_code LIKE ?)
        """
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY category_name"
        rows = self.conn.execute(sql, (pattern, pattern)).fetchall()
        return [self._row_to_model(r) for r in rows]

    def find_by_category(self, category_name: str) -> Product | None:
        row = self.conn.execute(
            "SELECT * FROM products WHERE category_name = ? AND is_active = 1",
            (category_name,),
        ).fetchone()
        return self._row_to_model(row) if row else None

    def soft_delete(self, product_id: int) -> None:
        self.conn.execute(
            "UPDATE products SET is_active = 0 WHERE id = ?",
            (product_id,),
        )
        self.conn.commit()
