"""State dataclass."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class State:
    code: str = ""
    state_name: str = ""
