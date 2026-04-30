from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.core.rbac import require_roles
from backend.schemas.committee import CommitteeReviewRequest, CommitteeReviewResponse
from backend.services.committee_review_service import CommitteeReviewService

router = APIRouter(prefix="/committee/reviews", tags=["committee-reviews"])


@router.post(
    "/{review_id}/decision",
    response_model=CommitteeReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def decide_committee_review(
    review_id: int,
    payload: CommitteeReviewRequest,
    _role: Annotated[str, Depends(require_roles("committee_reviewer"))],
) -> CommitteeReviewResponse:
    service = CommitteeReviewService()
    return service.record_decision(review_id, payload)
