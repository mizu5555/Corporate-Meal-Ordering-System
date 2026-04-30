from dataclasses import dataclass


@dataclass(frozen=True)
class CommitteeReview:
    id: int
    target_type: str
    target_id: int
    status: str
