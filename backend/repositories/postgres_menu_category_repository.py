from __future__ import annotations

from typing import Any

from backend.db.connection import get_connection
from backend.schemas.vendor_self import Category


class PostgresMenuCategoryRepository:
    def create(self, *, vendor_id: int, name: str, sort_order: int = 0) -> Category:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO menu_categories (vendor_id, name, sort_order)
                VALUES (%s, %s, %s)
                RETURNING id, vendor_id, name, sort_order, created_at
                """,
                (vendor_id, name, sort_order),
            ).fetchone()

        return Category(**dict(row))

    def list(self, *, vendor_id: int) -> list[Category]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, vendor_id, name, sort_order, created_at
                FROM menu_categories
                WHERE vendor_id = %s
                ORDER BY sort_order, id
                """,
                (vendor_id,),
            ).fetchall()

        return [Category(**dict(row)) for row in rows]

    def get(self, *, vendor_id: int, category_id: int) -> Category | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, vendor_id, name, sort_order, created_at
                FROM menu_categories
                WHERE vendor_id = %s AND id = %s
                """,
                (vendor_id, category_id),
            ).fetchone()

        if row is None:
            return None
        return Category(**dict(row))

    def update(
        self, *, vendor_id: int, category_id: int, fields: dict[str, Any]
    ) -> Category | None:
        allowed_columns = {
            "name": "name",
            "sort_order": "sort_order",
        }
        updates = [
            (allowed_columns[key], value)
            for key, value in fields.items()
            if key in allowed_columns and value is not None
        ]
        if not updates:
            return self.get(vendor_id=vendor_id, category_id=category_id)

        assignments = [f"{column} = %s" for column, _ in updates]
        values = [value for _, value in updates]
        values.extend([vendor_id, category_id])

        with get_connection() as conn:
            row = conn.execute(
                f"""
                UPDATE menu_categories
                SET {", ".join(assignments)}
                WHERE vendor_id = %s AND id = %s
                RETURNING id, vendor_id, name, sort_order, created_at
                """,
                values,
            ).fetchone()

        if row is None:
            return None
        return Category(**dict(row))

    def delete(self, *, vendor_id: int, category_id: int) -> bool:
        with get_connection() as conn:
            result = conn.execute(
                """
                DELETE FROM menu_categories
                WHERE vendor_id = %s AND id = %s
                """,
                (vendor_id, category_id),
            )

        return result.rowcount > 0
