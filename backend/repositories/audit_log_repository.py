class AuditLogRepository:
    def record_vendor_review(self, application_id: int, decision: str) -> None:
        # Database implementation will be added when persistence work starts.
        return None

    def record_committee_review(
        self,
        review_id: int,
        decision: str,
        reason: str | None = None,
    ) -> None:
        # Database implementation will be added when persistence work starts.
        return None
