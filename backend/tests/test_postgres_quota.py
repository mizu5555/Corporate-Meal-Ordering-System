"""Unit tests for atomic quota deduction in PostgresEmployeeSelectionRepository.

Tests verify that create_order():
  - issues SELECT ... FOR UPDATE on menu_items (row lock)
  - raises 409 QUOTA_EXHAUSTED when quota is full
  - marks item available=FALSE when quota reaches zero (issue #53)
  - raises 409 ITEM_UNAVAILABLE for unavailable items
  - raises 404 not_found for missing items
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, call, patch

import pytest

from backend.repositories.employee_selection_repository import OrderItemSnapshot
from backend.repositories.postgres_employee_selection_repository import (
    PostgresEmployeeSelectionRepository,
)

_MEAL_DATE = date(2026, 6, 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _menu_row(daily_quota: int | None = 10, available: bool = True) -> dict:
    return {"id": 1, "daily_quota": daily_quota, "available": available}


def _used_row(used: int = 0) -> dict:
    return {"used": used}


def _order_row() -> dict:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return {
        "id": 99,
        "employee_id": 1,
        "vendor_id": 2,
        "meal_date": _MEAL_DATE,
        "status": "pending",
        "total_price_cents": 1000,
        "created_at": now,
        "updated_at": now,
        "cancelled_at": None,
    }


def _item_row(order_id: int = 99) -> dict:
    return {
        "id": 1,
        "order_id": order_id,
        "item_id": 1,
        "item_name": "Burger",
        "quantity": 1,
        "unit_price_cents": 1000,
        "total_price_cents": 1000,
    }


def _snapshot(quantity: int = 1) -> OrderItemSnapshot:
    return OrderItemSnapshot(
        item_id=1, item_name="Burger", quantity=quantity, unit_price_cents=1000
    )


def _conn_with_side_effects(*results) -> MagicMock:
    """Build a mock connection whose execute() calls return the given results in order."""
    conn = MagicMock()
    side = []
    for r in results:
        mock_result = MagicMock()
        if isinstance(r, list):
            mock_result.fetchone.return_value = r[0] if r else None
            mock_result.fetchall.return_value = r
        else:
            mock_result.fetchone.return_value = r
        side.append(mock_result)
    conn.execute.side_effect = side

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# FOR UPDATE row lock
# ---------------------------------------------------------------------------

def test_create_order_uses_for_update_lock() -> None:
    """The first SELECT on menu_items must include FOR UPDATE."""
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=None),  # menu_items SELECT FOR UPDATE
        _order_row(),                 # INSERT orders
        _item_row(),                  # INSERT order_items
    )
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        repo.create_order(
            employee_id=1, vendor_id=2, items=[_snapshot()], meal_date=_MEAL_DATE
        )

    first_sql_call = ctx.__enter__.return_value.execute.call_args_list[0]
    sql = first_sql_call[0][0]
    assert "FOR UPDATE" in sql.upper()


def test_list_orders_filters_by_employee_and_date_range() -> None:
    order_rows = [
        {
            **_order_row(),
            "pickup_code": "0601-0099",
            "pickup_confirmed_at": None,
            "pickup_confirmed_by_user_id": None,
            "facility_id": None,
        }
    ]
    ctx = _conn_with_side_effects(order_rows)

    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with patch.object(repo, "_hydrate_order", side_effect=lambda _conn, row: row):
            rows = repo.list_orders(
                employee_id=1,
                start_date=date(2026, 5, 1),
                end_date=date(2026, 6, 7),
            )

    sql, values = ctx.__enter__.return_value.execute.call_args.args
    assert "employee_id = %s" in sql
    assert "COALESCE(meal_date, created_at::date) >= %s" in sql
    assert "COALESCE(meal_date, created_at::date) <= %s" in sql
    assert values == [1, date(2026, 5, 1), date(2026, 6, 7)]
    assert rows == order_rows


# ---------------------------------------------------------------------------
# Quota exhausted
# ---------------------------------------------------------------------------

def test_create_order_raises_quota_exhausted_when_used_equals_quota() -> None:
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=5),   # menu_items lock
        _used_row(used=5),          # SUM(quantity) = quota
    )
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with pytest.raises(Exception) as exc_info:
            repo.create_order(
                employee_id=1, vendor_id=2, items=[_snapshot(1)], meal_date=_MEAL_DATE
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "QUOTA_EXHAUSTED"


def test_create_order_raises_quota_exhausted_when_request_would_exceed() -> None:
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=5),
        _used_row(used=4),   # 4 used + 2 requested = 6 > 5
    )
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with pytest.raises(Exception) as exc_info:
            repo.create_order(
                employee_id=1, vendor_id=2, items=[_snapshot(2)], meal_date=_MEAL_DATE
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "QUOTA_EXHAUSTED"


def test_create_order_succeeds_when_used_plus_requested_equals_quota() -> None:
    """Exactly filling the quota is still allowed; item gets marked sold out."""
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=5),
        _used_row(used=4),   # 4 + 1 = 5 = quota → allowed, then sold out
        None,                # UPDATE available=FALSE
        _order_row(),
        _item_row(),
    )
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        order = repo.create_order(
            employee_id=1, vendor_id=2, items=[_snapshot(1)], meal_date=_MEAL_DATE
        )

    assert order.id == 99


# ---------------------------------------------------------------------------
# Auto sold-out (issue #53)
# ---------------------------------------------------------------------------

def test_create_order_marks_sold_out_when_last_quota_taken() -> None:
    """When remaining quota hits zero, available=FALSE must be set in the same tx."""
    conn = MagicMock()
    execute_results = [
        MagicMock(**{"fetchone.return_value": _menu_row(daily_quota=3)}),  # FOR UPDATE
        MagicMock(**{"fetchone.return_value": _used_row(used=2)}),         # SUM
        MagicMock(**{"fetchone.return_value": None}),                       # UPDATE available
        MagicMock(**{"fetchone.return_value": _order_row()}),               # INSERT order
        MagicMock(**{"fetchone.return_value": _item_row()}),                # INSERT order_item
    ]
    conn.execute.side_effect = execute_results
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)

    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        repo.create_order(
            employee_id=1, vendor_id=2, items=[_snapshot(1)], meal_date=_MEAL_DATE
        )

    # Find the UPDATE call that sets available = FALSE
    all_sqls = [str(c[0][0]) for c in conn.execute.call_args_list]
    sold_out_calls = [s for s in all_sqls if "available" in s.lower() and "false" in s.lower()]
    assert sold_out_calls, "Expected an UPDATE menu_items SET available = FALSE"


def test_create_order_does_not_mark_sold_out_when_quota_not_exhausted() -> None:
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=10),
        _used_row(used=3),   # 3 + 1 = 4 < 10 → no sold-out update
        _order_row(),
        _item_row(),
    )
    conn = ctx.__enter__.return_value

    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        repo.create_order(
            employee_id=1, vendor_id=2, items=[_snapshot(1)], meal_date=_MEAL_DATE
        )

    all_sqls = [str(c[0][0]) for c in conn.execute.call_args_list]
    sold_out_calls = [s for s in all_sqls if "available" in s.lower() and "false" in s.lower()]
    assert not sold_out_calls, "Should NOT update available when quota not exhausted"


def test_create_order_skips_quota_check_when_daily_quota_is_none() -> None:
    """Items with no quota limit should never trigger QUOTA_EXHAUSTED."""
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=None),  # no quota limit
        _order_row(),
        _item_row(),
    )
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        order = repo.create_order(
            employee_id=1, vendor_id=2, items=[_snapshot(999)], meal_date=_MEAL_DATE
        )

    assert order.id == 99


# ---------------------------------------------------------------------------
# Item unavailable / not found
# ---------------------------------------------------------------------------

def test_create_order_raises_item_unavailable() -> None:
    ctx = _conn_with_side_effects(_menu_row(daily_quota=None, available=False))
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with pytest.raises(Exception) as exc_info:
            repo.create_order(
                employee_id=1, vendor_id=2, items=[_snapshot()], meal_date=_MEAL_DATE
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "ITEM_UNAVAILABLE"


def test_create_order_returns_quota_exhausted_when_auto_sold_out_item_is_full() -> None:
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=5, available=False),
        _used_row(used=5),
    )
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with pytest.raises(Exception) as exc_info:
            repo.create_order(
                employee_id=1, vendor_id=2, items=[_snapshot()], meal_date=_MEAL_DATE
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "QUOTA_EXHAUSTED"


def test_create_order_returns_item_unavailable_when_vendor_disabled_before_quota_full() -> None:
    ctx = _conn_with_side_effects(
        _menu_row(daily_quota=5, available=False),
        _used_row(used=3),
    )
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with pytest.raises(Exception) as exc_info:
            repo.create_order(
                employee_id=1, vendor_id=2, items=[_snapshot()], meal_date=_MEAL_DATE
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "ITEM_UNAVAILABLE"


def test_create_order_translates_lock_conflict_to_concurrent_conflict() -> None:
    from backend.repositories import postgres_employee_selection_repository as repo_module

    if not repo_module._PSYCOPG_CONFLICT_ERRORS:
        pytest.skip("psycopg is not installed")

    conn = MagicMock()
    conn.execute.side_effect = repo_module._PSYCOPG_CONFLICT_ERRORS[0]("lock conflict")
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)

    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with pytest.raises(Exception) as exc_info:
            repo.create_order(
                employee_id=1, vendor_id=2, items=[_snapshot()], meal_date=_MEAL_DATE
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONCURRENT_CONFLICT"


def test_create_order_raises_not_found_for_missing_item() -> None:
    ctx = _conn_with_side_effects(None)  # menu_items row not found
    with patch(
        "backend.repositories.postgres_employee_selection_repository.get_connection",
        return_value=ctx,
    ):
        repo = PostgresEmployeeSelectionRepository()
        with pytest.raises(Exception) as exc_info:
            repo.create_order(
                employee_id=1, vendor_id=2, items=[_snapshot()], meal_date=_MEAL_DATE
            )

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"
