"""Process-wide UserRepository provider (Postgres when DATABASE_URL, else in-memory)."""
from __future__ import annotations

from backend.core.config import settings
from backend.repositories.user_repository import UserRepository

_user_repository = None


def get_user_repository():
    """Return a shared user directory for badge lookups.

    Postgres-backed when DATABASE_URL is set, else an in-memory instance (tests
    override this dependency with a seeded repo).
    """
    global _user_repository
    if _user_repository is None:
        if settings.database_url:
            from backend.repositories.postgres_user_repository import PostgresUserRepository

            _user_repository = PostgresUserRepository()
        else:
            _user_repository = UserRepository()
    return _user_repository
