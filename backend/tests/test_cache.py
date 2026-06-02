"""Unit tests for the in-process TTL cache utility (backend/core/cache.py)."""
from __future__ import annotations

import backend.core.cache as cache_module
from backend.core.cache import TTLCache


def test_get_or_set_caches_within_ttl(monkeypatch) -> None:
    """Second call within the TTL returns the cached value without re-running producer."""
    clock = {"now": 1000.0}
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: clock["now"])

    calls = {"n": 0}

    def produce() -> str:
        calls["n"] += 1
        return f"value-{calls['n']}"

    cache = TTLCache(ttl_seconds=30.0)

    assert cache.get_or_set("k", produce) == "value-1"
    clock["now"] += 10.0  # still inside the 30s window
    assert cache.get_or_set("k", produce) == "value-1"
    assert calls["n"] == 1


def test_get_or_set_refreshes_after_ttl(monkeypatch) -> None:
    """Once the TTL elapses the producer runs again and the new value is stored."""
    clock = {"now": 0.0}
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: clock["now"])

    calls = {"n": 0}

    def produce() -> int:
        calls["n"] += 1
        return calls["n"]

    cache = TTLCache(ttl_seconds=5.0)

    assert cache.get_or_set("k", produce) == 1
    clock["now"] += 6.0  # past the 5s TTL
    assert cache.get_or_set("k", produce) == 2
    assert calls["n"] == 2


def test_separate_keys_are_independent(monkeypatch) -> None:
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: 0.0)
    cache = TTLCache(ttl_seconds=30.0)

    assert cache.get_or_set("a", lambda: "A") == "A"
    assert cache.get_or_set("b", lambda: "B") == "B"
    # Cached independently.
    assert cache.get_or_set("a", lambda: "changed") == "A"
    assert cache.get_or_set("b", lambda: "changed") == "B"


def test_invalidate_single_key(monkeypatch) -> None:
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: 0.0)
    cache = TTLCache(ttl_seconds=30.0)

    cache.get_or_set("a", lambda: "A")
    cache.get_or_set("b", lambda: "B")
    cache.invalidate("a")

    assert cache.get_or_set("a", lambda: "A2") == "A2"  # recomputed
    assert cache.get_or_set("b", lambda: "B2") == "B"   # still cached


def test_invalidate_all(monkeypatch) -> None:
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: 0.0)
    cache = TTLCache(ttl_seconds=30.0)

    cache.get_or_set("a", lambda: "A")
    cache.get_or_set("b", lambda: "B")
    cache.invalidate()

    assert cache.get_or_set("a", lambda: "A2") == "A2"
    assert cache.get_or_set("b", lambda: "B2") == "B2"
