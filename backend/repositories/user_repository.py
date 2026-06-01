"""In-memory user directory for badge lookups (tests / no-DB dev).

Mirrors the slice of the users table that badge features need. The Postgres
variant reads the real table; this one is seeded explicitly in tests.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass


@dataclass
class UserRecord:
    id: int
    display_name: str
    role: str
    badge_code: str | None = None
    is_active: bool = True


class UserRepository:
    def __init__(self) -> None:
        self._by_id: dict[int, UserRecord] = {}
        self._badge_seq = itertools.count(1)

    def add(
        self, *, id: int, display_name: str, role: str, badge_code: str | None = None, is_active: bool = True
    ) -> UserRecord:
        record = UserRecord(
            id=id,
            display_name=display_name,
            role=role,
            badge_code=badge_code,
            is_active=is_active,
        )
        self._by_id[id] = record
        return record

    def get_by_id(self, user_id: int) -> UserRecord | None:
        return self._by_id.get(user_id)

    def get_by_badge_code(self, badge_code: str) -> UserRecord | None:
        for record in self._by_id.values():
            if record.badge_code == badge_code:
                return record
        return None

    def next_badge_code(self) -> str:
        return f"EMP-{next(self._badge_seq):04d}"
