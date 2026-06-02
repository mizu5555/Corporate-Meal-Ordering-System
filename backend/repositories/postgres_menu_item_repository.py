from __future__ import annotations

from datetime import date
from typing import Any

from backend.db.connection import get_connection
from backend.schemas.vendor_self import MenuItem, MenuItemDateOverride


class PostgresMenuItemRepository:
    # ── item CRUD ──────────────────────────────────────────────────────────────

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

    # ── per-date effective reads ────────────────────────────────────────────────

    def list_effective(
        self,
        *,
        vendor_id: int,
        meal_date: date,
        category_id: int | None = None,
        available: bool | None = None,
    ) -> list[MenuItem]:
        """Return items with per-date overrides merged in (COALESCE at DB level)."""
        where = ["mi.vendor_id = %s"]
        values: list[Any] = [meal_date, vendor_id]

        if category_id is not None:
            where.append("mi.category_id = %s")
            values.append(category_id)
        if available is not None:
            where.append("COALESCE(o.available, mi.available) = %s")
            values.append(available)

        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    mi.id, mi.vendor_id, mi.category_id, mi.name, mi.description,
                    COALESCE(o.price_cents, mi.price_cents) AS price_cents,
                    COALESCE(o.available, mi.available)     AS available,
                    COALESCE(o.daily_quota, mi.daily_quota) AS daily_quota,
                    COALESCE(o.is_recommended, FALSE)       AS is_recommended,
                    mi.dietary_tags, mi.photo_path, mi.created_at, mi.updated_at
                FROM menu_items mi
                LEFT JOIN menu_item_date_overrides o
                    ON o.item_id = mi.id AND o.meal_date = %s
                WHERE {" AND ".join(where)}
                ORDER BY mi.id
                """,
                values,
            ).fetchall()

        return [MenuItem(**dict(row)) for row in rows]

    def get_effective(
        self,
        *,
        vendor_id: int,
        item_id: int,
        meal_date: date,
    ) -> MenuItem | None:
        """Return a single item with any per-date override merged in."""
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    mi.id, mi.vendor_id, mi.category_id, mi.name, mi.description,
                    COALESCE(o.price_cents, mi.price_cents) AS price_cents,
                    COALESCE(o.available, mi.available)     AS available,
                    COALESCE(o.daily_quota, mi.daily_quota) AS daily_quota,
                    COALESCE(o.is_recommended, FALSE)       AS is_recommended,
                    mi.dietary_tags, mi.photo_path, mi.created_at, mi.updated_at
                FROM menu_items mi
                LEFT JOIN menu_item_date_overrides o
                    ON o.item_id = mi.id AND o.meal_date = %s
                WHERE mi.vendor_id = %s AND mi.id = %s
                """,
                (meal_date, vendor_id, item_id),
            ).fetchone()

        if row is None:
            return None
        return MenuItem(**dict(row))

    # ── date override CRUD ─────────────────────────────────────────────────────

    def list_date_overrides(self, *, vendor_id: int, item_id: int) -> list[MenuItemDateOverride]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT o.item_id, o.meal_date, o.available, o.daily_quota,
                       o.price_cents, o.is_recommended, o.created_at, o.updated_at
                FROM menu_item_date_overrides o
                JOIN menu_items mi ON mi.id = o.item_id
                WHERE mi.vendor_id = %s AND o.item_id = %s
                ORDER BY o.meal_date
                """,
                (vendor_id, item_id),
            ).fetchall()
        return [MenuItemDateOverride(**dict(row)) for row in rows]

    def get_date_override(
        self, *, vendor_id: int, item_id: int, meal_date: date
    ) -> MenuItemDateOverride | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT o.item_id, o.meal_date, o.available, o.daily_quota,
                       o.price_cents, o.is_recommended, o.created_at, o.updated_at
                FROM menu_item_date_overrides o
                JOIN menu_items mi ON mi.id = o.item_id
                WHERE mi.vendor_id = %s AND o.item_id = %s AND o.meal_date = %s
                """,
                (vendor_id, item_id, meal_date),
            ).fetchone()
        if row is None:
            return None
        return MenuItemDateOverride(**dict(row))

    def upsert_date_override(
        self,
        *,
        vendor_id: int,
        item_id: int,
        meal_date: date,
        available: bool | None,
        daily_quota: int | None,
        price_cents: int | None,
        is_recommended: bool | None = None,
    ) -> MenuItemDateOverride:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO menu_item_date_overrides
                    (item_id, meal_date, available, daily_quota, price_cents, is_recommended)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (item_id, meal_date) DO UPDATE SET
                    available    = EXCLUDED.available,
                    daily_quota  = EXCLUDED.daily_quota,
                    price_cents  = EXCLUDED.price_cents,
                    is_recommended = EXCLUDED.is_recommended,
                    updated_at   = NOW()
                RETURNING item_id, meal_date, available, daily_quota,
                          price_cents, is_recommended, created_at, updated_at
                """,
                (item_id, meal_date, available, daily_quota, price_cents, is_recommended),
            ).fetchone()
            conn.commit()
        return MenuItemDateOverride(**dict(row))

    def delete_date_override(
        self, *, vendor_id: int, item_id: int, meal_date: date
    ) -> bool:
        with get_connection() as conn:
            result = conn.execute(
                """
                DELETE FROM menu_item_date_overrides
                WHERE item_id = %s AND meal_date = %s
                  AND item_id IN (
                      SELECT id FROM menu_items WHERE vendor_id = %s
                  )
                """,
                (item_id, meal_date, vendor_id),
            )
            conn.commit()
        return result.rowcount > 0
