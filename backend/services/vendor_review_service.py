from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.vendor_repository import VendorRepository
from backend.schemas.vendor import VendorReviewRequest, VendorReviewResponse


class VendorReviewService:
    def __init__(
        self,
        vendor_repository: VendorRepository | None = None,
        audit_log_repository: AuditLogRepository | None = None,
    ) -> None:
        self.vendor_repository = vendor_repository or VendorRepository()
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    def review_application(
        self,
        application_id: int,
        payload: VendorReviewRequest,
    ) -> VendorReviewResponse:
        self.vendor_repository.mark_application_reviewed(application_id, payload.decision)
        self.audit_log_repository.record(
            actor_user_id=None,
            actor_role=None,
            action="vendor.review",
            target_type="vendor_application",
            target_id=application_id,
            metadata={"decision": payload.decision},
        )

        return VendorReviewResponse(
            application_id=application_id,
            decision=payload.decision,
            status="review_recorded",
        )
