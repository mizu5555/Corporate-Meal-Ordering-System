from __future__ import annotations

from datetime import date

from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.schemas.billing import EmployeeTotal, VendorReceivable


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        return start, date(year + 1, 1, 1)
    return start, date(year, month + 1, 1)


def default_badge_code(employee_id: int) -> str:
    return f"EMP-{employee_id:04d}"


class ReportingRepository:
    def __init__(
        self,
        selection_repo: EmployeeSelectionRepository,
        vendor_repo: VendorProfileRepository,
    ) -> None:
        self._selection_repo = selection_repo
        self._vendor_repo = vendor_repo

    def vendor_monthly_receivables(self, year: int, month: int) -> list[VendorReceivable]:
        start, end = month_bounds(year, month)
        totals: dict[int, dict[str, int]] = {}

        for order in self._selection_repo._orders.values():
            if order.status != "delivered" or order.meal_date is None:
                continue
            if not (start <= order.meal_date < end):
                continue
            amount = sum(
                item.quantity * item.unit_price_cents
                for item in self._selection_repo._items.values()
                if item.order_id == order.id
            )
            entry = totals.setdefault(order.vendor_id, {"amount_cents": 0, "order_count": 0})
            entry["amount_cents"] += amount
            entry["order_count"] += 1

        rows: list[VendorReceivable] = []
        for vendor_id, total in totals.items():
            vendor = self._vendor_repo.get(vendor_id)
            rows.append(
                VendorReceivable(
                    vendor_id=vendor_id,
                    vendor_name=vendor.name if vendor is not None else f"Vendor {vendor_id}",
                    amount_cents=total["amount_cents"],
                    order_count=total["order_count"],
                )
            )
        return sorted(rows, key=lambda row: row.vendor_id)

    def employee_monthly_totals(self, year: int, month: int) -> list[EmployeeTotal]:
        start, end = month_bounds(year, month)
        totals: dict[int, dict[str, int]] = {}

        for order in self._selection_repo._orders.values():
            if order.status != "delivered" or order.meal_date is None:
                continue
            if not (start <= order.meal_date < end):
                continue
            amount = sum(
                item.quantity * item.unit_price_cents
                for item in self._selection_repo._items.values()
                if item.order_id == order.id
            )
            entry = totals.setdefault(order.employee_id, {"amount_cents": 0, "order_count": 0})
            entry["amount_cents"] += amount
            entry["order_count"] += 1

        rows = [
            EmployeeTotal(
                employee_id=employee_id,
                employee_name=f"Employee {employee_id}",
                badge_code=default_badge_code(employee_id),
                amount_cents=total["amount_cents"],
                order_count=total["order_count"],
            )
            for employee_id, total in totals.items()
        ]
        return sorted(rows, key=lambda row: row.employee_id)
