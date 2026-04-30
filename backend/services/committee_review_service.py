from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.committee_review_repository import CommitteeReviewRepository
from backend.schemas.committee import CommitteeReviewRequest, CommitteeReviewResponse


class CommitteeReviewService:
    def __init__(
        self,
        committee_review_repository: CommitteeReviewRepository | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self.committee_review_repository = (
            committee_review_repository or CommitteeReviewRepository()
        )
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    def record_decision(
        self,
        review_id: int,
        payload: CommitteeReviewRequest,
    ) -> CommitteeReviewResponse:
        self.committee_review_repository.mark_review_decided(
            review_id,
            payload.decision,
        )
        self.audit_log_repository.record_committee_review(review_id, payload.decision)

        return CommitteeReviewResponse(
            review_id=review_id,
            decision=payload.decision,
            status="review_recorded",
        )
