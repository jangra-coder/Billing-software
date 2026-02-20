"""Custom field definition dataclass."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class CustomFieldDef:
    """Defines one custom attribute for an entity type (product/customer/purchase)."""
    id: int | None = None
    entity_type: str = ""       # "product", "customer", "purchase"
    field_name: str = ""        # snake_case key used in JSON, e.g. "color"
    field_label: str = ""       # Display label, e.g. "Color"
    field_type: str = "text"    # "text" or "number"
    sort_order: int = 0
    is_active: int = 1
    is_builtin: int = 0         # 1 = built-in field (column on the table, not JSON)
    is_required: int = 0        # 1 = cannot be deactivated by user
    created_at: str = ""
