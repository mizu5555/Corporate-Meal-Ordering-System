"""Unit tests for GET /vendor/me/revenue."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.core.reporting import get_reporting_repository
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.main import app
from backend.repositories.menu_item_repository import MenuItemRepository
from backend.repositories.reporting_repository import ReportingRepository
from backend.repositories.vendor_profile_repository import VendorProfileRepository, VendorRecord
from backend.routes.vendor_menu import get_menu_item_repository


@pytest.fixture()
def client():
    vendor_repo = VendorProfileRepository()
    vendor_repo.seed(VendorRecord(id=1, name="Noodle House", status="approved"))
    vendor_repo.assign_facility(1, facility_id=10, code="F10", name="Fab 10")

    item_repo = MenuItemRepository()
    rice = item_repo.create(vendor_id=1, name="Rice Bowl", price_cents=120, daily_quota=5)
    soup = item_repo.create(vendor_id=1, name="Soup", price_cents=90, daily_quota=None)

    today = date(2026, 5, 30)
    yesterday = date(2026, 5, 29)
    today_ts = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
    yesterday_ts = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)

    reporting_repo = ReportingRepository()
    reporting_repo.seed_order(
        order_id=1, vendor_id=1, vendor_name="Noodle House",
        facility_id=10, facility_name="Fab 10", status="pending",
        created_at=today_ts, meal_date=today,
        items=[(rice.id, 2, rice.price_cents), (soup.id, 1, soup.price_cents)],
    )
    reporting_repo.seed_order(
        order_id=2, vendor_id=1, vendor_name="Noodle House",
        facility_id=10, facility_name="Fab 10", status="pending",
        created_at=yesterday_ts, meal_date=yesterday,
        items=[(rice.id, 1, rice.price_cents)],
    )
    reporting_repo.seed_order(
        order_id=3, vendor_id=1, vendor_name="Noodle House",
        facility_id=10, facility_name="Fab 10", status="cancelled",
        created_at=today_ts, meal_date=today,
        items=[(rice.id, 3, rice.price_cents)],
    )

    app.dependency_overrides[get_vendor_profile_repository] = lambda: vendor_repo
    app.dependency_overrides[get_menu_item_repository] = lambda: item_repo
    app.dependency_overrides[get_reporting_repository] = lambda: reporting_repo
    yield TestClient(app)
    app.dependency_overrides.pop(get_vendor_profile_repository, None)
    app.dependency_overrides.pop(get_menu_item_repository, None)
    app.dependency_overrides.pop(get_reporting_repository, None)


_VENDOR_HEADERS = {"x-user-role": "vendor_manager", "x-vendor-id": "1"}


def test_vendor_revenue_dashboard_counts_today_stock_and_period_sales(client) -> None:
    resp = client.get(
        "/vendor/me/revenue?today=2026-05-30&start=2026-05-29&end=2026-05-30&facility_id=10",
        headers=_VENDOR_HEADERS,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == {
        "order_count": 2,
        "quantity_sold": 4,
        "revenue_cents": 450,
    }

    today_by_name = {item["item_name"]: item for item in body["today_items"]}
    assert today_by_name["Rice Bowl"]["sold_quantity"] == 2
    assert today_by_name["Rice Bowl"]["remaining_quantity"] == 3
    assert today_by_name["Rice Bowl"]["revenue_cents"] == 240
    assert today_by_name["Soup"]["sold_quantity"] == 1
    assert today_by_name["Soup"]["remaining_quantity"] is None

    period_by_name = {item["item_name"]: item for item in body["period_items"]}
    assert period_by_name["Rice Bowl"]["quantity_sold"] == 3
    assert period_by_name["Rice Bowl"]["order_count"] == 2
    assert period_by_name["Soup"]["quantity_sold"] == 1


def test_vendor_revenue_rejects_unknown_facility(client) -> None:
    resp = client.get(
        "/vendor/me/revenue?today=2026-05-30&facility_id=99",
        headers=_VENDOR_HEADERS,
    )

    assert resp.status_code == 403
    assert resp.json()["code"] == "forbidden"


def test_vendor_revenue_rejects_invalid_range(client) -> None:
    resp = client.get(
        "/vendor/me/revenue?start=2026-05-31&end=2026-05-30",
        headers=_VENDOR_HEADERS,
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "validation_error"
