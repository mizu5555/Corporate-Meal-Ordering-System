from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas.vendor_self import Facility


class VendorReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str | None = None


class VendorReviewResponse(BaseModel):
    application_id: int
    decision: str
    status: str


class VendorApplicationCreate(BaseModel):
    vendor_name: str = ""
    address: str | None = None
    business_hours: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    facility_ids: list[int] = Field(default_factory=list)


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
    served_facilities: list[Facility] = Field(default_factory=list)
    review_reason: str | None = None
    reviewed_at: datetime | None = None


class VendorDailyRecommendationLimitUpdate(BaseModel):
    daily_recommendation_limit: int = Field(ge=1, le=3)


class VendorDailyRecommendationLimit(BaseModel):
    vendor_id: int
    daily_recommendation_limit: int = Field(ge=1, le=3)
