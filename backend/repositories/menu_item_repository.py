"""Placeholder — Task 9 replaces this with the full implementation.

Only `has_items_in_category` is needed in T8 for the categories DELETE 409 check.
The internal `_rows` dict-of-dict is intentionally minimal so this placeholder
can be replaced wholesale in T9 without callers caring about its shape.
"""
from __future__ import annotations


class MenuItemRepository:
    def __init__(self) -> None:
        self._rows: dict[int, dict] = {}

    def has_items_in_category(self, *, vendor_id: int, category_id: int) -> bool:
        """Return True if any menu item in the given vendor scope still references the category."""
        return any(
            r["vendor_id"] == vendor_id and r["category_id"] == category_id
            for r in self._rows.values()
        )
