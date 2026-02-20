"""CompanyProfile repository — singleton row CRUD."""

from __future__ import annotations

import sqlite3

from models.company import CompanyProfile
from repositories.base_repo import BaseRepository


class CompanyRepo(BaseRepository):
    TABLE = "company_profile"
    MODEL = CompanyProfile

    def get(self) -> CompanyProfile:
        """Return the single company profile row."""
        row = self.conn.execute(
            "SELECT * FROM company_profile WHERE id = 1"
        ).fetchone()
        if row is None:
            # Should not happen after seed, but be safe
            return CompanyProfile()
        return self._row_to_model(row)

    def save(self, profile: CompanyProfile) -> None:
        """Upsert the singleton row."""
        profile.id = 1
        d = {
            k: v for k, v in profile.__dict__.items()
            if k not in ("id", "updated_at")
        }
        set_clause = ", ".join(f"{k} = ?" for k in d.keys())
        self.conn.execute(
            f"UPDATE company_profile SET {set_clause}, "
            f"updated_at = datetime('now') WHERE id = 1",
            tuple(d.values()),
        )
        self.conn.commit()
