"""Custom field definitions repository — manages dynamic attributes per entity type."""

from __future__ import annotations

import re
import sqlite3

from models.custom_field import CustomFieldDef
from repositories.base_repo import BaseRepository


# ── Built-in field definitions per entity type ───────────────────────
# (field_name, field_label, field_type, is_required)
PRODUCT_BUILTINS: list[tuple[str, str, str, bool]] = [
    ("category_name", "Category / Name", "text", True),
    ("hsn_code",      "HSN / SAC Code",  "text", False),
    ("gst_rate",      "GST Rate",        "number", False),
    ("default_rate",  "Default Rate",    "number", False),
]

CUSTOMER_BUILTINS: list[tuple[str, str, str, bool]] = [
    ("name",          "Customer / Contact Name", "text", True),
    ("company_name",  "Company / Business Name", "text", False),
    ("mobile",        "Mobile",                  "text", False),
    ("email",         "Email",                   "text", False),
    ("gstin",         "GSTIN",                   "text", False),
    ("pan",           "PAN",                     "text", False),
    ("address_line1", "Address Line 1",          "text", False),
    ("address_line2", "Address Line 2",          "text", False),
    ("address_line3", "Address Line 3",          "text", False),
    ("state_code",    "State Code (2-digit)",    "text", False),
    ("vendor_code",   "Vendor Code",             "text", False),
]

PURCHASE_BUILTINS: list[tuple[str, str, str, bool]] = [
    ("purchase_date", "Date",        "text",   True),
    ("invoice_no",    "Invoice #",   "text",   False),
    ("description",   "Description", "text",   False),
    ("amount",        "Amount",      "number", True),
    ("vendor_name",   "Vendor",      "text",   False),
    ("category",      "Category",    "text",   False),
    ("notes",         "Notes",       "text",   False),
]

_BUILTIN_MAP: dict[str, list[tuple[str, str, str, bool]]] = {
    "product":  PRODUCT_BUILTINS,
    "customer": CUSTOMER_BUILTINS,
    "purchase": PURCHASE_BUILTINS,
}


class CustomFieldRepo(BaseRepository):
    TABLE = "custom_field_definitions"
    MODEL = CustomFieldDef

    def list_for_entity(self, entity_type: str, active_only: bool = True) -> list[CustomFieldDef]:
        """Return all custom field definitions for an entity type, ordered by sort_order."""
        sql = "SELECT * FROM custom_field_definitions WHERE entity_type = ?"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY sort_order, id"
        rows = self.conn.execute(sql, (entity_type,)).fetchall()
        return [self._row_to_model(r) for r in rows]

    def find_by_name(self, entity_type: str, field_name: str) -> CustomFieldDef | None:
        """Look up a single field definition by entity + name."""
        row = self.conn.execute(
            "SELECT * FROM custom_field_definitions "
            "WHERE entity_type = ? AND field_name = ?",
            (entity_type, field_name),
        ).fetchone()
        return self._row_to_model(row) if row else None

    def ensure_field(self, entity_type: str, field_name: str,
                     field_label: str = "", field_type: str = "text",
                     is_builtin: bool = False, is_required: bool = False) -> CustomFieldDef:
        """Get or create a custom field definition.  Returns the definition."""
        existing = self.find_by_name(entity_type, field_name)
        if existing:
            # Re-activate if it was deactivated
            if not existing.is_active:
                self.conn.execute(
                    "UPDATE custom_field_definitions SET is_active = 1 WHERE id = ?",
                    (existing.id,),
                )
                self.conn.commit()
                existing.is_active = 1
            return existing
        # Derive label from field_name if not supplied
        if not field_label:
            field_label = field_name.replace("_", " ").title()
        # Determine next sort_order
        row = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM custom_field_definitions "
            "WHERE entity_type = ?",
            (entity_type,),
        ).fetchone()
        next_order = (row[0] if row else 0) + 1
        cfd = CustomFieldDef(
            entity_type=entity_type,
            field_name=field_name,
            field_label=field_label,
            field_type=field_type,
            sort_order=next_order,
            is_builtin=int(is_builtin),
            is_required=int(is_required),
        )
        new_id = self.insert(cfd)
        cfd.id = new_id
        return cfd

    def deactivate(self, field_id: int) -> bool:
        """Soft-delete a custom field definition. Returns False if field is required."""
        row = self.conn.execute(
            "SELECT is_required FROM custom_field_definitions WHERE id = ?",
            (field_id,),
        ).fetchone()
        if row and row[0]:
            return False  # Cannot deactivate required fields
        self.conn.execute(
            "UPDATE custom_field_definitions SET is_active = 0 WHERE id = ?",
            (field_id,),
        )
        self.conn.commit()
        return True

    def seed_builtins(self, entity_type: str) -> None:
        """Ensure all built-in field definitions exist for an entity type.

        Called once on dialog open / page init. Idempotent — skips fields
        that already have a row.
        """
        builtins = _BUILTIN_MAP.get(entity_type, [])
        for idx, (fname, flabel, ftype, required) in enumerate(builtins):
            existing = self.find_by_name(entity_type, fname)
            if existing:
                # Make sure is_builtin / is_required flags are set
                if not existing.is_builtin or (required and not existing.is_required):
                    self.conn.execute(
                        "UPDATE custom_field_definitions "
                        "SET is_builtin = 1, is_required = ? WHERE id = ?",
                        (int(required), existing.id),
                    )
                    self.conn.commit()
                continue
            cfd = CustomFieldDef(
                entity_type=entity_type,
                field_name=fname,
                field_label=flabel,
                field_type=ftype,
                sort_order=idx,
                is_builtin=1,
                is_required=int(required),
            )
            self.insert(cfd)

    def active_builtin_names(self, entity_type: str) -> set[str]:
        """Return the set of *active* built-in field_names for an entity type."""
        self.seed_builtins(entity_type)
        rows = self.conn.execute(
            "SELECT field_name FROM custom_field_definitions "
            "WHERE entity_type = ? AND is_builtin = 1 AND is_active = 1",
            (entity_type,),
        ).fetchall()
        return {r[0] for r in rows}

    def reorder(self, field_ids: list[int]) -> None:
        """Set sort_order based on position in the list."""
        cur = self.conn.cursor()
        for idx, fid in enumerate(field_ids):
            cur.execute(
                "UPDATE custom_field_definitions SET sort_order = ? WHERE id = ?",
                (idx + 1, fid),
            )
        self.conn.commit()

    @staticmethod
    def to_field_name(label: str) -> str:
        """Convert a human label to a safe snake_case field_name."""
        text = label.strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text
