"""In-memory committee review repository.

This is intentionally process-local for the feature skeleton. The DB-backed
implementation can replace this class without changing route/service contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone


@dataclass(frozen=True)
class CommitteeReviewRecord:
    id: int
    target_type: str
    target_id: int
    title: str
    status: str = "pending"
    submitted_by_user_id: int | None = None
    decision: str | None = None
    reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None


class CommitteeReviewRepository:
    def __init__(self) -> None:
        self._rows: dict[int, CommitteeReviewRecord] = {}

    def seed(self, record: CommitteeReviewRecord) -> None:
        self._rows[record.id] = record

    def get(self, review_id: int) -> CommitteeReviewRecord | None:
        return self._rows.get(review_id)

    def list_pending(self) -> list[CommitteeReviewRecord]:
        rows = [row for row in self._rows.values() if row.status == "pending"]
        rows.sort(key=lambda row: row.id)
        return rows

    def mark_review_decided(
        self,
        review_id: int,
        decision: str,
        reason: str | None = None,
    ) -> CommitteeReviewRecord | None:
        existing = self._rows.get(review_id)
        if existing is None:
            return None

        updated = replace(
            existing,
            status=decision,
            decision=decision,
            reason=reason,
            reviewed_at=datetime.now(timezone.utc),
        )
        self._rows[review_id] = updated
        return updated
