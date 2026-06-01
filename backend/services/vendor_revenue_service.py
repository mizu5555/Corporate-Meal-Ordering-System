from __future__ import annotations

from datetime import date

from backend.core.errors import CodedHTTPException
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository
from backend.schemas.vendor_revenue import (
    VendorItemSales,
    VendorRevenueDashboard,
    VendorRevenueSummary,
    VendorTodayItemStat,
)


class VendorRevenueService:
    def __init__(
        self,
        menu_item_repository: MenuItemRepository,
        reporting_repository,
        vendor_repository: VendorProfileRepository,
    ) -> None:
        self._items = menu_item_repository
        self._reporting = reporting_repository
        self._vendors = vendor_repository

    def dashboard(
        self,
        vendor_id: int,
        *,
        today: date,
        start: date,
        end: date,
        facility_id: int | None = None,
    ) -> VendorRevenueDashboard:
        if start > end:
            raise CodedHTTPException(
                status_code=400,
                code="validation_error",
                detail="start must be on or before end",
            )
        self._assert_facility_access(vendor_id, facility_id)

        menu_items = self._items.list(vendor_id=vendor_id)
        today_stats = self._reporting.vendor_today_item_stats(
            vendor_id, today, facility_id=facility_id
        )
        period_sales = self._reporting.vendor_period_item_sales(
            vendor_id, start, end, facility_id=facility_id
        )
        summary = self._reporting.vendor_period_summary(
            vendor_id, start, end, facility_id=facility_id
        )

        return VendorRevenueDashboard(
            today=today,
            start=start,
            end=end,
            summary=VendorRevenueSummary(
                order_count=summary.order_count,
                quantity_sold=summary.quantity_sold,
                revenue_cents=summary.revenue_cents,
            ),
            today_items=self._today_items(menu_items, today_stats),
            period_items=self._period_items(menu_items, period_sales),
        )

    def _assert_facility_access(self, vendor_id: int, facility_id: int | None) -> None:
        if facility_id is None:
            return
        if not any(facility.id == facility_id for facility in self._vendors.list_facilities(vendor_id)):
            raise CodedHTTPException(
                status_code=403,
                code="forbidden",
                detail="vendor does not serve the selected facility",
            )

    @staticmethod
    def _today_items(menu_items, today_stats) -> list[VendorTodayItemStat]:
        sold_by_item = {stat.item_id: stat for stat in today_stats}
        rows: list[VendorTodayItemStat] = []
        for item in menu_items:
            stat = sold_by_item.get(item.id)
            sold_quantity = stat.sold_quantity if stat else 0
            revenue_cents = stat.revenue_cents if stat else 0
            remaining = None
            if item.daily_quota is not None:
                remaining = max(item.daily_quota - sold_quantity, 0)
            rows.append(
                VendorTodayItemStat(
                    item_id=item.id,
                    item_name=item.name,
                    daily_quota=item.daily_quota,
                    sold_quantity=sold_quantity,
                    remaining_quantity=remaining,
                    revenue_cents=revenue_cents,
                    available=item.available,
                )
            )
        return rows

    @staticmethod
    def _period_items(menu_items, period_sales) -> list[VendorItemSales]:
        menu_names = {item.id: item.name for item in menu_items}
        rows = [
            VendorItemSales(
                item_id=sale.item_id,
                item_name=menu_names.get(sale.item_id, f"Item #{sale.item_id}"),
                quantity_sold=sale.quantity_sold,
                revenue_cents=sale.revenue_cents,
                order_count=sale.order_count,
            )
            for sale in period_sales
        ]
        rows.sort(key=lambda row: (-row.quantity_sold, row.item_name))
        return rows
