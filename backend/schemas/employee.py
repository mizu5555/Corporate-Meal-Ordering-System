"""Employee-facing vendor, menu, order, and meal selection schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.schemas.vendor_self import DietaryTag, Facility, normalize_dietary_tags


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
    remaining_quantity: int | None = None
    is_recommended: bool = False
    photo_path: str | None
    dietary_tags: list[DietaryTag] = Field(default_factory=list)

    @field_validator("dietary_tags", mode="before")
    @classmethod
    def _normalize_dietary_tags(cls, value: object) -> list[DietaryTag]:
        return normalize_dietary_tags(value)


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
    employee_id: int | None = None
    employee_badge_code: str | None = None
    masked_name: str | None = None
    vendor_id: int
    facility_id: int | None = None
    meal_date: date | None = None
    status: OrderStatus
    items: list[EmployeeOrderItem]
    total_price_cents: int
    pickup_code: str | None = None
    pickup_confirmed_at: datetime | None = None
    pickup_confirmed_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None = None


class BatchOrderStatusUpdate(BaseModel):
    order_ids: list[int] = Field(min_length=1)
    status: OrderStatus


class BatchOrderResult(BaseModel):
    order_id: int
    success: bool
    order: EmployeeOrder | None = None
    error: str | None = None
    code: str | None = None


class BatchOrderStatusResponse(BaseModel):
    results: list[BatchOrderResult]
    succeeded: int
    failed: int


class PickupLabelItem(BaseModel):
    item_name: str
    quantity: int


class PickupLabel(BaseModel):
    order_id: int
    pickup_code: str | None = None
    employee_badge_code: str | None = None
    masked_name: str | None = None
    # internal only: repos set this; the service clears it. Never serialized.
    source_employee_id: int | None = Field(default=None, exclude=True)
    vendor_id: int
    vendor_name: str
    meal_date: date | None = None
    status: OrderStatus
    facility_names: list[str] = Field(default_factory=list)
    items: list[PickupLabelItem]
    total_quantity: int
    total_price_cents: int
    pickup_confirmed_at: datetime | None = None
    pickup_confirmed_by_user_id: int | None = None


class RandomMealDrawRequest(BaseModel):
    meal_date: date
    vendor_ids: list[int] | None = None
    facility_id: int | None = None
    include_tags: list[DietaryTag] = Field(default_factory=list)
    exclude_tags: list[DietaryTag] = Field(default_factory=list)

    @field_validator("include_tags", "exclude_tags", mode="before")
    @classmethod
    def _normalize_dietary_tags(cls, value: object) -> list[DietaryTag]:
        return normalize_dietary_tags(value)


class RandomMealDraw(BaseModel):
    meal_date: date
    vendor: EmployeeVendor
    item: EmployeeMenuItem
    remaining_quantity: int | None = None


class RecommendedItem(BaseModel):
    vendor: EmployeeVendor
    item: EmployeeMenuItem
    quantity_sold: int
    remaining_quantity: int | None = None
    from_sales: bool = True
