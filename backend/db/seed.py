from __future__ import annotations

import logging
from pathlib import Path

from backend.core.config import settings
from backend.db.connection import get_connection

logger = logging.getLogger(__name__)

_SEED_FILE = Path(__file__).parent / "seeds" / "demo_seed.sql"


def run_demo_seed() -> None:
    """Apply the comprehensive demo dataset when SEED_DEMO_DATA is enabled.

    Gated + idempotent: safe to run on every startup. Only staging/preview set
    SEED_DEMO_DATA=true; prod leaves it false so it keeps the minimal baseline.
    """
    if not settings.seed_demo_data:
        return
    if not settings.database_url:
        logger.info("SEED_DEMO_DATA set but DATABASE_URL empty; skipping demo seed")
        return
    sql = _SEED_FILE.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    logger.info("Demo seed applied")
