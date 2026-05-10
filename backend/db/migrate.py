from __future__ import annotations

import logging
from pathlib import Path

from backend.core.config import settings
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def run_migrations() -> None:
    """Apply SQL migrations that have not been recorded yet."""
    if not settings.database_url:
        logger.info("DATABASE_URL is empty; skipping database migrations")
        return

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("SELECT filename FROM schema_migrations")
            applied = {row["filename"] for row in cur.fetchall()}

            for path in migration_files:
                if path.name in applied:
                    continue

                logger.info("Applying database migration %s", path.name)
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (path.name,),
                )

        conn.commit()
