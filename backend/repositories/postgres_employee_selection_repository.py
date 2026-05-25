from __future__ import annotations

from backend.db.connection import get_connection
from backend.schemas.employee import MealSelection


def _to_schema(row) -> MealSelection:
    d = dict(row)
    d["total_price_cents"] = d["quantity"] * d["unit_price_cents"]
    return MealSelection(**d)


class PostgresEmployeeSelectionRepository:
    def create(
        self,
        *,
        employee_id: int,
        vendor_id: int,
        item_id: int,
        item_name: str,
        quantity: int,
        unit_price_cents: int,
    ) -> MealSelection:
        with get_connection() as conn:
            row = conn.execute(
                """
                INSERT INTO meal_selections
                    (employee_id, vendor_id, item_id, item_name, quantity, unit_price_cents)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, employee_id, vendor_id, item_id, item_name,
                          quantity, unit_price_cents, created_at
                """,
                (employee_id, vendor_id, item_id, item_name, quantity, unit_price_cents),
            ).fetchone()
        return _to_schema(row)

    def list(self, *, employee_id: int) -> list[MealSelection]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, employee_id, vendor_id, item_id, item_name,
                       quantity, unit_price_cents, created_at
                FROM meal_selections
                WHERE employee_id = %s
                ORDER BY id
                """,
                (employee_id,),
            ).fetchall()
        return [_to_schema(r) for r in rows]

    def list_by_vendor(self, *, vendor_id: int) -> list[MealSelection]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, employee_id, vendor_id, item_id, item_name,
                       quantity, unit_price_cents, created_at
                FROM meal_selections
                WHERE vendor_id = %s
                ORDER BY id
                """,
                (vendor_id,),
            ).fetchall()
        return [_to_schema(r) for r in rows]
