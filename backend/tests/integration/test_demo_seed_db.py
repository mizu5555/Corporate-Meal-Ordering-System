import os

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires DATABASE_URL")


def _count(cur, sql):
    cur.execute(sql)
    return cur.fetchone()["count"]


def test_demo_seed_is_comprehensive_and_idempotent(monkeypatch):
    from psycopg import connect
    from psycopg.rows import dict_row
    from backend.core.config import settings
    from backend.db.migrate import run_migrations
    from backend.db import seed

    run_migrations()
    monkeypatch.setattr(settings, "seed_demo_data", True)

    seed.run_demo_seed()
    conn = connect(os.environ["DATABASE_URL"], row_factory=dict_row, autocommit=True)
    cur = conn.cursor()
    assert _count(cur, "SELECT COUNT(*) AS count FROM facilities") >= 3
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendors WHERE status='approved'") >= 3
    assert _count(cur, "SELECT COUNT(*) AS count FROM menu_items") >= 6
    orders_1 = _count(cur, "SELECT COUNT(*) AS count FROM orders")
    assert orders_1 >= 10
    assert _count(cur, "SELECT COUNT(*) AS count FROM orders WHERE status='delivered'") >= 5

    seed.run_demo_seed()  # second apply — must NOT duplicate
    assert _count(cur, "SELECT COUNT(*) AS count FROM orders") == orders_1, "not idempotent"
    conn.close()
