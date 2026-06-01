"""Integration tests for vendor menu endpoints against a real PostgreSQL database.

Covers:
  - Menu item CRUD via HTTP (POST/GET/PATCH/DELETE /vendor/me/menu)
  - Per-date schedule CRUD via HTTP (GET/PUT/DELETE /vendor/me/menu/{id}/schedule)
  - list_effective and get_effective via the employee browse / order endpoints
  - Direct repo calls for methods not exposed through HTTP routes

Run with DATABASE_URL set:
    DATABASE_URL=postgresql://... pytest backend/tests/integration/test_vendor_menu_db.py -v
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.db.connection import get_connection
from backend.main import app
from backend.repositories.postgres_menu_item_repository import PostgresMenuItemRepository

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def seeded_ids():
    """Resolve vendor/employee rows seeded by migrations."""
    with get_connection() as conn:
        vendor = conn.execute(
            "SELECT id FROM vendors WHERE name = 'Sunny Kitchen'"
        ).fetchone()
        employee = conn.execute(
            "SELECT id FROM users WHERE email = 'employee@corpmeal.local'"
        ).fetchone()
    assert vendor is not None, "Sunny Kitchen not found — did migrations run?"
    assert employee is not None, "employee@corpmeal.local not found — did migrations run?"
    return vendor["id"], employee["id"]


@pytest.fixture(autouse=True)
def clean_inttest_menu():
    """Remove IntTest-prefixed rows inserted during each test."""
    yield
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM menu_item_date_overrides "
            "WHERE item_id IN (SELECT id FROM menu_items WHERE name LIKE 'IntTest%')"
        )
        conn.execute("DELETE FROM order_items WHERE order_id IN "
                     "(SELECT id FROM orders WHERE vendor_id IN "
                     "(SELECT id FROM vendors WHERE name = 'Sunny Kitchen'))")
        conn.execute("DELETE FROM orders WHERE vendor_id IN "
                     "(SELECT id FROM vendors WHERE name = 'Sunny Kitchen')")
        conn.execute("DELETE FROM menu_items WHERE name LIKE 'IntTest%'")
        conn.commit()


def _vh(vendor_id: int) -> dict:
    return {"x-user-role": "vendor_manager", "x-vendor-id": str(vendor_id)}


def _eh(employee_id: int) -> dict:
    return {"x-user-role": "employee", "x-user-id": str(employee_id)}


def _today_plus(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Menu item CRUD (covers create / list / get / update / delete in postgres repo)
# ---------------------------------------------------------------------------


def test_create_and_list_menu_item(client, seeded_ids):
    vendor_id, _ = seeded_ids

    resp = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest Bento", "price_cents": 1000, "available": True},
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]
    assert resp.json()["name"] == "IntTest Bento"

    resp = client.get("/vendor/me/menu", headers=_vh(vendor_id))
    assert resp.status_code == 200
    assert any(i["id"] == item_id for i in resp.json())


def test_list_menu_with_available_filter(client, seeded_ids):
    vendor_id, _ = seeded_ids

    client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest FilterItem", "price_cents": 800, "available": False},
    )

    resp = client.get("/vendor/me/menu?available=true", headers=_vh(vendor_id))
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json()]
    assert "IntTest FilterItem" not in names


def test_get_single_menu_item(client, seeded_ids):
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest GetItem", "price_cents": 600},
    )
    item_id = create.json()["id"]

    resp = client.get(f"/vendor/me/menu/{item_id}", headers=_vh(vendor_id))
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id
    assert resp.json()["price_cents"] == 600


def test_update_menu_item(client, seeded_ids):
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest PatchItem", "price_cents": 500},
    )
    item_id = create.json()["id"]

    resp = client.patch(
        f"/vendor/me/menu/{item_id}",
        headers=_vh(vendor_id),
        json={"price_cents": 750, "available": False},
    )
    assert resp.status_code == 200
    assert resp.json()["price_cents"] == 750
    assert resp.json()["available"] is False


def test_delete_menu_item(client, seeded_ids):
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest DelItem", "price_cents": 400},
    )
    item_id = create.json()["id"]

    resp = client.delete(f"/vendor/me/menu/{item_id}", headers=_vh(vendor_id))
    assert resp.status_code == 204

    resp = client.get(f"/vendor/me/menu/{item_id}", headers=_vh(vendor_id))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Per-date schedule CRUD (covers override CRUD in postgres repo)
# ---------------------------------------------------------------------------


def test_list_schedule_empty(client, seeded_ids):
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest EmptySched", "price_cents": 800},
    )
    item_id = create.json()["id"]

    resp = client.get(f"/vendor/me/menu/{item_id}/schedule", headers=_vh(vendor_id))
    assert resp.status_code == 200
    assert resp.json() == []


def test_upsert_and_list_schedule(client, seeded_ids):
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest UpsertSched", "price_cents": 800},
    )
    item_id = create.json()["id"]
    target = _today_plus(1)

    # Initial upsert (INSERT path)
    resp = client.put(
        f"/vendor/me/menu/{item_id}/schedule/{target}",
        headers=_vh(vendor_id),
        json={"price_cents": 900, "daily_quota": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["price_cents"] == 900
    assert body["daily_quota"] == 5
    assert body["available"] is None

    # List should contain it
    resp = client.get(f"/vendor/me/menu/{item_id}/schedule", headers=_vh(vendor_id))
    assert resp.status_code == 200
    overrides = resp.json()
    assert len(overrides) == 1
    assert overrides[0]["meal_date"] == target


def test_upsert_schedule_update_path(client, seeded_ids):
    """Second PUT on the same date should update the existing row (ON CONFLICT)."""
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest UpdateSched", "price_cents": 800},
    )
    item_id = create.json()["id"]
    target = _today_plus(2)

    client.put(
        f"/vendor/me/menu/{item_id}/schedule/{target}",
        headers=_vh(vendor_id),
        json={"price_cents": 900},
    )
    resp = client.put(
        f"/vendor/me/menu/{item_id}/schedule/{target}",
        headers=_vh(vendor_id),
        json={"price_cents": 1100},
    )
    assert resp.status_code == 200
    assert resp.json()["price_cents"] == 1100

    # Only one override row should exist (idempotent)
    list_resp = client.get(f"/vendor/me/menu/{item_id}/schedule", headers=_vh(vendor_id))
    assert len(list_resp.json()) == 1


def test_delete_schedule_override(client, seeded_ids):
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest DelSched", "price_cents": 800},
    )
    item_id = create.json()["id"]
    target = _today_plus(1)

    client.put(
        f"/vendor/me/menu/{item_id}/schedule/{target}",
        headers=_vh(vendor_id),
        json={"daily_quota": 3},
    )

    resp = client.delete(f"/vendor/me/menu/{item_id}/schedule/{target}", headers=_vh(vendor_id))
    assert resp.status_code == 204

    list_resp = client.get(f"/vendor/me/menu/{item_id}/schedule", headers=_vh(vendor_id))
    assert list_resp.json() == []


def test_delete_schedule_nonexistent_is_idempotent(client, seeded_ids):
    vendor_id, _ = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest IdemDel", "price_cents": 800},
    )
    item_id = create.json()["id"]

    resp = client.delete(
        f"/vendor/me/menu/{item_id}/schedule/{_today_plus(1)}",
        headers=_vh(vendor_id),
    )
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# list_effective: employee browse with meal_date (covers postgres list_effective)
# ---------------------------------------------------------------------------


def test_list_effective_base_values_no_override(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest EffBase", "price_cents": 1000, "available": True},
    )
    item_id = create.json()["id"]

    resp = client.get(
        f"/employee/vendors/{vendor_id}/menu?meal_date={_today_plus(0)}&available=true",
        headers=_eh(employee_id),
    )
    assert resp.status_code == 200
    item = next((i for i in resp.json() if i["id"] == item_id), None)
    assert item is not None
    assert item["price_cents"] == 1000
    assert item["available"] is True


def test_list_effective_with_price_override(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest EffPrice", "price_cents": 1000, "available": True},
    )
    item_id = create.json()["id"]
    target = _today_plus(1)

    client.put(
        f"/vendor/me/menu/{item_id}/schedule/{target}",
        headers=_vh(vendor_id),
        json={"price_cents": 1500},
    )

    resp = client.get(
        f"/employee/vendors/{vendor_id}/menu?meal_date={target}&available=true",
        headers=_eh(employee_id),
    )
    assert resp.status_code == 200
    item = next((i for i in resp.json() if i["id"] == item_id), None)
    assert item is not None
    assert item["price_cents"] == 1500


def test_list_effective_availability_override_hides_item(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest EffAvail", "price_cents": 1000, "available": True},
    )
    item_id = create.json()["id"]
    target = _today_plus(2)

    client.put(
        f"/vendor/me/menu/{item_id}/schedule/{target}",
        headers=_vh(vendor_id),
        json={"available": False},
    )

    resp = client.get(
        f"/employee/vendors/{vendor_id}/menu?meal_date={target}&available=true",
        headers=_eh(employee_id),
    )
    assert resp.status_code == 200
    assert not any(i["id"] == item_id for i in resp.json())


def test_list_effective_with_category_filter(client, seeded_ids):
    """Covers the category_id branch in list_effective."""
    vendor_id, employee_id = seeded_ids

    cat_resp = client.post(
        "/vendor/me/categories",
        headers=_vh(vendor_id),
        json={"name": "IntTest Cat"},
    )
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest EffCat", "price_cents": 1000, "available": True, "category_id": cat_id},
    )
    item_id = create.json()["id"]

    # Browse with category filter
    resp = client.get(
        f"/employee/vendors/{vendor_id}/menu?meal_date={_today_plus(0)}&category_id={cat_id}",
        headers=_eh(employee_id),
    )
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert item_id in ids

    # Cleanup category
    client.delete(f"/vendor/me/menu/{item_id}", headers=_vh(vendor_id))
    with get_connection() as conn:
        conn.execute("DELETE FROM menu_categories WHERE name = 'IntTest Cat' AND vendor_id = %s", (vendor_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# get_effective: covered via employee order creation
# ---------------------------------------------------------------------------


def test_get_effective_via_order_creation(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest GetEff", "price_cents": 2000, "available": True},
    )
    item_id = create.json()["id"]
    target = date.today().isoformat()

    resp = client.post(
        f"/employee/vendors/{vendor_id}/orders",
        headers=_eh(employee_id),
        json={"meal_date": target, "items": [{"item_id": item_id, "quantity": 1}]},
    )
    assert resp.status_code == 201
    assert resp.json()["items"][0]["unit_price_cents"] == 2000


def test_get_effective_with_price_override_in_order(client, seeded_ids):
    vendor_id, employee_id = seeded_ids

    create = client.post(
        "/vendor/me/menu",
        headers=_vh(vendor_id),
        json={"name": "IntTest GetEffOvr", "price_cents": 2000, "available": True},
    )
    item_id = create.json()["id"]
    target = (date.today() + timedelta(days=1)).isoformat()

    client.put(
        f"/vendor/me/menu/{item_id}/schedule/{target}",
        headers=_vh(vendor_id),
        json={"price_cents": 2500},
    )

    resp = client.post(
        f"/employee/vendors/{vendor_id}/orders",
        headers=_eh(employee_id),
        json={"meal_date": target, "items": [{"item_id": item_id, "quantity": 1}]},
    )
    assert resp.status_code == 201
    assert resp.json()["items"][0]["unit_price_cents"] == 2500


# ---------------------------------------------------------------------------
# Direct repo tests for paths not reachable through HTTP
# ---------------------------------------------------------------------------


def test_postgres_repo_get_date_override_direct(seeded_ids):
    """Directly test get_date_override — not exposed via any HTTP route."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")

    vendor_id, _ = seeded_ids
    repo = PostgresMenuItemRepository()

    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO menu_items (vendor_id, name, price_cents, available) "
            "VALUES (%s, 'IntTest DirectGet', 500, TRUE) RETURNING id",
            (vendor_id,),
        ).fetchone()
        conn.commit()
    item_id = row["id"]

    try:
        target = date.today() + timedelta(days=1)

        # No override yet — should return None
        result = repo.get_date_override(vendor_id=vendor_id, item_id=item_id, meal_date=target)
        assert result is None

        # Upsert an override then fetch it
        repo.upsert_date_override(
            vendor_id=vendor_id,
            item_id=item_id,
            meal_date=target,
            available=False,
            daily_quota=None,
            price_cents=None,
        )
        result = repo.get_date_override(vendor_id=vendor_id, item_id=item_id, meal_date=target)
        assert result is not None
        assert result.available is False

        # Wrong vendor should return None
        result = repo.get_date_override(vendor_id=99999, item_id=item_id, meal_date=target)
        assert result is None

    finally:
        with get_connection() as conn:
            conn.execute("DELETE FROM menu_item_date_overrides WHERE item_id = %s", (item_id,))
            conn.execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
            conn.commit()


