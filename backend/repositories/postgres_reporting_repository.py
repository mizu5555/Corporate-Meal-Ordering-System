from __future__ import annotations

from datetime import date

from backend.db.connection import get_connection
from backend.schemas.admin_stats import DayPoint, FacilityStat, OrderSummary, VendorStat

_WINDOW = "o.status <> 'cancelled' AND o.created_at::date BETWEEN %s AND %s"


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
