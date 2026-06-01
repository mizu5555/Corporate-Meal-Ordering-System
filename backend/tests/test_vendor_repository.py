from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.repositories.vendor_repository import VendorRepository
from backend.schemas.vendor import VendorApplicationCreate


def _result(*, one=None, all_rows=None) -> MagicMock:
    result = MagicMock()
    result.fetchone.return_value = one
    result.fetchall.return_value = [] if all_rows is None else all_rows
    return result


def _conn_ctx(*results: MagicMock) -> MagicMock:
    conn = MagicMock()
    conn.execute.side_effect = results
    ctx = MagicMock()
    ctx.__enter__.return_value = conn
    ctx.__exit__.return_value = False
    return ctx


def _application_row() -> dict:
    return {
        "application_id": 501,
        "status": "pending",
        "review_reason": None,
        "reviewed_at": None,
        "submitted_at": datetime(2026, 5, 30, tzinfo=timezone.utc),
        "vendor_id": 77,
        "vendor_name": "My Kitchen",
        "address": "1 Main St",
        "business_hours": "11:00-14:00",
        "contact_phone": "02-1234-5678",
        "contact_email": "k@example.com",
    }


def _facility_rows() -> list[dict]:
    return [
        {"id": 1, "code": "F12A", "name": "Fab 12A"},
        {"id": 2, "code": "F14B", "name": "Fab 14B"},
    ]


def test_create_application_persists_and_returns_served_facilities() -> None:
    submitted_at = datetime(2026, 5, 30, tzinfo=timezone.utc)
    ctx = _conn_ctx(
        _result(one={"id": 77}),
        _result(),
        _result(),
        _result(one={"id": 501, "created_at": submitted_at}),
        _result(all_rows=_facility_rows()),
    )
    payload = VendorApplicationCreate(
        vendor_name="My Kitchen",
        address="1 Main St",
        business_hours="11:00-14:00",
        contact_phone="02-1234-5678",
        contact_email="k@example.com",
        facility_ids=[1, 2],
    )

    with patch("backend.repositories.vendor_repository.get_connection", return_value=ctx):
        detail = VendorRepository().create_application(user_id=42, data=payload)

    conn = ctx.__enter__.return_value
    facility_insert_params = [
        call.args[1]
        for call in conn.execute.call_args_list
        if "INSERT INTO vendor_facilities" in call.args[0]
    ]
    assert facility_insert_params == [(77, 1), (77, 2)]
    assert detail.application_id == 501
    assert detail.vendor_id == 77
    assert [facility.id for facility in detail.served_facilities] == [1, 2]


def test_get_my_application_returns_served_facilities() -> None:
    ctx = _conn_ctx(
        _result(one=_application_row()),
        _result(all_rows=_facility_rows()),
    )

    with patch("backend.repositories.vendor_repository.get_connection", return_value=ctx):
        detail = VendorRepository().get_my_application(user_id=42)

    assert detail is not None
    assert detail.vendor_id == 77
    assert [facility.code for facility in detail.served_facilities] == ["F12A", "F14B"]


def test_get_my_application_returns_none_when_missing() -> None:
    ctx = _conn_ctx(_result(one=None))

    with patch("backend.repositories.vendor_repository.get_connection", return_value=ctx):
        detail = VendorRepository().get_my_application(user_id=42)

    assert detail is None


def test_get_application_returns_served_facilities() -> None:
    ctx = _conn_ctx(
        _result(
            one={
                **_application_row(),
                "submitter_email": "owner@example.com",
                "submitter_name": "Owner",
            }
        ),
        _result(all_rows=_facility_rows()),
    )

    with patch("backend.repositories.vendor_repository.get_connection", return_value=ctx):
        detail = VendorRepository().get_application(application_id=501)

    assert detail is not None
    assert detail.submitter_email == "owner@example.com"
    assert [facility.name for facility in detail.served_facilities] == ["Fab 12A", "Fab 14B"]


def test_get_application_returns_none_when_missing() -> None:
    ctx = _conn_ctx(_result(one=None))

    with patch("backend.repositories.vendor_repository.get_connection", return_value=ctx):
        detail = VendorRepository().get_application(application_id=501)

    assert detail is None
