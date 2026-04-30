from pydantic import BaseModel, Field


class VendorReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str | None = None


class VendorReviewResponse(BaseModel):
    application_id: int
    decision: str
    status: str
