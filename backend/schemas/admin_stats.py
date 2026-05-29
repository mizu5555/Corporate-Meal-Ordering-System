from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class OrderSummary(BaseModel):
    order_count: int
    total_revenue_cents: int
    total_quantity: int
    active_vendor_count: int


class VendorStat(BaseModel):
    vendor_id: int
    vendor_name: str
    order_count: int
    quantity: int
    revenue_cents: int


class FacilityStat(BaseModel):
    facility_id: int | None = None
    facility_name: str | None = None
    order_count: int
    quantity: int


class DayPoint(BaseModel):
    day: date
    order_count: int
    revenue_cents: int


class ItemSales(BaseModel):
    item_id: int
    vendor_id: int
    quantity_sold: int


class DashboardStats(BaseModel):
    start: date
    end: date
    summary: OrderSummary
    vendor_ranking: list[VendorStat]
    facility_distribution: list[FacilityStat]
    daily_trend: list[DayPoint]
