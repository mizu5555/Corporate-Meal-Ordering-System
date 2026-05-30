from __future__ import annotations

from backend.db.connection import get_connection
from backend.repositories.reporting_repository import default_badge_code, month_bounds
from backend.schemas.billing import EmployeeTotal, VendorReceivable


class PostgresReportingRepository:
    def vendor_monthly_receivables(self, year: int, month: int) -> list[VendorReceivable]:
        start, end = month_bounds(year, month)
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    v.id AS vendor_id,
                    v.name AS vendor_name,
                    COALESCE(SUM(o.total_price_cents), 0)::int AS amount_cents,
                    COUNT(o.id)::int AS order_count
                FROM orders o
                JOIN vendors v ON v.id = o.vendor_id
                WHERE o.status = 'delivered'
                  AND o.meal_date >= %s
                  AND o.meal_date < %s
                GROUP BY v.id, v.name
                ORDER BY v.id
                """,
                (start, end),
            ).fetchall()

        return [VendorReceivable(**dict(row)) for row in rows]

    def employee_monthly_totals(self, year: int, month: int) -> list[EmployeeTotal]:
        start, end = month_bounds(year, month)
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    u.id AS employee_id,
                    u.display_name AS employee_name,
                    COALESCE(u.badge_code, 'EMP-' || LPAD(u.id::text, 4, '0')) AS badge_code,
                    COALESCE(SUM(o.total_price_cents), 0)::int AS amount_cents,
                    COUNT(o.id)::int AS order_count
                FROM orders o
                JOIN users u ON u.id = o.employee_id
                WHERE o.status = 'delivered'
                  AND o.meal_date >= %s
                  AND o.meal_date < %s
                GROUP BY u.id, u.display_name, u.badge_code
                ORDER BY u.id
                """,
                (start, end),
            ).fetchall()

        data = [dict(row) for row in rows]
        for row in data:
            if not row.get("badge_code"):
                row["badge_code"] = default_badge_code(int(row["employee_id"]))
        return [EmployeeTotal(**row) for row in data]
