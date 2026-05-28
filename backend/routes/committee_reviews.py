from typing import Annotated

from fastapi import APIRouter, Depends, status

from backend.core.audit import get_audit_log_repository
from backend.core.rbac import get_current_user_id, require_roles
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.committee_review_repository import CommitteeReviewRepository
from backend.schemas.committee import CommitteeReviewItem, CommitteeReviewRequest, CommitteeReviewResponse
from backend.services.committee_review_service import CommitteeReviewService

router = APIRouter(prefix="/committee/reviews", tags=["committee-reviews"])

_committee_review_repo = CommitteeReviewRepository()


def get_committee_review_repository() -> CommitteeReviewRepository:
    return _committee_review_repo


def get_committee_review_service(
    repository: Annotated[
        CommitteeReviewRepository,
        Depends(get_committee_review_repository),
    ],
    audit_repository: Annotated[
        AuditLogRepository,
        Depends(get_audit_log_repository),
    ],
) -> CommitteeReviewService:
    return CommitteeReviewService(
        committee_review_repository=repository,
        audit_log_repository=audit_repository,
    )


@router.get("/pending", response_model=list[CommitteeReviewItem])
def list_pending_committee_reviews(
    _role: Annotated[str, Depends(require_roles("committee_reviewer"))],
    service: Annotated[CommitteeReviewService, Depends(get_committee_review_service)],
) -> list[CommitteeReviewItem]:
    return service.list_pending_reviews()


@router.post(
    "/{review_id}/decision",
    response_model=CommitteeReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def decide_committee_review(
    review_id: int,
    payload: CommitteeReviewRequest,
    _role: Annotated[str, Depends(require_roles("committee_reviewer"))],
    actor_id: Annotated[int | None, Depends(get_current_user_id)],
    service: Annotated[CommitteeReviewService, Depends(get_committee_review_service)],
) -> CommitteeReviewResponse:
    return service.record_decision(
        review_id,
        payload,
        actor_user_id=actor_id,
        actor_role="committee_reviewer",
    )
