"""Unit tests for per-date menu scheduling (override CRUD + effective resolution).

Tests cover:
  - Base fallback: no override → base values used everywhere (ordering, browse, random)
  - Per-date quota override: ordering respects the overridden quota
  - Per-date availability off: item not orderable / not visible for that day
  - Per-date price override: snapshot captures the overridden price
  - Non-overridden date: base values unchanged for other dates
  - CRUD endpoints via HTTP: list, upsert, delete
  - Validation: date outside 7-day window rejected
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.core.audit import get_audit_log_repository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.employee_selection_repository import EmployeeSelectionRepository
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.employee_ordering import get_employee_selection_repository
from backend.routes.vendor_menu import get_menu_item_repository
from backend.services.employee_ordering_service import EmployeeOrderingService
from backend.services.vendor_menu_service import VendorMenuService, MENU_DATE_WINDOW_DAYS
from backend.repositories.menu_category_repository import MenuCategoryRepository
from backend.storage.photo_storage import PhotoStorage
from unittest.mock import MagicMock


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_repos():
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(VendorRecord(id=1, name="Bento", status="approved", address="No.1"))
    item_repo = MenuItemRepository()
    selection_repo = EmployeeSelectionRepository()
    return vendor_repo, item_repo, selection_repo


def _make_service(vendor_repo, item_repo, selection_repo):
    return EmployeeOrderingService(
        vendor_repository=vendor_repo,
        menu_item_repository=item_repo,
        selection_repository=selection_repo,
        audit_log_repository=AuditLogRepository(),
    )


def _make_vendor_menu_service(item_repo):
    cat_repo = MenuCategoryRepository()
    storage = MagicMock(spec=PhotoStorage)
    return VendorMenuService(item_repo, cat_repo, storage)


def _setup_http():
    vendor_repo, item_repo, selection_repo = _make_repos()
    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_menu_item_repository] = lambda: item_repo
    app.dependency_overrides[get_employee_selection_repository] = lambda: selection_repo
    app.dependency_overrides[get_audit_log_repository] = lambda: AuditLogRepository()
    return TestClient(app), vendor_repo, item_repo, selection_repo


def teardown_function():
    app.dependency_overrides.clear()


def _today_plus(days: int) -> date:
    return date.today() + timedelta(days=days)


def _vh() -> dict:
    return {"x-user-role": "vendor_manager", "x-vendor-id": "1"}


def _eh(uid: int = 99) -> dict:
    return {"x-user-role": "employee", "x-user-id": str(uid)}


# ── 1. Base fallback ──────────────────────────────────────────────────────────


def test_base_fallback_no_override_browse() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True, daily_quota=10)
    svc = _make_service(vendor_repo, item_repo, selection_repo)

    items = svc.list_menu(1, meal_date=_today_plus(0))
    assert len(items) == 1
    assert items[0].available is True
    assert items[0].daily_quota == 10
    assert items[0].price_cents == 8000


def test_base_fallback_no_override_order_price() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    svc = _make_service(vendor_repo, item_repo, selection_repo)

    from backend.schemas.employee import EmployeeOrderCreate, EmployeeOrderItemCreate
    order = svc.create_order(
        10, 1,
        EmployeeOrderCreate(
            meal_date=_today_plus(1),
            items=[EmployeeOrderItemCreate(item_id=item.id, quantity=1)],
        ),
    )
    assert order.items[0].unit_price_cents == 8000


# ── 2. Per-date quota override ────────────────────────────────────────────────


def test_per_date_quota_override_allows_order_within_new_quota() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True, daily_quota=5)
    target = _today_plus(1)
    # Set override: only 2 allowed on target day
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=None, daily_quota=2, price_cents=None,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)
    from backend.schemas.employee import EmployeeOrderCreate, EmployeeOrderItemCreate

    order = svc.create_order(
        10, 1,
        EmployeeOrderCreate(
            meal_date=target,
            items=[EmployeeOrderItemCreate(item_id=item.id, quantity=2)],
        ),
    )
    assert order.items[0].quantity == 2


def test_per_date_quota_override_blocks_order_exceeding_new_quota() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True, daily_quota=10)
    target = _today_plus(1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=None, daily_quota=1, price_cents=None,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)
    from backend.schemas.employee import EmployeeOrderCreate, EmployeeOrderItemCreate
    from backend.core.errors import CodedHTTPException

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.create_order(
            10, 1,
            EmployeeOrderCreate(
                meal_date=target,
                items=[EmployeeOrderItemCreate(item_id=item.id, quantity=2)],
            ),
        )
    assert exc_info.value.code == "QUOTA_EXHAUSTED"


def test_per_date_quota_override_zero_means_sold_out() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True, daily_quota=10)
    target = _today_plus(1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=None, daily_quota=0, price_cents=None,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)
    from backend.schemas.employee import EmployeeOrderCreate, EmployeeOrderItemCreate
    from backend.core.errors import CodedHTTPException

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.create_order(
            10, 1,
            EmployeeOrderCreate(
                meal_date=target,
                items=[EmployeeOrderItemCreate(item_id=item.id, quantity=1)],
            ),
        )
    assert exc_info.value.code == "QUOTA_EXHAUSTED"


# ── 3. Per-date availability off ──────────────────────────────────────────────


def test_per_date_availability_off_hides_item_from_browse() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=False, daily_quota=None, price_cents=None,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)

    items = svc.list_menu(1, meal_date=target)
    assert items == []  # available=True filter hides this item


def test_per_date_availability_off_blocks_ordering() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=False, daily_quota=None, price_cents=None,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)
    from backend.schemas.employee import EmployeeOrderCreate, EmployeeOrderItemCreate
    from backend.core.errors import CodedHTTPException

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.create_order(
            10, 1,
            EmployeeOrderCreate(
                meal_date=target,
                items=[EmployeeOrderItemCreate(item_id=item.id, quantity=1)],
            ),
        )
    assert exc_info.value.code == "ITEM_UNAVAILABLE"


# ── 4. Per-date price override ────────────────────────────────────────────────


def test_per_date_price_override_used_in_order_snapshot() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=None, daily_quota=None, price_cents=9500,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)
    from backend.schemas.employee import EmployeeOrderCreate, EmployeeOrderItemCreate

    order = svc.create_order(
        10, 1,
        EmployeeOrderCreate(
            meal_date=target,
            items=[EmployeeOrderItemCreate(item_id=item.id, quantity=1)],
        ),
    )
    assert order.items[0].unit_price_cents == 9500


def test_per_date_price_override_shown_in_browse() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=None, daily_quota=None, price_cents=9500,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)

    items = svc.list_menu(1, meal_date=target)
    assert items[0].price_cents == 9500


# ── 5. Non-overridden date unaffected ─────────────────────────────────────────


def test_override_on_one_date_does_not_affect_other_dates() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True, daily_quota=10)
    target = _today_plus(2)
    other = _today_plus(3)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=False, daily_quota=0, price_cents=9999,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)

    items_other = svc.list_menu(1, meal_date=other)
    assert len(items_other) == 1
    assert items_other[0].available is True
    assert items_other[0].daily_quota == 10
    assert items_other[0].price_cents == 8000


# ── 6. HTTP CRUD endpoints ────────────────────────────────────────────────────


def test_put_schedule_creates_override() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1).isoformat()

    resp = client.put(
        f"/vendor/me/menu/{item.id}/schedule/{target}",
        headers=_vh(),
        json={"available": False, "daily_quota": 5, "price_cents": 9000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["item_id"] == item.id
    assert body["meal_date"] == target
    assert body["available"] is False
    assert body["daily_quota"] == 5
    assert body["price_cents"] == 9000


def test_put_schedule_marks_item_as_daily_recommended_for_employee_browse() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(0).isoformat()

    resp = client.put(
        f"/vendor/me/menu/{item.id}/schedule/{target}",
        headers=_vh(),
        json={"is_recommended": True},
    )

    assert resp.status_code == 200
    assert resp.json()["is_recommended"] is True

    menu = client.get(
        "/employee/vendors/1/menu",
        headers=_eh(),
        params={"meal_date": target},
    )
    assert menu.status_code == 200
    assert menu.json()[0]["is_recommended"] is True


def test_put_schedule_rejects_recommendations_over_vendor_limit() -> None:
    client, vendor_repo, item_repo, _ = _setup_http()
    vendor_repo.update(1, {"daily_recommendation_limit": 1})
    first = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    second = item_repo.create(vendor_id=1, name="Noodles", price_cents=9000, available=True)
    target = _today_plus(0).isoformat()

    ok = client.put(
        f"/vendor/me/menu/{first.id}/schedule/{target}",
        headers=_vh(),
        json={"is_recommended": True},
    )
    over = client.put(
        f"/vendor/me/menu/{second.id}/schedule/{target}",
        headers=_vh(),
        json={"is_recommended": True},
    )

    assert ok.status_code == 200
    assert over.status_code == 409
    assert over.json()["code"] == "daily_recommendation_limit_exceeded"


def test_put_schedule_is_idempotent() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1).isoformat()

    client.put(
        f"/vendor/me/menu/{item.id}/schedule/{target}",
        headers=_vh(),
        json={"daily_quota": 5},
    )
    resp = client.put(
        f"/vendor/me/menu/{item.id}/schedule/{target}",
        headers=_vh(),
        json={"daily_quota": 3},
    )
    assert resp.status_code == 200
    assert resp.json()["daily_quota"] == 3


def test_get_schedule_list() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    d1 = _today_plus(1).isoformat()
    d2 = _today_plus(2).isoformat()

    client.put(f"/vendor/me/menu/{item.id}/schedule/{d1}", headers=_vh(), json={"daily_quota": 5})
    client.put(f"/vendor/me/menu/{item.id}/schedule/{d2}", headers=_vh(), json={"available": False})

    resp = client.get(f"/vendor/me/menu/{item.id}/schedule", headers=_vh())
    assert resp.status_code == 200
    dates = [r["meal_date"] for r in resp.json()]
    assert d1 in dates
    assert d2 in dates


def test_delete_schedule_removes_override() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1).isoformat()

    client.put(f"/vendor/me/menu/{item.id}/schedule/{target}", headers=_vh(), json={"daily_quota": 5})

    del_resp = client.delete(f"/vendor/me/menu/{item.id}/schedule/{target}", headers=_vh())
    assert del_resp.status_code == 204

    list_resp = client.get(f"/vendor/me/menu/{item.id}/schedule", headers=_vh())
    assert list_resp.json() == []


def test_delete_schedule_nonexistent_is_ok() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    resp = client.delete(
        f"/vendor/me/menu/{item.id}/schedule/{_today_plus(1).isoformat()}",
        headers=_vh(),
    )
    assert resp.status_code == 204


# ── 7. Date-window validation ─────────────────────────────────────────────────


def test_put_schedule_rejects_past_date() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    resp = client.put(
        f"/vendor/me/menu/{item.id}/schedule/{yesterday}",
        headers=_vh(),
        json={"daily_quota": 5},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"


def test_put_schedule_rejects_date_beyond_window() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    far_date = (date.today() + timedelta(days=MENU_DATE_WINDOW_DAYS)).isoformat()

    resp = client.put(
        f"/vendor/me/menu/{item.id}/schedule/{far_date}",
        headers=_vh(),
        json={"daily_quota": 5},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"


def test_put_schedule_accepts_last_day_of_window() -> None:
    client, _, item_repo, _ = _setup_http()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    last_day = (date.today() + timedelta(days=MENU_DATE_WINDOW_DAYS - 1)).isoformat()

    resp = client.put(
        f"/vendor/me/menu/{item.id}/schedule/{last_day}",
        headers=_vh(),
        json={"daily_quota": 5},
    )
    assert resp.status_code == 200


# ── 8. Random draw respects per-date availability ────────────────────────────


def test_random_draw_skips_unavailable_item_on_date() -> None:
    vendor_repo, item_repo, selection_repo = _make_repos()
    item = item_repo.create(vendor_id=1, name="Rice Box", price_cents=8000, available=True)
    target = _today_plus(1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=False, daily_quota=None, price_cents=None,
    )
    svc = _make_service(vendor_repo, item_repo, selection_repo)
    from backend.schemas.employee import RandomMealDrawRequest
    from backend.core.errors import CodedHTTPException

    with pytest.raises(CodedHTTPException) as exc_info:
        svc.draw_random_meal(RandomMealDrawRequest(meal_date=target, vendor_ids=[1]))
    assert exc_info.value.code == "no_random_meal_available"


# ── 9. In-memory repo guard clauses (covers missing lines in menu_item_repository.py) ──


def test_inmem_update_wrong_vendor_returns_none() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    result = item_repo.update(vendor_id=2, item_id=item.id, fields={"name": "Y"})
    assert result is None


def test_inmem_delete_wrong_vendor_returns_false() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    result = item_repo.delete(vendor_id=2, item_id=item.id)
    assert result is False


def test_inmem_delete_cascades_overrides() -> None:
    """Deleting an item must remove its per-date overrides (line 165)."""
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    target = date.today() + timedelta(days=1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=None, daily_quota=5, price_cents=None,
    )
    assert len(item_repo._overrides) == 1
    item_repo.delete(vendor_id=1, item_id=item.id)
    assert len(item_repo._overrides) == 0


def test_inmem_set_photo_wrong_vendor_is_noop() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    item_repo.set_photo_path(vendor_id=2, item_id=item.id, photo_path="/test.jpg")
    result = item_repo.get(vendor_id=1, item_id=item.id)
    assert result is not None
    assert result.photo_path is None  # unchanged — guard clause fired


def test_inmem_clear_photo_wrong_vendor_is_noop() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    item_repo.set_photo_path(vendor_id=1, item_id=item.id, photo_path="/test.jpg")
    item_repo.clear_photo_path(vendor_id=2, item_id=item.id)
    result = item_repo.get(vendor_id=1, item_id=item.id)
    assert result is not None
    assert result.photo_path == "/test.jpg"  # unchanged — guard clause fired


def test_inmem_get_effective_wrong_vendor_returns_none() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    result = item_repo.get_effective(vendor_id=2, item_id=item.id, meal_date=date.today())
    assert result is None


def test_inmem_list_date_overrides_wrong_vendor_returns_empty() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    result = item_repo.list_date_overrides(vendor_id=2, item_id=item.id)
    assert result == []


def test_inmem_get_date_override_item_not_found() -> None:
    _, item_repo, _ = _make_repos()
    result = item_repo.get_date_override(vendor_id=1, item_id=9999, meal_date=date.today())
    assert result is None


def test_inmem_get_date_override_no_override_for_date() -> None:
    """Item exists but no override for the given date — returns None."""
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    result = item_repo.get_date_override(vendor_id=1, item_id=item.id, meal_date=date.today())
    assert result is None


def test_inmem_get_date_override_returns_existing_override() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    target = date.today() + timedelta(days=1)
    item_repo.upsert_date_override(
        vendor_id=1, item_id=item.id, meal_date=target,
        available=False, daily_quota=None, price_cents=None,
    )
    result = item_repo.get_date_override(vendor_id=1, item_id=item.id, meal_date=target)
    assert result is not None
    assert result.available is False


def test_inmem_upsert_date_override_wrong_vendor_raises() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    with pytest.raises(KeyError):
        item_repo.upsert_date_override(
            vendor_id=2, item_id=item.id, meal_date=date.today() + timedelta(days=1),
            available=None, daily_quota=5, price_cents=None,
        )


def test_inmem_delete_date_override_wrong_vendor_returns_false() -> None:
    _, item_repo, _ = _make_repos()
    item = item_repo.create(vendor_id=1, name="X", price_cents=100)
    result = item_repo.delete_date_override(vendor_id=2, item_id=item.id, meal_date=date.today())
    assert result is False
