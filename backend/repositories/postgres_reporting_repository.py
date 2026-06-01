from __future__ import annotations

from datetime import date

from backend.db.connection import get_connection
from backend.repositories.reporting_repository import default_badge_code
from backend.schemas.admin_stats import (
    DayPoint,
    FacilityStat,
    ItemSales,
    OrderSummary,
    VendorItemPeriodAggregate,
    VendorItemTodayAggregate,
    VendorRevenueWindowSummary,
    VendorStat,
)
from backend.schemas.billing import EmployeeTotal, VendorReceivable

_WINDOW = "o.status <> 'cancelled' AND o.created_at::date BETWEEN %s AND %s"

_MONTH = (
    "o.status = 'delivered' AND o.meal_date IS NOT NULL "
    "AND EXTRACT(YEAR FROM o.meal_date) = %s AND EXTRACT(MONTH FROM o.meal_date) = %s"
)


class PostgresReportingRepository:
    def order_summary(self, start: date, end: date) -> OrderSummary:
        with get_connection() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(DISTINCT o.id) AS order_count,
                       COALESCE(SUM(oi.total_price_cents), 0) AS total_revenue_cents,
                       COALESCE(SUM(oi.quantity), 0) AS total_quantity,
                       COUNT(DISTINCT o.vendor_id) AS active_vendor_count
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE {_WINDOW}
                """,
                [start, end],
            ).fetchone()
        return OrderSummary(
            order_count=int(row["order_count"]),
            total_revenue_cents=int(row["total_revenue_cents"]),
            total_quantity=int(row["total_quantity"]),
            active_vendor_count=int(row["active_vendor_count"]),
        )

    def vendor_ranking(self, start: date, end: date, limit: int) -> list[VendorStat]:
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.vendor_id, v.name AS vendor_name,
                       COUNT(DISTINCT o.id) AS order_count,
                       COALESCE(SUM(oi.quantity), 0) AS quantity,
                       COALESCE(SUM(oi.total_price_cents), 0) AS revenue_cents
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN vendors v ON v.id = o.vendor_id
                WHERE {_WINDOW}
                GROUP BY o.vendor_id, v.name
                ORDER BY revenue_cents DESC
                LIMIT %s
                """,
                [start, end, limit],
            ).fetchall()
        return [
            VendorStat(
                vendor_id=int(r["vendor_id"]), vendor_name=r["vendor_name"],
                order_count=int(r["order_count"]), quantity=int(r["quantity"]),
                revenue_cents=int(r["revenue_cents"]),
            )
            for r in rows
        ]

    def facility_distribution(self, start: date, end: date) -> list[FacilityStat]:
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.facility_id, f.name AS facility_name,
                       COUNT(DISTINCT o.id) AS order_count,
                       COALESCE(SUM(oi.quantity), 0) AS quantity
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN facilities f ON f.id = o.facility_id
                WHERE {_WINDOW}
                GROUP BY o.facility_id, f.name
                ORDER BY quantity DESC
                """,
                [start, end],
            ).fetchall()
        return [
            FacilityStat(
                facility_id=int(r["facility_id"]) if r["facility_id"] is not None else None,
                facility_name=r["facility_name"],
                order_count=int(r["order_count"]), quantity=int(r["quantity"]),
            )
            for r in rows
        ]

    def daily_trend(self, start: date, end: date) -> list[DayPoint]:
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.created_at::date AS day,
                       COUNT(DISTINCT o.id) AS order_count,
                       COALESCE(SUM(oi.total_price_cents), 0) AS revenue_cents
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE {_WINDOW}
                GROUP BY o.created_at::date
                ORDER BY day
                """,
                [start, end],
            ).fetchall()
        return [
            DayPoint(day=r["day"], order_count=int(r["order_count"]), revenue_cents=int(r["revenue_cents"]))
            for r in rows
        ]

    def vendor_monthly_receivables(self, year: int, month: int) -> list[VendorReceivable]:
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.vendor_id, v.name AS vendor_name, v.owner_user_id,
                       COUNT(DISTINCT o.id) AS order_count,
                       COALESCE(SUM(oi.quantity), 0) AS quantity,
                       COALESCE(SUM(oi.total_price_cents), 0) AS amount_cents
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN vendors v ON v.id = o.vendor_id
                WHERE {_MONTH}
                GROUP BY o.vendor_id, v.name, v.owner_user_id
                ORDER BY amount_cents DESC
                """,
                [year, month],
            ).fetchall()
        return [
            VendorReceivable(
                vendor_id=int(r["vendor_id"]), vendor_name=r["vendor_name"],
                owner_user_id=int(r["owner_user_id"]) if r["owner_user_id"] is not None else None,
                order_count=int(r["order_count"]), quantity=int(r["quantity"]),
                amount_cents=int(r["amount_cents"]),
            )
            for r in rows
        ]

    def top_items(
        self, start: date, end: date, limit: int, vendor_ids: list[int] | None = None
    ) -> list[ItemSales]:
        where = ["o.status <> 'cancelled'", "o.created_at::date BETWEEN %s AND %s", "oi.item_id IS NOT NULL"]
        values = [start, end]
        if vendor_ids is not None:
            where.append("o.vendor_id = ANY(%s)")
            values.append(list(vendor_ids))
        values.append(limit)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT oi.item_id, MIN(o.vendor_id) AS vendor_id,
                       COALESCE(SUM(oi.quantity), 0) AS quantity_sold
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE {" AND ".join(where)}
                GROUP BY oi.item_id
                ORDER BY quantity_sold DESC
                LIMIT %s
                """,
                values,
            ).fetchall()
        return [
            ItemSales(item_id=int(r["item_id"]), vendor_id=int(r["vendor_id"]),
                      quantity_sold=int(r["quantity_sold"]))
            for r in rows
        ]

    def vendor_today_item_stats(
        self,
        vendor_id: int,
        day: date,
        *,
        facility_id: int | None = None,
    ) -> list[VendorItemTodayAggregate]:
        where = [
            "o.status <> 'cancelled'",
            "o.vendor_id = %s",
            "COALESCE(o.meal_date, o.created_at::date) = %s",
        ]
        values: list[object] = [vendor_id, day]
        if facility_id is not None:
            where.append("o.facility_id = %s")
            values.append(facility_id)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT oi.item_id,
                       COALESCE(SUM(oi.quantity), 0) AS sold_quantity,
                       COALESCE(SUM(oi.total_price_cents), 0) AS revenue_cents
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE {" AND ".join(where)}
                GROUP BY oi.item_id
                """,
                values,
            ).fetchall()
        return [
            VendorItemTodayAggregate(
                item_id=int(r["item_id"]),
                sold_quantity=int(r["sold_quantity"]),
                revenue_cents=int(r["revenue_cents"]),
            )
            for r in rows
        ]

    def vendor_period_item_sales(
        self,
        vendor_id: int,
        start: date,
        end: date,
        *,
        facility_id: int | None = None,
    ) -> list[VendorItemPeriodAggregate]:
        where = [
            "o.status <> 'cancelled'",
            "o.vendor_id = %s",
            "COALESCE(o.meal_date, o.created_at::date) BETWEEN %s AND %s",
        ]
        values: list[object] = [vendor_id, start, end]
        if facility_id is not None:
            where.append("o.facility_id = %s")
            values.append(facility_id)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT oi.item_id,
                       COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
                       COALESCE(SUM(oi.total_price_cents), 0) AS revenue_cents,
                       COUNT(DISTINCT o.id) AS order_count
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE {" AND ".join(where)}
                GROUP BY oi.item_id
                """,
                values,
            ).fetchall()
        return [
            VendorItemPeriodAggregate(
                item_id=int(r["item_id"]),
                quantity_sold=int(r["quantity_sold"]),
                revenue_cents=int(r["revenue_cents"]),
                order_count=int(r["order_count"]),
            )
            for r in rows
        ]

    def vendor_period_summary(
        self,
        vendor_id: int,
        start: date,
        end: date,
        *,
        facility_id: int | None = None,
    ) -> VendorRevenueWindowSummary:
        where = [
            "o.status <> 'cancelled'",
            "o.vendor_id = %s",
            "COALESCE(o.meal_date, o.created_at::date) BETWEEN %s AND %s",
        ]
        values: list[object] = [vendor_id, start, end]
        if facility_id is not None:
            where.append("o.facility_id = %s")
            values.append(facility_id)
        with get_connection() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(DISTINCT o.id) AS order_count,
                       COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
                       COALESCE(SUM(oi.total_price_cents), 0) AS revenue_cents
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE {" AND ".join(where)}
                """,
                values,
            ).fetchone()
        return VendorRevenueWindowSummary(
            order_count=int(row["order_count"]),
            quantity_sold=int(row["quantity_sold"]),
            revenue_cents=int(row["revenue_cents"]),
        )

    def employee_monthly_totals(self, year: int, month: int) -> list[EmployeeTotal]:
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.employee_id, u.display_name AS employee_name, u.badge_code,
                       COUNT(DISTINCT o.id) AS order_count,
                       COALESCE(SUM(oi.total_price_cents), 0) AS amount_cents
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN users u ON u.id = o.employee_id
                WHERE {_MONTH}
                GROUP BY o.employee_id, u.display_name, u.badge_code
                ORDER BY amount_cents DESC
                """,
                [year, month],
            ).fetchall()
        out: list[EmployeeTotal] = []
        for r in rows:
            employee_id = int(r["employee_id"])
            out.append(
                EmployeeTotal(
                    employee_id=employee_id,
                    employee_name=r["employee_name"],
                    badge_code=r["badge_code"] or default_badge_code(employee_id),
                    order_count=int(r["order_count"]),
                    amount_cents=int(r["amount_cents"]),
                )
            )
        return out