def test_postgres_repo_set_and_clear_photo_path(seeded_ids):
    """Directly test set_photo_path / clear_photo_path (photo upload not easily tested via HTTP)."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")

    vendor_id, _ = seeded_ids
    repo = PostgresMenuItemRepository()

    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO menu_items (vendor_id, name, price_cents, available) "
            "VALUES (%s, 'IntTest Photo', 500, TRUE) RETURNING id",
            (vendor_id,),
        ).fetchone()
        conn.commit()
    item_id = row["id"]

    try:
        repo.set_photo_path(vendor_id=vendor_id, item_id=item_id, photo_path="/uploads/test.jpg")
        item = repo.get(vendor_id=vendor_id, item_id=item_id)
        assert item is not None
        assert item.photo_path == "/uploads/test.jpg"

        repo.clear_photo_path(vendor_id=vendor_id, item_id=item_id)
        item = repo.get(vendor_id=vendor_id, item_id=item_id)
        assert item.photo_path is None

    finally:
        with get_connection() as conn:
            conn.execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
            conn.commit()


def test_postgres_repo_has_items_in_category(seeded_ids):
    """Directly test has_items_in_category."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")

    vendor_id, _ = seeded_ids
    repo = PostgresMenuItemRepository()

    with get_connection() as conn:
        cat_row = conn.execute(
            "INSERT INTO menu_categories (vendor_id, name) VALUES (%s, 'IntTest HasCat') RETURNING id",
            (vendor_id,),
        ).fetchone()
        item_row = conn.execute(
            "INSERT INTO menu_items (vendor_id, category_id, name, price_cents, available) "
            "VALUES (%s, %s, 'IntTest HasCatItem', 500, TRUE) RETURNING id",
            (vendor_id, cat_row["id"]),
        ).fetchone()
        conn.commit()
    cat_id = cat_row["id"]
    item_id = item_row["id"]

    try:
        assert repo.has_items_in_category(vendor_id=vendor_id, category_id=cat_id) is True

        with get_connection() as conn:
            conn.execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
            conn.commit()
        item_id = None

        assert repo.has_items_in_category(vendor_id=vendor_id, category_id=cat_id) is False
    finally:
        with get_connection() as conn:
            if item_id is not None:
                conn.execute("DELETE FROM menu_items WHERE id = %s", (item_id,))
            conn.execute("DELETE FROM menu_categories WHERE id = %s", (cat_id,))
            conn.commit()


def test_postgres_repo_get_effective_not_found(seeded_ids):
    """Covers the None-return branch of get_effective."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")

    vendor_id, _ = seeded_ids
    repo = PostgresMenuItemRepository()
    result = repo.get_effective(vendor_id=vendor_id, item_id=999999, meal_date=date.today())
    assert result is None
