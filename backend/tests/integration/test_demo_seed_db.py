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
    apps_1 = _count(cur, "SELECT COUNT(*) AS count FROM vendor_applications")

    seed.run_demo_seed()  # second apply — must NOT duplicate
    assert _count(cur, "SELECT COUNT(*) AS count FROM orders") == orders_1, "not idempotent"
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendor_applications") == apps_1, "vendor_applications not idempotent"

    # ── Review-state coverage (issue #168) ──────────────────────────────────
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendor_applications WHERE status='approved'") >= 3
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendor_applications WHERE status='pending'") >= 1
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendor_applications WHERE status='rejected'") >= 1
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendors WHERE status='pending'") >= 1
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendors WHERE status='rejected'") >= 1
    assert _count(cur, "SELECT COUNT(*) AS count FROM vendor_applications WHERE status='rejected' AND review_reason IS NOT NULL") >= 1
    assert _count(cur, "SELECT COUNT(*) AS count FROM audit_logs WHERE action='vendor.review'") >= 4
    inactive_emps = _count(cur, """
        SELECT COUNT(*) AS count FROM users u
        JOIN roles r ON r.id = u.role_id
        WHERE r.name = 'employee' AND u.is_active = FALSE
    """)
    assert inactive_emps >= 2, f"expected >=2 pending employees, got {inactive_emps}"

    # ── Menu enrichment (issue #168): dietary tags + a sold-out example ───────
    assert _count(cur, "SELECT COUNT(*) AS count FROM menu_items WHERE array_length(dietary_tags, 1) > 0") >= 6
    assert _count(cur, "SELECT COUNT(*) AS count FROM menu_items WHERE daily_quota = 0") >= 1

    # ── Facility-consistency assertions ──────────────────────────────────────
    # Every order's facility_id must be in the employee's assigned facilities.
    # Scoped to demo vendors to avoid interference from other tests' orders.
    employee_facility_violations = _count(cur, """
        SELECT COUNT(*) AS count
        FROM orders o
        JOIN vendors v ON v.id = o.vendor_id
        WHERE v.name IN ('Sunny Kitchen', 'Demo Noodle House', 'Demo Green Bowl')
          AND o.facility_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM employee_facilities ef
            WHERE ef.employee_id = o.employee_id
              AND ef.facility_id = o.facility_id
          )
    """)
    assert employee_facility_violations == 0, (
        f"{employee_facility_violations} demo order(s) have a facility_id not in the employee's facilities"
    )

    # Every order's facility_id must also be in the vendor's served facilities.
    vendor_facility_violations = _count(cur, """
        SELECT COUNT(*) AS count
        FROM orders o
        JOIN vendors v ON v.id = o.vendor_id
        WHERE v.name IN ('Sunny Kitchen', 'Demo Noodle House', 'Demo Green Bowl')
          AND o.facility_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM vendor_facilities vf
            WHERE vf.vendor_id = o.vendor_id
              AND vf.facility_id = o.facility_id
          )
    """)
    assert vendor_facility_violations == 0, (
        f"{vendor_facility_violations} demo order(s) have a facility_id not served by the vendor"
    )

    conn.close()
