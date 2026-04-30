from pydantic import BaseModel, Field


class CommitteeReviewRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|needs_changes)$")
    reason: str | None = None


class CommitteeReviewResponse(BaseModel):
    review_id: int
    decision: str
    status: str
