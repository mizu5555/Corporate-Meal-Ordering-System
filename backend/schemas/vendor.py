from datetime import datetime

from pydantic import BaseModel, Field


class VendorReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str | None = None


class VendorReviewResponse(BaseModel):
    application_id: int
    decision: str
    status: str


class VendorApplicationCreate(BaseModel):
    vendor_name: str
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class VendorApplicationSummary(BaseModel):
    application_id: int
    vendor_id: int
    vendor_name: str
    status: str
    submitter_email: str | None = None
    submitter_name: str | None = None
    submitted_at: datetime


class VendorApplicationDetail(VendorApplicationSummary):
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    review_reason: str | None = None
    reviewed_at: datetime | None = None
