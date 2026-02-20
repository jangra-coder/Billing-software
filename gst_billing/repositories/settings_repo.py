"""Lightweight repositories for lookup / config tables."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

from models.state import State


class StateMasterRepo:
    """Read-only state master."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list_all(self) -> list[State]:
        rows = self.conn.execute(
            "SELECT code, state_name FROM state_master ORDER BY code"
        ).fetchall()
        return [State(code=r[0], state_name=r[1]) for r in rows]

    def get_by_code(self, code: str) -> State | None:
        row = self.conn.execute(
            "SELECT code, state_name FROM state_master WHERE code = ?",
            (code,),
        ).fetchone()
        return State(code=row[0], state_name=row[1]) if row else None

    def get_name(self, code: str) -> str:
        """Quick lookup: code → state_name.  Returns '' if not found."""
        state = self.get_by_code(code)
        return state.state_name if state else ""


class TermsConditionsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_for_type(self, doc_type: str) -> tuple[str, bool]:
        """Return (tc_text, is_enabled) for the given document type."""
        row = self.conn.execute(
            "SELECT tc_text, is_enabled FROM terms_conditions "
            "WHERE document_type = ?",
            (doc_type,),
        ).fetchone()
        if row is None:
            return ("", True)
        return (row[0] or "", bool(row[1]))

    def save(self, doc_type: str, tc_text: str, is_enabled: bool = True) -> None:
        self.conn.execute(
            "UPDATE terms_conditions SET tc_text = ?, is_enabled = ? "
            "WHERE document_type = ?",
            (tc_text, int(is_enabled), doc_type),
        )
        self.conn.commit()

    def list_all(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT document_type, tc_text, is_enabled FROM terms_conditions"
        ).fetchall()
        return [
            {"document_type": r[0], "tc_text": r[1] or "", "is_enabled": bool(r[2])}
            for r in rows
        ]


class DocTypeConfigRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list_enabled(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM doc_type_config WHERE is_enabled = 1 "
            "ORDER BY sort_order"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_all(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM doc_type_config ORDER BY sort_order"
        ).fetchall()
        return [dict(r) for r in rows]

    def get(self, code: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM doc_type_config WHERE code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None

    def save(self, data: dict) -> None:
        code = data["code"]
        existing = self.get(code)
        if existing:
            sets = ", ".join(
                f"{k} = ?" for k in data.keys() if k != "code"
            )
            vals = [v for k, v in data.items() if k != "code"]
            self.conn.execute(
                f"UPDATE doc_type_config SET {sets} WHERE code = ?",
                (*vals, code),
            )
        else:
            cols = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            self.conn.execute(
                f"INSERT INTO doc_type_config ({cols}) VALUES ({placeholders})",
                tuple(data.values()),
            )
        self.conn.commit()


class PdfTemplateRepo:
    """Singleton pdf_template_settings row."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self) -> dict:
        row = self.conn.execute(
            "SELECT * FROM pdf_template_settings WHERE id = 1"
        ).fetchone()
        return dict(row) if row else {}

    def save(self, data: dict) -> None:
        data.pop("id", None)
        data.pop("updated_at", None)
        sets = ", ".join(f"{k} = ?" for k in data.keys())
        self.conn.execute(
            f"UPDATE pdf_template_settings SET {sets}, "
            f"updated_at = datetime('now') WHERE id = 1",
            tuple(data.values()),
        )
        self.conn.commit()

    def get_copy_types(self) -> list[str]:
        row = self.get()
        raw = row.get("copy_types_json", "[]")
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return ["Original for Recipient"]


class AppSettingsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, key: str, default: str = "") -> str:
        row = self.conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def set(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def get_all(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {r[0]: r[1] for r in rows}


class PurchaseCategoryRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list_active(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM purchase_categories "
            "WHERE is_active = 1 ORDER BY sort_order"
        ).fetchall()
        return [r[0] for r in rows]

    def add(self, name: str) -> None:
        max_order = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM purchase_categories"
        ).fetchone()[0]
        self.conn.execute(
            "INSERT OR IGNORE INTO purchase_categories (name, sort_order) "
            "VALUES (?, ?)",
            (name, max_order + 1),
        )
        self.conn.commit()
