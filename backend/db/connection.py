from __future__ import annotations

from typing import Any

from backend.core.config import settings


def get_connection() -> Any:
    """Open a PostgreSQL connection using DATABASE_URL.

    The psycopg import is intentionally lazy so unit tests that keep using the
    in-memory repositories do not need an active database connection.
    """
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    from psycopg import connect
    from psycopg.rows import dict_row

    return connect(settings.database_url, row_factory=dict_row)
