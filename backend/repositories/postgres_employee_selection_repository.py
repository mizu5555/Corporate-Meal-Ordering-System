from __future__ import annotations

from datetime import date

from backend.db.connection import get_connection
from backend.repositories.employee_selection_repository import OrderItemSnapshot
from backend.schemas.employee import EmployeeOrder, EmployeeOrderItem, MealSelection


def _selection_to_schema(row) -> MealSelection:
    d = dict(row)
    d["total_price_cents"] = d["quantity"] * d["unit_price_cents"]
    return MealSelection(**d)


def _order_item_to_schema(row) -> EmployeeOrderItem:
    return EmployeeOrderItem(**dict(row))


def _order_to_schema(order_row, item_rows) -> EmployeeOrder:
    order = dict(order_row)
    items = [_order_item_to_schema(row) for row in item_rows]
    order["items"] = items
    return EmployeeOrder(**order)


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
        meal_date: date | None = None,
    ) -> MealSelection:
        order = self.create_order(
            employee_id=employee_id,
            vendor_id=vendor_id,
            meal_date=meal_date,
            items=[
                OrderItemSnapshot(
                    item_id=item_id,
                    item_name=item_name,
                    quantity=quantity,
                    unit_price_cents=unit_price_cents,
                )
            ],
        )
        item = order.items[0]
        return MealSelection(
            id=item.id,
            order_id=order.id,
            employee_id=order.employee_id,
            vendor_id=order.vendor_id,
            meal_date=order.meal_date,
            item_id=item.item_id,
            item_name=item.item_name,
            quantity=item.quantity,
            unit_price_cents=item.unit_price_cents,
            total_price_cents=item.total_price_cents,
            created_at=order.created_at,
        )

    def create_order(
        self,
        *,
        employee_id: int,
        vendor_id: int,
        items: list[OrderItemSnapshot],
        meal_date: date | None = None,
    ) -> EmployeeOrder:
        total_price_cents = sum(item.quantity * item.unit_price_cents for item in items)
        with get_connection() as conn:
            order_row = conn.execute(
                """
                INSERT INTO orders (employee_id, vendor_id, meal_date, total_price_cents)
                VALUES (%s, %s, %s, %s)
                RETURNING id, employee_id, vendor_id, meal_date, status,
                          total_price_cents, created_at, updated_at, cancelled_at
                """,
                (employee_id, vendor_id, meal_date, total_price_cents),
            ).fetchone()
            order_id = order_row["id"]
            item_rows = []
            for item in items:
                item_rows.append(
                    conn.execute(
                        """
                        INSERT INTO order_items (
                            order_id, item_id, item_name, quantity,
                            unit_price_cents, total_price_cents
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, order_id, item_id, item_name, quantity,
                                  unit_price_cents, total_price_cents
                        """,
                        (
                            order_id,
                            item.item_id,
                            item.item_name,
                            item.quantity,
                            item.unit_price_cents,
                            item.quantity * item.unit_price_cents,
                        ),
                    ).fetchone()
                )
        return _order_to_schema(order_row, item_rows)

    def list(self, *, employee_id: int) -> list[MealSelection]:
        selections: list[MealSelection] = []
        for order in self.list_orders(employee_id=employee_id):
            for item in order.items:
                selections.append(
                    MealSelection(
                        id=item.id,
                        order_id=order.id,
                        employee_id=order.employee_id,
                        vendor_id=order.vendor_id,
                        meal_date=order.meal_date,
                        item_id=item.item_id,
                        item_name=item.item_name,
                        quantity=item.quantity,
                        unit_price_cents=item.unit_price_cents,
                        total_price_cents=item.total_price_cents,
                        created_at=order.created_at,
                    )
                )
        return selections

    def list_by_vendor(self, *, vendor_id: int) -> list[MealSelection]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT oi.id, o.id AS order_id, o.employee_id, o.vendor_id,
                       o.meal_date, oi.item_id, oi.item_name, oi.quantity,
                       oi.unit_price_cents, o.created_at
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.vendor_id = %s
                ORDER BY oi.id
                """,
                (vendor_id,),
            ).fetchall()
        return [_selection_to_schema(r) for r in rows]

    def list_orders(self, *, employee_id: int) -> list[EmployeeOrder]:
        with get_connection() as conn:
            order_rows = conn.execute(
                """
                SELECT id, employee_id, vendor_id, meal_date, status,
                       total_price_cents, created_at, updated_at, cancelled_at
                FROM orders
                WHERE employee_id = %s
                ORDER BY id
                """,
                (employee_id,),
            ).fetchall()
            return [self._hydrate_order(conn, row) for row in order_rows]

    def get_order(self, *, employee_id: int, order_id: int) -> EmployeeOrder | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, employee_id, vendor_id, meal_date, status,
                       total_price_cents, created_at, updated_at, cancelled_at
                FROM orders
                WHERE employee_id = %s AND id = %s
                """,
                (employee_id, order_id),
            ).fetchone()
            if row is None:
                return None
            return self._hydrate_order(conn, row)

    def cancel_order(self, *, employee_id: int, order_id: int) -> EmployeeOrder | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                UPDATE orders
                SET status = 'cancelled', updated_at = NOW(), cancelled_at = NOW()
                WHERE employee_id = %s AND id = %s AND status = 'pending'
                RETURNING id, employee_id, vendor_id, meal_date, status,
                          total_price_cents, created_at, updated_at, cancelled_at
                """,
                (employee_id, order_id),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    """
                    SELECT id, employee_id, vendor_id, meal_date, status,
                           total_price_cents, created_at, updated_at, cancelled_at
                    FROM orders
                    WHERE employee_id = %s AND id = %s
                    """,
                    (employee_id, order_id),
                ).fetchone()
                if row is None:
                    return None
            return self._hydrate_order(conn, row)

    def item_quantities_for_date(
        self, *, meal_date: date, vendor_ids: list[int] | None = None
    ) -> dict[int, int]:
        where = ["o.meal_date = %s", "o.status <> 'cancelled'"]
        values: list[object] = [meal_date]
        if vendor_ids is not None:
            where.append("o.vendor_id = ANY(%s)")
            values.append(vendor_ids)

        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT oi.item_id, COALESCE(SUM(oi.quantity), 0) AS quantity
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE {" AND ".join(where)}
                GROUP BY oi.item_id
                """,
                values,
            ).fetchall()
        return {int(row["item_id"]): int(row["quantity"]) for row in rows}

    def _hydrate_order(self, conn, order_row) -> EmployeeOrder:
        item_rows = conn.execute(
            """
            SELECT id, order_id, item_id, item_name, quantity,
                   unit_price_cents, total_price_cents
            FROM order_items
            WHERE order_id = %s
            ORDER BY id
            """,
            (order_row["id"],),
        ).fetchall()
        return _order_to_schema(order_row, item_rows)
