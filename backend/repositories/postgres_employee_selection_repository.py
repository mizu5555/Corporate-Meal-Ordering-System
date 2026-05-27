from __future__ import annotations

from datetime import date

from backend.core.errors import CodedHTTPException
from backend.core.order_failure_codes import (
    CONCURRENT_CONFLICT,
    ITEM_UNAVAILABLE,
    QUOTA_EXHAUSTED,
)
from backend.db.connection import get_connection
from backend.repositories.employee_selection_repository import OrderItemSnapshot
from backend.schemas.employee import EmployeeOrder, EmployeeOrderItem, MealSelection

try:
    from psycopg import errors as psycopg_errors
except ImportError:  # pragma: no cover - psycopg is present in deployed Postgres environments.
    psycopg_errors = None

if psycopg_errors is None:
    _PSYCOPG_CONFLICT_ERRORS: tuple[type[BaseException], ...] = ()
else:
    _PSYCOPG_CONFLICT_ERRORS = (
        psycopg_errors.DeadlockDetected,
        psycopg_errors.LockNotAvailable,
        psycopg_errors.SerializationFailure,
    )


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
        with get_connection() as conn:
            # ── Step 1: Acquire row locks and validate quota atomically ──────
            # SELECT ... FOR UPDATE locks each menu_items row for the duration
            # of this transaction, preventing concurrent transactions from
            # passing the quota check simultaneously (eliminates TOCTOU race).
            for item_snap in items:
                try:
                    menu_row = conn.execute(
                        """
                        SELECT id, daily_quota, available
                        FROM menu_items
                        WHERE id = %s
                        FOR UPDATE
                        """,
                        (item_snap.item_id,),
                    ).fetchone()
                except _PSYCOPG_CONFLICT_ERRORS as exc:
                    raise CodedHTTPException(
                        status_code=409,
                        code=CONCURRENT_CONFLICT,
                        detail="order could not be placed due to a concurrent update; please try again",
                    ) from exc

                if menu_row is None:
                    raise CodedHTTPException(
                        status_code=404, code="not_found", detail="menu item not found"
                    )
                used = None

                if menu_row["daily_quota"] is not None:
                    # Count already-ordered quantity within the same locked
                    # transaction for a consistent, race-free read.
                    used_row = conn.execute(
                        """
                        SELECT COALESCE(SUM(oi.quantity), 0) AS used
                        FROM order_items oi
                        JOIN orders o ON o.id = oi.order_id
                        WHERE oi.item_id = %s
                          AND o.meal_date = %s
                          AND o.status <> 'cancelled'
                        """,
                        (item_snap.item_id, meal_date),
                    ).fetchone()
                    used = int(used_row["used"])

                    if not menu_row["available"]:
                        if used >= menu_row["daily_quota"]:
                            raise CodedHTTPException(
                                status_code=409,
                                code=QUOTA_EXHAUSTED,
                                detail="daily quota exhausted for this item",
                            )
                        raise CodedHTTPException(
                            status_code=409,
                            code=ITEM_UNAVAILABLE,
                            detail="menu item unavailable",
                        )

                    if used + item_snap.quantity > menu_row["daily_quota"]:
                        raise CodedHTTPException(
                            status_code=409,
                            code=QUOTA_EXHAUSTED,
                            detail="daily quota exhausted for this item",
                        )

                    # Issue #53: auto-mark sold out when this order fills the
                    # last slot — happens inside the same transaction so
                    # employees immediately stop seeing the item as available.
                    if used + item_snap.quantity >= menu_row["daily_quota"]:
                        conn.execute(
                            """
                            UPDATE menu_items
                            SET available = FALSE, updated_at = NOW()
                            WHERE id = %s
                            """,
                            (item_snap.item_id,),
                        )

                if not menu_row["available"]:
                    raise CodedHTTPException(
                        status_code=409,
                        code=ITEM_UNAVAILABLE,
                        detail="menu item unavailable",
                    )

            # ── Step 2: Insert order and line items ──────────────────────────
            total_price_cents = sum(s.quantity * s.unit_price_cents for s in items)
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
            for item_snap in items:
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
                            item_snap.item_id,
                            item_snap.item_name,
                            item_snap.quantity,
                            item_snap.unit_price_cents,
                            item_snap.quantity * item_snap.unit_price_cents,
                        ),
                    ).fetchone()
                )
        # Transaction commits here; all locks released.
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

    def list_orders_by_vendor(self, *, vendor_id: int) -> list[EmployeeOrder]:
        with get_connection() as conn:
            order_rows = conn.execute(
                """
                SELECT id, employee_id, vendor_id, meal_date, status,
                       total_price_cents, created_at, updated_at, cancelled_at
                FROM orders
                WHERE vendor_id = %s
                ORDER BY id
                """,
                (vendor_id,),
            ).fetchall()
            return [self._hydrate_order(conn, row) for row in order_rows]

    def get_order_for_vendor(self, *, vendor_id: int, order_id: int) -> EmployeeOrder | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, employee_id, vendor_id, meal_date, status,
                       total_price_cents, created_at, updated_at, cancelled_at
                FROM orders
                WHERE vendor_id = %s AND id = %s
                """,
                (vendor_id, order_id),
            ).fetchone()
            if row is None:
                return None
            return self._hydrate_order(conn, row)

    def update_order_status(self, *, vendor_id: int, order_id: int, new_status: str) -> EmployeeOrder | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                UPDATE orders
                SET status = %s,
                    updated_at = NOW(),
                    cancelled_at = CASE WHEN %s = 'cancelled' THEN NOW() ELSE cancelled_at END
                WHERE vendor_id = %s AND id = %s
                RETURNING id, employee_id, vendor_id, meal_date, status,
                          total_price_cents, created_at, updated_at, cancelled_at
                """,
                (new_status, new_status, vendor_id, order_id),
            ).fetchone()
            if row is None:
                return None
            return self._hydrate_order(conn, row)

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

    def update_order(
        self,
        *,
        employee_id: int,
        order_id: int,
        items: list[OrderItemSnapshot],
        meal_date: date | None = None,
    ) -> EmployeeOrder | None:
        with get_connection() as conn:
            order_row = conn.execute(
                """
                SELECT id, employee_id, vendor_id, meal_date, status,
                       total_price_cents, created_at, updated_at, cancelled_at
                FROM orders
                WHERE employee_id = %s AND id = %s
                FOR UPDATE
                """,
                (employee_id, order_id),
            ).fetchone()
            if order_row is None:
                return None

            for item_snap in items:
                try:
                    menu_row = conn.execute(
                        """
                        SELECT id, daily_quota, available
                        FROM menu_items
                        WHERE id = %s
                        FOR UPDATE
                        """,
                        (item_snap.item_id,),
                    ).fetchone()
                except _PSYCOPG_CONFLICT_ERRORS as exc:
                    raise CodedHTTPException(
                        status_code=409,
                        code=CONCURRENT_CONFLICT,
                        detail="order could not be updated due to a concurrent update; please try again",
                    ) from exc

                if menu_row is None:
                    raise CodedHTTPException(
                        status_code=404, code="not_found", detail="menu item not found"
                    )

                if menu_row["daily_quota"] is not None:
                    used_row = conn.execute(
                        """
                        SELECT COALESCE(SUM(oi.quantity), 0) AS used
                        FROM order_items oi
                        JOIN orders o ON o.id = oi.order_id
                        WHERE oi.item_id = %s
                          AND o.meal_date = %s
                          AND o.status <> 'cancelled'
                          AND o.id <> %s
                        """,
                        (item_snap.item_id, meal_date, order_id),
                    ).fetchone()
                    used = int(used_row["used"])

                    if not menu_row["available"] and used >= menu_row["daily_quota"]:
                        raise CodedHTTPException(
                            status_code=409,
                            code=QUOTA_EXHAUSTED,
                            detail="daily quota exhausted for this item",
                        )

                    if menu_row["available"] and used + item_snap.quantity > menu_row["daily_quota"]:
                        raise CodedHTTPException(
                            status_code=409,
                            code=QUOTA_EXHAUSTED,
                            detail="daily quota exhausted for this item",
                        )

                if not menu_row["available"]:
                    raise CodedHTTPException(
                        status_code=409,
                        code=ITEM_UNAVAILABLE,
                        detail="menu item unavailable",
                    )

            total_price_cents = sum(s.quantity * s.unit_price_cents for s in items)
            row = conn.execute(
                """
                UPDATE orders
                SET meal_date = %s,
                    total_price_cents = %s,
                    updated_at = NOW()
                WHERE employee_id = %s AND id = %s
                RETURNING id, employee_id, vendor_id, meal_date, status,
                          total_price_cents, created_at, updated_at, cancelled_at
                """,
                (meal_date, total_price_cents, employee_id, order_id),
            ).fetchone()

            conn.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
            item_rows = []
            for item_snap in items:
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
                            item_snap.item_id,
                            item_snap.item_name,
                            item_snap.quantity,
                            item_snap.unit_price_cents,
                            item_snap.quantity * item_snap.unit_price_cents,
                        ),
                    ).fetchone()
                )

        return _order_to_schema(row, item_rows)

    def item_quantities_for_date(
        self,
        *,
        meal_date: date,
        vendor_ids: list[int] | None = None,
        exclude_order_id: int | None = None,
    ) -> dict[int, int]:
        where = ["o.meal_date = %s", "o.status <> 'cancelled'"]
        values: list[object] = [meal_date]
        if vendor_ids is not None:
            where.append("o.vendor_id = ANY(%s)")
            values.append(vendor_ids)
        if exclude_order_id is not None:
            where.append("o.id <> %s")
            values.append(exclude_order_id)

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
