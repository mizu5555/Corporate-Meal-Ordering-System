"""Lightweight in-process TTL cache for hot, read-mostly data.

設計取捨（與水平擴展直接相關）：

- **Per-process / 每個 process 各自一份**：backend 跑多個 replica 時，每個容器
  保有自己的快取，不跨實例共享。因此一筆寫入最多在「一個 TTL 視窗」之後才會
  在所有 replica 上一致（eventual consistency）。這是刻意的——換來零外部依賴
  （不需要 Redis）並把過期窗口限制在 TTL 以內。
- **短 TTL**：只適合「讀多寫少、可容忍數十秒陳舊」的資料（例如核准商家清單）。
  **不要**拿來放需要 read-your-writes 強一致的資料。
- 之後若出現真實流量或跨主機需求，可把這個 in-process 快取換成 Redis，呼叫端
  介面（`get_or_set`）不變。
"""
from __future__ import annotations

import threading
import time
from typing import Callable, TypeVar

T = TypeVar("T")


class TTLCache:
    """以單調時鐘為基準、執行緒安全的簡易 key→value TTL 快取。

    FastAPI 的同步 route 跑在 threadpool，因此多執行緒會同時存取，需要鎖保護。
    """

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        # key -> (expires_at_monotonic, value)
        self._store: dict[str, tuple[float, object]] = {}

    def get_or_set(self, key: str, producer: Callable[[], T]) -> T:
        """命中且未過期則回傳快取值；否則呼叫 producer 取得新值並寫回。

        producer 刻意在鎖外執行，避免一個慢的 DB 查詢卡住其他 key。代價是
        快取失效瞬間可能有少量重複查詢（thundering herd），在本專案規模可接受。
        """
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is not None and entry[0] > now:
                return entry[1]  # type: ignore[return-value]

        value = producer()

        with self._lock:
            self._store[key] = (now + self._ttl, value)
        return value

    def invalidate(self, key: str | None = None) -> None:
        """清掉指定 key；不給 key 則清空整個快取。"""
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)
