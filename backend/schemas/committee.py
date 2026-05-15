from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CommitteeReviewRequest(BaseModel):
    decision: Literal["approved", "rejected", "needs_changes"]
    reason: str | None = None


class CommitteeReviewItem(BaseModel):
    id: int
    target_type: str
    target_id: int
    title: str
    status: str
    submitted_by_user_id: int | None = None
    created_at: datetime


class CommitteeReviewResponse(BaseModel):
    review_id: int
    decision: Literal["approved", "rejected", "needs_changes"]
    status: str
    reason: str | None = None
