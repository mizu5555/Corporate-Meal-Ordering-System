from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class VendorTodayItemStat(BaseModel):
    item_id: int
    item_name: str
    daily_quota: int | None = None
    sold_quantity: int
    remaining_quantity: int | None = None
    revenue_cents: int
    available: bool


class VendorItemSales(BaseModel):
    item_id: int
    item_name: str
    quantity_sold: int
    revenue_cents: int
    order_count: int


class VendorRevenueSummary(BaseModel):
    order_count: int
    quantity_sold: int
    revenue_cents: int


class VendorRevenueDashboard(BaseModel):
    today: date
    start: date
    end: date
    summary: VendorRevenueSummary
    today_items: list[VendorTodayItemStat]
    period_items: list[VendorItemSales]
