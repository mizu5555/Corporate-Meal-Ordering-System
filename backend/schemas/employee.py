"""Employee-facing vendor, menu, order, and meal selection schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.schemas.vendor_self import Facility


class EmployeeVendor(BaseModel):
    id: int
    name: str
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    served_facilities: list[Facility] = Field(default_factory=list)


class EmployeeMenuItem(BaseModel):
    id: int
    vendor_id: int
    category_id: int | None
    name: str
    description: str | None
    price_cents: int
    available: bool
    daily_quota: int | None
    photo_path: str | None


class MealSelectionCreate(BaseModel):
    item_id: int
    quantity: int = Field(ge=1)
    meal_date: date | None = None
    facility_id: int | None = None


class MealSelection(BaseModel):
    id: int
    order_id: int | None = None
    employee_id: int
    vendor_id: int
    facility_id: int | None = None
    meal_date: date | None = None
    item_id: int
    item_name: str
    quantity: int
    unit_price_cents: int
    total_price_cents: int
    created_at: datetime


OrderStatus = Literal["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]


class VendorOrderStatusUpdate(BaseModel):
    status: OrderStatus


class EmployeeOrderItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(ge=1)


class EmployeeOrderCreate(BaseModel):
    items: list[EmployeeOrderItemCreate] = Field(min_length=1)
    meal_date: date | None = None
    facility_id: int | None = None


class EmployeeOrderUpdate(BaseModel):
    items: list[EmployeeOrderItemCreate] = Field(min_length=1)
    meal_date: date | None = None
    facility_id: int | None = None


class EmployeeOrderItem(BaseModel):
    id: int
    order_id: int
    item_id: int
    item_name: str
    quantity: int
    unit_price_cents: int
    total_price_cents: int


class EmployeeOrder(BaseModel):
    id: int
    employee_id: int
    vendor_id: int
    facility_id: int | None = None
    meal_date: date | None = None
    status: OrderStatus
    items: list[EmployeeOrderItem]
    total_price_cents: int
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None = None


class RandomMealDrawRequest(BaseModel):
    meal_date: date
    vendor_ids: list[int] | None = None
    facility_id: int | None = None


class RandomMealDraw(BaseModel):
    meal_date: date
    vendor: EmployeeVendor
    item: EmployeeMenuItem
    remaining_quantity: int | None = None
