"""Product dataclass — service/product category with HSN code."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Product:
    id: int | None = None
    category_name: str = ""
    hsn_code: str = ""
    default_rate: int = 0       # Paise
    gst_rate: float = 18.0      # Percentage
    is_active: int = 1
    custom_fields: str = "{}"   # JSON dict of custom attributes
    created_at: str = ""
