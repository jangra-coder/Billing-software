"""
Abstract base repository — DRY CRUD helpers.

Every concrete repo inherits from this and gets get_by_id, insert,
update, delete, and list_all for free.  Override or extend as needed.
"""

from __future__ import annotations

import sqlite3
from dataclasses import fields, asdict
from typing import TypeVar, Type, Sequence

T = TypeVar("T")


class BaseRepository:
    TABLE: str = ""
    MODEL: Type | None = None

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # -- helpers --------------------------------------------------------------

    def _row_to_model(self, row: sqlite3.Row) -> object:
        """Convert a sqlite3.Row to the repository's dataclass."""
        if self.MODEL is None:
            raise NotImplementedError("Set MODEL on the subclass")
        field_names = {f.name for f in fields(self.MODEL)}
        kwargs = {k: row[k] for k in row.keys() if k in field_names}
        return self.MODEL(**kwargs)

    # -- CRUD -----------------------------------------------------------------

    def get_by_id(self, row_id: int) -> object | None:
        row = self.conn.execute(
            f"SELECT * FROM {self.TABLE} WHERE id = ?", (row_id,)
        ).fetchone()
        return self._row_to_model(row) if row else None

    def list_all(self, active_only: bool = False) -> list:
        sql = f"SELECT * FROM {self.TABLE}"
        if active_only and "is_active" in {f.name for f in fields(self.MODEL)}:
            sql += " WHERE is_active = 1"
        rows = self.conn.execute(sql).fetchall()
        return [self._row_to_model(r) for r in rows]

    def insert(self, obj: object) -> int:
        d = asdict(obj)
        d.pop("id", None)  # auto-increment
        # Remove empty timestamps so SQLite defaults kick in
        for ts in ("created_at", "updated_at", "applied_at"):
            if ts in d and not d[ts]:
                d.pop(ts)
        cols = ", ".join(d.keys())
        placeholders = ", ".join("?" for _ in d)
        cur = self.conn.execute(
            f"INSERT INTO {self.TABLE} ({cols}) VALUES ({placeholders})",
            tuple(d.values()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, obj: object) -> None:
        d = asdict(obj)
        row_id = d.pop("id")
        if row_id is None:
            raise ValueError("Cannot update without an id")
        # Refresh updated_at
        for ts in ("updated_at",):
            if ts in d:
                d[ts] = ""  # will be ignored; set via trigger or manual SQL
        set_clause = ", ".join(f"{k} = ?" for k in d.keys())
        self.conn.execute(
            f"UPDATE {self.TABLE} SET {set_clause}, "
            f"updated_at = datetime('now') WHERE id = ?",
            (*d.values(), row_id),
        )
        self.conn.commit()

    def delete(self, row_id: int) -> None:
        self.conn.execute(
            f"DELETE FROM {self.TABLE} WHERE id = ?", (row_id,)
        )
        self.conn.commit()

    def count(self) -> int:
        row = self.conn.execute(
            f"SELECT COUNT(*) FROM {self.TABLE}"
        ).fetchone()
        return row[0] if row else 0
