"""Semantic control grounding compatibility layer."""

from typing import Optional

from .grounder import get_anchor as resolve_anchor


def get_anchor(app_name: str, anchor_name: str, default: Optional[list[int]] = None) -> list[int]:
    return resolve_anchor(app_name, anchor_name, default)
