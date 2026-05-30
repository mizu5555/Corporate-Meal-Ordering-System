from __future__ import annotations

from pydantic import BaseModel, Field


class MonthlyBillingSummary(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    amount_cents: int
    order_count: int


class VendorReceivable(BaseModel):
    vendor_id: int
    vendor_name: str
    amount_cents: int
    order_count: int


class EmployeeTotal(BaseModel):
    employee_id: int
    employee_name: str
    badge_code: str
    amount_cents: int
    order_count: int
