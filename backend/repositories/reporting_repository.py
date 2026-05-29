"""In-memory reporting/aggregation repository.

Process-local skeleton + substitutable fake for tests. The Postgres-backed
implementation (PostgresReportingRepository) mirrors these method contracts.
Aggregations exclude cancelled orders and filter on created_at date (inclusive).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from backend.schemas.admin_stats import DayPoint, FacilityStat, OrderSummary, VendorStat
from backend.schemas.billing import EmployeeTotal, VendorReceivable


@dataclass
class _OrderRow:
    order_id: int
    vendor_id: int
    vendor_name: str
    facility_id: int | None
    facility_name: str | None
    status: str
    created_at: datetime
    # items: list of (item_id, quantity, unit_price_cents)
    items: list[tuple[int, int, int]] = field(default_factory=list)
    employee_id: int | None = None
    employee_name: str | None = None
    meal_date: date | None = None
    owner_user_id: int | None = None


class ReportingRepository:
    def __init__(self) -> None:
        self._orders: list[_OrderRow] = []

    def seed_order(
        self,
        *,
        order_id: int,
        vendor_id: int,
        vendor_name: str,
        facility_id: int | None,
        facility_name: str | None,
        status: str,
        created_at: datetime,
        items: list[tuple[int, int, int]],
        employee_id: int | None = None,
        employee_name: str | None = None,
        meal_date: date | None = None,
        owner_user_id: int | None = None,
    ) -> None:
        self._orders.append(
            _OrderRow(
                order_id=order_id,
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                facility_id=facility_id,
                facility_name=facility_name,
                status=status,
                created_at=created_at,
                items=items,
                employee_id=employee_id,
                employee_name=employee_name,
                meal_date=meal_date,
                owner_user_id=owner_user_id,
            )
        )

    def _in_window(self, row: _OrderRow, start: date, end: date) -> bool:
        return row.status != "cancelled" and start <= row.created_at.date() <= end

    def _qualifying(self, start: date, end: date) -> list[_OrderRow]:
        return [r for r in self._orders if self._in_window(r, start, end)]

    @staticmethod
    def _row_quantity(row: _OrderRow) -> int:
        return sum(qty for _item_id, qty, _total in row.items)

    @staticmethod
    def _row_revenue(row: _OrderRow) -> int:
        return sum(qty * unit_price for _item_id, qty, unit_price in row.items)

    def order_summary(self, start: date, end: date) -> OrderSummary:
        rows = self._qualifying(start, end)
        return OrderSummary(
            order_count=len(rows),
            total_revenue_cents=sum(self._row_revenue(r) for r in rows),
            total_quantity=sum(self._row_quantity(r) for r in rows),
            active_vendor_count=len({r.vendor_id for r in rows}),
        )

    def vendor_ranking(self, start: date, end: date, limit: int) -> list[VendorStat]:
        acc: dict[int, dict] = {}
        for r in self._qualifying(start, end):
            a = acc.setdefault(
                r.vendor_id,
                {"vendor_name": r.vendor_name, "order_count": 0, "quantity": 0, "revenue_cents": 0},
            )
            a["order_count"] += 1
            a["quantity"] += self._row_quantity(r)
            a["revenue_cents"] += self._row_revenue(r)
        stats = [
            VendorStat(vendor_id=vid, vendor_name=a["vendor_name"], order_count=a["order_count"],
                       quantity=a["quantity"], revenue_cents=a["revenue_cents"])
            for vid, a in acc.items()
        ]
        stats.sort(key=lambda s: s.revenue_cents, reverse=True)
        return stats[:limit]

    def facility_distribution(self, start: date, end: date) -> list[FacilityStat]:
        acc: dict[int | None, dict] = {}
        for r in self._qualifying(start, end):
            a = acc.setdefault(
                r.facility_id,
                {"facility_name": r.facility_name, "order_count": 0, "quantity": 0},
            )
            a["order_count"] += 1
            a["quantity"] += self._row_quantity(r)
        stats = [
            FacilityStat(facility_id=fid, facility_name=a["facility_name"],
                         order_count=a["order_count"], quantity=a["quantity"])
            for fid, a in acc.items()
        ]
        stats.sort(key=lambda s: s.quantity, reverse=True)
        return stats

    def daily_trend(self, start: date, end: date) -> list[DayPoint]:
        acc: dict[date, dict] = {}
        for r in self._qualifying(start, end):
            day = r.created_at.date()
            a = acc.setdefault(day, {"order_count": 0, "revenue_cents": 0})
            a["order_count"] += 1
            a["revenue_cents"] += self._row_revenue(r)
        return [
            DayPoint(day=day, order_count=a["order_count"], revenue_cents=a["revenue_cents"])
            for day, a in sorted(acc.items())
        ]

    def _delivered_in_month(self, year: int, month: int) -> list[_OrderRow]:
        return [
            r
            for r in self._orders
            if r.status == "delivered"
            and r.meal_date is not None
            and r.meal_date.year == year
            and r.meal_date.month == month
        ]

    def vendor_monthly_receivables(self, year: int, month: int) -> list[VendorReceivable]:
        acc: dict[int, dict] = {}
        for r in self._delivered_in_month(year, month):
            a = acc.setdefault(
                r.vendor_id,
                {
                    "vendor_name": r.vendor_name,
                    "owner_user_id": r.owner_user_id,
                    "order_count": 0,
                    "quantity": 0,
                    "amount_cents": 0,
                },
            )
            a["order_count"] += 1
            a["quantity"] += self._row_quantity(r)
            a["amount_cents"] += self._row_revenue(r)
        rows = [
            VendorReceivable(
                vendor_id=vid, vendor_name=a["vendor_name"], owner_user_id=a["owner_user_id"],
                order_count=a["order_count"], quantity=a["quantity"], amount_cents=a["amount_cents"],
            )
            for vid, a in acc.items()
        ]
        rows.sort(key=lambda r: r.amount_cents, reverse=True)
        return rows

    def employee_monthly_totals(self, year: int, month: int) -> list[EmployeeTotal]:
        acc: dict[int, dict] = {}
        for r in self._delivered_in_month(year, month):
            if r.employee_id is None:
                continue
            a = acc.setdefault(
                r.employee_id, {"employee_name": r.employee_name, "amount_cents": 0}
            )
            a["amount_cents"] += self._row_revenue(r)
        rows = [
            EmployeeTotal(employee_id=eid, employee_name=a["employee_name"], amount_cents=a["amount_cents"])
            for eid, a in acc.items()
        ]
        rows.sort(key=lambda r: r.amount_cents, reverse=True)
        return rows
