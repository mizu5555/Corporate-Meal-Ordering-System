"""Lifespan-time seed for the K6 smoke vendor.

Guards:
1. Env var off  → no seed (default, prod behaviour).
2. Env var "1"  → vendor 99 exists, approved, named "K6 Smoke Vendor".
3. Env var "0" / unset / anything-not-"1" → no seed (strict comparison).

If a future change ever drops the env-var guard or expands the seed beyond
the single bot vendor, these tests will catch it before staging picks up
the regression.
"""
from __future__ import annotations

import importlib

import pytest

import backend.main as backend_main
from backend.core.vendor_identity import _REPO_SINGLETON as _VENDOR_REPO_SINGLETON


@pytest.fixture(autouse=True)
def _clear_repo_state() -> None:
    """Each test starts from an empty repo regardless of execution order."""
    _VENDOR_REPO_SINGLETON._vendors.clear()
    _VENDOR_REPO_SINGLETON._facilities.clear()
    yield
    _VENDOR_REPO_SINGLETON._vendors.clear()
    _VENDOR_REPO_SINGLETON._facilities.clear()


def test_seed_skipped_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEED_K6_SMOKE_VENDOR", raising=False)
    backend_main._seed_k6_smoke_vendor()
    assert _VENDOR_REPO_SINGLETON.get(99) is None


def test_seed_skipped_when_env_not_exactly_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # Anything other than the exact string "1" must not trigger seeding —
    # avoids accidental enables from "true" / "yes" / "TRUE" / "0".
    for value in ("0", "true", "yes", "TRUE", "", " 1 "):
        monkeypatch.setenv("SEED_K6_SMOKE_VENDOR", value)
        backend_main._seed_k6_smoke_vendor()
        assert _VENDOR_REPO_SINGLETON.get(99) is None, (
            f"unexpected seed for env value {value!r}"
        )


def test_seed_creates_approved_vendor_when_env_is_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEED_K6_SMOKE_VENDOR", "1")
    backend_main._seed_k6_smoke_vendor()

    record = _VENDOR_REPO_SINGLETON.get(99)
    assert record is not None
    assert record.id == 99
    assert record.status == "approved"
    assert record.name == "K6 Smoke Vendor"


def test_seed_emits_warning_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A warning level entry is the canary for accidental prod activation."""
    monkeypatch.setenv("SEED_K6_SMOKE_VENDOR", "1")
    with caplog.at_level("WARNING", logger="backend.main"):
        backend_main._seed_k6_smoke_vendor()
    assert any(
        "K6 smoke vendor" in r.message and r.levelname == "WARNING"
        for r in caplog.records
    )


def test_seed_only_affects_target_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Seeding must not touch unrelated vendor ids that the test may rely on."""
    monkeypatch.setenv("SEED_K6_SMOKE_VENDOR", "1")
    backend_main._seed_k6_smoke_vendor()
    assert _VENDOR_REPO_SINGLETON.get(1) is None
    assert _VENDOR_REPO_SINGLETON.get(2) is None
