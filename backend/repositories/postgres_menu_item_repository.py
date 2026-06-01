from __future__ import annotations

from typing import Any

from backend.db.connection import get_connection
from backend.schemas.vendor_self import MenuItem


class PostgresMenuItemRepository:
    def create(
        self,
        *,
        vendor_id: int,
        name: str,
        price_cents: int,
        description: str | None = None,
        category_id: int | None = None,
        available: bool = True,
        daily_quota: int | None = None,
        dietary_tags: list[str] | None = None,
    ) -> MenuItem:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO menu_items (
                    vendor_id, category_id, name, description,
                    price_cents, available, daily_quota, dietary_tags
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    id, vendor_id, category_id, name, description,
                    price_cents, available, daily_quota, dietary_tags, photo_path,
                    created_at, updated_at
                """,
                (
                    vendor_id,
                    category_id,
                    name,
                    description,
                    price_cents,
                    available,
                    daily_quota,
                    dietary_tags or [],
                ),
            ).fetchone()

        return MenuItem(**dict(row))

    def list(
        self,
        *,
        vendor_id: int,
        category_id: int | None = None,
        available: bool | None = None,
    ) -> list[MenuItem]:
        where = ["vendor_id = %s"]
        values: list[Any] = [vendor_id]

        if category_id is not None:
            where.append("category_id = %s")
            values.append(category_id)
        if available is not None:
            where.append("available = %s")
            values.append(available)

        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    id, vendor_id, category_id, name, description,
                    price_cents, available, daily_quota, dietary_tags, photo_path,
                    created_at, updated_at
                FROM menu_items
                WHERE {" AND ".join(where)}
                ORDER BY id
                """,
                values,
            ).fetchall()

        return [MenuItem(**dict(row)) for row in rows]

    def get(self, *, vendor_id: int, item_id: int) -> MenuItem | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    id, vendor_id, category_id, name, description,
                    price_cents, available, daily_quota, dietary_tags, photo_path,
                    created_at, updated_at
                FROM menu_items
                WHERE vendor_id = %s AND id = %s
                """,
                (vendor_id, item_id),
            ).fetchone()

        if row is None:
            return None
        return MenuItem(**dict(row))

    def update(
        self, *, vendor_id: int, item_id: int, fields: dict[str, Any]
    ) -> MenuItem | None:
        allowed_columns = {
            "category_id": "category_id",
            "name": "name",
            "description": "description",
            "price_cents": "price_cents",
            "available": "available",
            "daily_quota": "daily_quota",
            "dietary_tags": "dietary_tags",
        }
        updates = [
            (allowed_columns[key], value)
            for key, value in fields.items()
            if key in allowed_columns
        ]
        if not updates:
            return self.get(vendor_id=vendor_id, item_id=item_id)

        assignments = [f"{column} = %s" for column, _ in updates]
        values = [value for _, value in updates]
        values.extend([vendor_id, item_id])

        with get_connection() as conn:
            row = conn.execute(
                f"""
                UPDATE menu_items
                SET {", ".join(assignments)}, updated_at = NOW()
                WHERE vendor_id = %s AND id = %s
                RETURNING
                    id, vendor_id, category_id, name, description,
                    price_cents, available, daily_quota, dietary_tags, photo_path,
                    created_at, updated_at
                """,
                values,
            ).fetchone()

        if row is None:
            return None
        return MenuItem(**dict(row))

    def delete(self, *, vendor_id: int, item_id: int) -> bool:
        with get_connection() as conn:
            result = conn.execute(
                """
                DELETE FROM menu_items
                WHERE vendor_id = %s AND id = %s
                """,
                (vendor_id, item_id),
            )

        return result.rowcount > 0

    def set_photo_path(self, *, vendor_id: int, item_id: int, photo_path: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE menu_items
                SET photo_path = %s, updated_at = NOW()
                WHERE vendor_id = %s AND id = %s
                """,
                (photo_path, vendor_id, item_id),
            )

    def clear_photo_path(self, *, vendor_id: int, item_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE menu_items
                SET photo_path = NULL, updated_at = NOW()
                WHERE vendor_id = %s AND id = %s
                """,
                (vendor_id, item_id),
            )

    def has_items_in_category(self, *, vendor_id: int, category_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM menu_items
                WHERE vendor_id = %s AND category_id = %s
                LIMIT 1
                """,
                (vendor_id, category_id),
            ).fetchone()

        return row is not None
