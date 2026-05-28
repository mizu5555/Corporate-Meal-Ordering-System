from backend.core.errors import CodedHTTPException
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.committee_review_repository import CommitteeReviewRecord, CommitteeReviewRepository
from backend.schemas.committee import CommitteeReviewItem, CommitteeReviewRequest, CommitteeReviewResponse


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

    def list_pending_reviews(self) -> list[CommitteeReviewItem]:
        return [
            self._to_item(record)
            for record in self.committee_review_repository.list_pending()
        ]

    def record_decision(
        self,
        review_id: int,
        payload: CommitteeReviewRequest,
        *,
        actor_user_id: int | None = None,
        actor_role: str | None = None,
    ) -> CommitteeReviewResponse:
        review = self.committee_review_repository.get(review_id)
        if review is None:
            raise CodedHTTPException(
                status_code=404,
                code="not_found",
                detail="committee review not found",
            )
        if review.status != "pending":
            raise CodedHTTPException(
                status_code=409,
                code="review_already_decided",
                detail="committee review has already been decided",
            )

        updated = self.committee_review_repository.mark_review_decided(
            review_id,
            payload.decision,
            payload.reason,
        )
        self.audit_log_repository.record(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action="committee.review",
            target_type="committee_review",
            target_id=review_id,
            metadata={"decision": payload.decision, "reason": payload.reason},
        )

        return CommitteeReviewResponse(
            review_id=review_id,
            decision=payload.decision,
            status=updated.status if updated else payload.decision,
            reason=payload.reason,
        )

    @staticmethod
    def _to_item(record: CommitteeReviewRecord) -> CommitteeReviewItem:
        return CommitteeReviewItem(
            id=record.id,
            target_type=record.target_type,
            target_id=record.target_id,
            title=record.title,
            status=record.status,
            submitted_by_user_id=record.submitted_by_user_id,
            created_at=record.created_at,
        )
