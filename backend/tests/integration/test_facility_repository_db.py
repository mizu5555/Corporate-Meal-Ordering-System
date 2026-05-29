"""Integration test for PostgresFacilityRepository — requires a live DATABASE_URL."""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires DATABASE_URL")

DATABASE_URL = os.getenv("DATABASE_URL", "")


@pytest.fixture(scope="module")
def migrated_db():
    from backend.db.migrate import run_migrations

    run_migrations()


@pytest.fixture()
def pg_conn():
    """Raw psycopg connection for setup/teardown that bypasses the app's get_connection()."""
    from psycopg import connect
    from psycopg.rows import dict_row

    conn = connect(DATABASE_URL, row_factory=dict_row, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture()
def vendor_id(migrated_db, pg_conn):
    """Insert a temporary vendor and return its id; clean up afterwards."""
    cur = pg_conn.cursor()
    cur.execute(
        "INSERT INTO vendors (name, status, contact_email) "
        "VALUES ('Facility Test', 'approved', 'ft@example.com') RETURNING id"
    )
    vid = cur.fetchone()["id"]
    yield vid
    cur.execute("DELETE FROM vendor_facilities WHERE vendor_id = %s", (vid,))
    cur.execute("DELETE FROM vendors WHERE id = %s", (vid,))


def test_create_and_list(migrated_db, pg_conn, vendor_id):
    from backend.repositories.postgres_facility_repository import PostgresFacilityRepository

    repo = PostgresFacilityRepository()

    fa = repo.create_facility("FTEST_A", "Integration Fab A")
    fb = repo.create_facility("FTEST_B", "Integration Fab B")

    try:
        all_codes = [f.code for f in repo.list_facilities()]
        assert "FTEST_A" in all_codes
        assert "FTEST_B" in all_codes

        # idempotency: second call with different name must return same row
        fa_dup = repo.create_facility("FTEST_A", "Should Not Override")
        assert fa_dup.id == fa.id
        assert fa_dup.name == "Integration Fab A"
    finally:
        cur = pg_conn.cursor()
        cur.execute("DELETE FROM facilities WHERE code IN ('FTEST_A', 'FTEST_B')")


def test_set_and_get_vendor_facilities(migrated_db, pg_conn, vendor_id):
    from backend.repositories.postgres_facility_repository import PostgresFacilityRepository

    repo = PostgresFacilityRepository()

    fa = repo.create_facility("FTEST_C", "Integration Fab C")
    fb = repo.create_facility("FTEST_D", "Integration Fab D")

    try:
        repo.set_vendor_facilities(vendor_id, [fa.id, fb.id])
        ids = repo.get_vendor_facility_ids(vendor_id)
        assert sorted(ids) == sorted([fa.id, fb.id])

        # Replace with only one facility
        repo.set_vendor_facilities(vendor_id, [fa.id])
        ids = repo.get_vendor_facility_ids(vendor_id)
        assert ids == [fa.id]
    finally:
        cur = pg_conn.cursor()
        cur.execute("DELETE FROM vendor_facilities WHERE vendor_id = %s", (vendor_id,))
        cur.execute("DELETE FROM facilities WHERE code IN ('FTEST_C', 'FTEST_D')")


def test_facility_exists(migrated_db, pg_conn):
    from backend.repositories.postgres_facility_repository import PostgresFacilityRepository

    repo = PostgresFacilityRepository()

    f = repo.create_facility("FTEST_E", "Integration Fab E")
    try:
        assert repo.facility_exists(f.id)
        assert not repo.facility_exists(99999)
    finally:
        cur = pg_conn.cursor()
        cur.execute("DELETE FROM facilities WHERE code = 'FTEST_E'")
