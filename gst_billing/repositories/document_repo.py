"""Document + DocumentItem repository — the core invoice CRUD."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, fields

from models.document import Document, DocumentItem
from repositories.base_repo import BaseRepository


class DocumentRepo(BaseRepository):
    TABLE = "documents"
    MODEL = Document

    # -- Read -----------------------------------------------------------------

    def get_with_items(self, doc_id: int) -> Document | None:
        """Load a document and all its line items."""
        doc = self.get_by_id(doc_id)
        if doc is None:
            return None
        doc.items = self._get_items(doc_id)
        return doc

    def find_by_number(self, doc_number: str) -> Document | None:
        row = self.conn.execute(
            "SELECT * FROM documents WHERE document_number = ?",
            (doc_number,),
        ).fetchone()
        return self._row_to_model(row) if row else None

    def list_filtered(
        self,
        doc_type: str | None = None,
        status: str | None = None,
        customer_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        """Filtered listing with pagination."""
        sql = "SELECT * FROM documents WHERE 1=1"
        params: list = []

        if doc_type:
            sql += " AND document_type = ?"
            params.append(doc_type)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if customer_id:
            sql += " AND customer_id = ?"
            params.append(customer_id)
        if date_from:
            sql += " AND document_date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND document_date <= ?"
            params.append(date_to)
        if search:
            pattern = f"%{search}%"
            sql += (
                " AND (document_number LIKE ? OR customer_name LIKE ?"
                " OR amount_in_words LIKE ?)"
            )
            params.extend([pattern, pattern, pattern])

        sql += " ORDER BY document_date DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_model(r) for r in rows]

    def count_filtered(self, **kwargs) -> int:
        """Count for pagination (mirrors list_filtered filters)."""
        sql = "SELECT COUNT(*) FROM documents WHERE 1=1"
        params: list = []
        for key in ("doc_type", "status", "customer_id", "date_from", "date_to"):
            val = kwargs.get(key)
            if val:
                col_map = {
                    "doc_type": "document_type",
                    "status": "status",
                    "customer_id": "customer_id",
                    "date_from": "document_date",
                    "date_to": "document_date",
                }
                col = col_map[key]
                op = ">=" if key == "date_from" else ("<=" if key == "date_to" else "=")
                sql += f" AND {col} {op} ?"
                params.append(val)
        row = self.conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    # -- Write ----------------------------------------------------------------

    def save_with_items(self, doc: Document) -> int:
        """Insert or update a document and its line items atomically."""
        cur = self.conn.cursor()
        try:
            if doc.id is None:
                # Insert document
                doc_id = self._insert_doc(cur, doc)
            else:
                doc_id = doc.id
                self._update_doc(cur, doc)
                # Remove old items then re-insert
                cur.execute(
                    "DELETE FROM document_items WHERE document_id = ?",
                    (doc_id,),
                )

            # Insert items
            for idx, item in enumerate(doc.items, start=1):
                item.document_id = doc_id
                item.serial_no = idx
                self._insert_item(cur, item)

            self.conn.commit()
            return doc_id
        except Exception:
            self.conn.rollback()
            raise

    def update_status(self, doc_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE documents SET status = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (status, doc_id),
        )
        self.conn.commit()

    # -- Private helpers ------------------------------------------------------

    def _get_items(self, doc_id: int) -> list[DocumentItem]:
        rows = self.conn.execute(
            "SELECT * FROM document_items WHERE document_id = ? "
            "ORDER BY serial_no",
            (doc_id,),
        ).fetchall()
        item_fields = {f.name for f in fields(DocumentItem)}
        return [
            DocumentItem(**{k: r[k] for k in r.keys() if k in item_fields})
            for r in rows
        ]

    def _insert_doc(self, cur: sqlite3.Cursor, doc: Document) -> int:
        d = asdict(doc)
        d.pop("id", None)
        d.pop("items", None)
        for ts in ("created_at", "updated_at"):
            if ts in d and not d[ts]:
                d.pop(ts)
        cols = ", ".join(d.keys())
        placeholders = ", ".join("?" for _ in d)
        cur.execute(
            f"INSERT INTO documents ({cols}) VALUES ({placeholders})",
            tuple(d.values()),
        )
        return cur.lastrowid

    def _update_doc(self, cur: sqlite3.Cursor, doc: Document) -> None:
        d = asdict(doc)
        row_id = d.pop("id")
        d.pop("items", None)
        d.pop("created_at", None)
        d.pop("updated_at", None)
        set_clause = ", ".join(f"{k} = ?" for k in d.keys())
        cur.execute(
            f"UPDATE documents SET {set_clause}, "
            f"updated_at = datetime('now') WHERE id = ?",
            (*d.values(), row_id),
        )

    def _insert_item(self, cur: sqlite3.Cursor, item: DocumentItem) -> None:
        d = asdict(item)
        d.pop("id", None)
        for ts in ("created_at",):
            if ts in d and not d[ts]:
                d.pop(ts)
        cols = ", ".join(d.keys())
        placeholders = ", ".join("?" for _ in d)
        cur.execute(
            f"INSERT INTO document_items ({cols}) VALUES ({placeholders})",
            tuple(d.values()),
        )
