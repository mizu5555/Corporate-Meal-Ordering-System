"""In-memory MenuItemRepository。

Vendor-scoped 菜單項目儲存。所有 query 必須以 vendor_id scope。
DB 接好後換成 SQL 實作；介面不變。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from itertools import count
from typing import Any

from backend.schemas.vendor_self import MenuItem, MenuItemDateOverride


@dataclass
class _ItemRecord:
    id: int
    vendor_id: int
    category_id: int | None
    name: str
    description: str | None
    price_cents: int
    available: bool
    daily_quota: int | None
    dietary_tags: list[str]
    photo_path: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class _OverrideRecord:
    item_id: int
    meal_date: date
    available: bool | None
    daily_quota: int | None
    price_cents: int | None
    is_recommended: bool | None
    created_at: datetime
    updated_at: datetime


def _to_schema(rec: _ItemRecord) -> MenuItem:
    return MenuItem(
        id=rec.id,
        vendor_id=rec.vendor_id,
        category_id=rec.category_id,
        name=rec.name,
        description=rec.description,
        price_cents=rec.price_cents,
        available=rec.available,
        daily_quota=rec.daily_quota,
        is_recommended=False,
        dietary_tags=list(rec.dietary_tags),
        photo_path=rec.photo_path,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


def _to_override_schema(rec: _OverrideRecord) -> MenuItemDateOverride:
    return MenuItemDateOverride(
        item_id=rec.item_id,
        meal_date=rec.meal_date,
        available=rec.available,
        daily_quota=rec.daily_quota,
        price_cents=rec.price_cents,
        is_recommended=rec.is_recommended,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


def _apply_override(item: MenuItem, override: _OverrideRecord | None) -> MenuItem:
    """Merge a per-date override into an item, leaving None fields at their base value."""
    if override is None:
        return item
    updates: dict[str, Any] = {}
    if override.available is not None:
        updates["available"] = override.available
    if override.daily_quota is not None:
        updates["daily_quota"] = override.daily_quota
    if override.price_cents is not None:
        updates["price_cents"] = override.price_cents
    if override.is_recommended is not None:
        updates["is_recommended"] = override.is_recommended
    return item.model_copy(update=updates) if updates else item


class MenuItemRepository:
    def __init__(self) -> None:
        self._rows: dict[int, _ItemRecord] = {}
        self._overrides: dict[tuple[int, date], _OverrideRecord] = {}
        self._id_seq = count(1)

    # ── item CRUD ──────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        vendor_id: int,
        name: str,
        price_cents: int,
        description: str | None = None,
        category_id: int | None = None,
        available: bool = True,
        daily_quota: int | None = None,
        dietary_tags: list[str] | None = None,
    ) -> MenuItem:
        now = datetime.now(timezone.utc)
        rec = _ItemRecord(
            id=next(self._id_seq),
            vendor_id=vendor_id,
            category_id=category_id,
            name=name,
            description=description,
            price_cents=price_cents,
            available=available,
            daily_quota=daily_quota,
            dietary_tags=list(dietary_tags or []),
            photo_path=None,
            created_at=now,
            updated_at=now,
        )
        self._rows[rec.id] = rec
        return _to_schema(rec)

    def list(
        self,
        *,
        vendor_id: int,
        category_id: int | None = None,
        available: bool | None = None,
    ) -> list[MenuItem]:
        rows = [r for r in self._rows.values() if r.vendor_id == vendor_id]
        if category_id is not None:
            rows = [r for r in rows if r.category_id == category_id]
        if available is not None:
            rows = [r for r in rows if r.available == available]
        rows.sort(key=lambda r: r.id)
        return [_to_schema(r) for r in rows]

    def get(self, *, vendor_id: int, item_id: int) -> MenuItem | None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        return _to_schema(rec)

    def update(
        self, *, vendor_id: int, item_id: int, fields: dict[str, Any]
    ) -> MenuItem | None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        # `daily_quota=0` 是合法值 (暫停供應)，不能用 truthy 過濾；
        # `category_id=None` 也是合法 (取消分類)。所以不能 drop None — 用 sentinel：
        # 這裡 fields 只包含 client 真有送的鍵 (caller 已 exclude_unset)，故安全直接套用。
        merged = replace(rec, **fields, updated_at=datetime.now(timezone.utc))
        self._rows[item_id] = merged
        return _to_schema(merged)

    def delete(self, *, vendor_id: int, item_id: int) -> bool:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return False
        del self._rows[item_id]
        # Cascade: remove all overrides for this item
        for key in [k for k in self._overrides if k[0] == item_id]:
            del self._overrides[key]
        return True

    def set_photo_path(self, *, vendor_id: int, item_id: int, photo_path: str) -> None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return
        self._rows[item_id] = replace(rec, photo_path=photo_path, updated_at=datetime.now(timezone.utc))

    def clear_photo_path(self, *, vendor_id: int, item_id: int) -> None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return
        self._rows[item_id] = replace(rec, photo_path=None, updated_at=datetime.now(timezone.utc))

    def has_items_in_category(self, *, vendor_id: int, category_id: int) -> bool:
        return any(
            r.vendor_id == vendor_id and r.category_id == category_id
            for r in self._rows.values()
        )

    # ── per-date effective reads ────────────────────────────────────────────────

    def list_effective(
        self,
        *,
        vendor_id: int,
        meal_date: date,
        category_id: int | None = None,
        available: bool | None = None,
    ) -> list[MenuItem]:
        """Return items with any per-date overrides merged in for meal_date."""
        rows = [r for r in self._rows.values() if r.vendor_id == vendor_id]
        if category_id is not None:
            rows = [r for r in rows if r.category_id == category_id]
        rows.sort(key=lambda r: r.id)
        items = [
            _apply_override(_to_schema(r), self._overrides.get((r.id, meal_date)))
            for r in rows
        ]
        if available is not None:
            items = [i for i in items if i.available == available]
        return items

    def get_effective(
        self,
        *,
        vendor_id: int,
        item_id: int,
        meal_date: date,
    ) -> MenuItem | None:
        """Return a single item with any per-date override merged in for meal_date."""
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        return _apply_override(_to_schema(rec), self._overrides.get((item_id, meal_date)))

    # ── date override CRUD ─────────────────────────────────────────────────────

    def list_date_overrides(self, *, vendor_id: int, item_id: int) -> list[MenuItemDateOverride]:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return []
        overrides = [
            _to_override_schema(ov)
            for key, ov in self._overrides.items()
            if key[0] == item_id
        ]
        overrides.sort(key=lambda o: o.meal_date)
        return overrides

    def get_date_override(
        self, *, vendor_id: int, item_id: int, meal_date: date
    ) -> MenuItemDateOverride | None:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return None
        ov = self._overrides.get((item_id, meal_date))
        return _to_override_schema(ov) if ov else None

    def upsert_date_override(
        self,
        *,
        vendor_id: int,
        item_id: int,
        meal_date: date,
        available: bool | None,
        daily_quota: int | None,
        price_cents: int | None,
        is_recommended: bool | None = None,
    ) -> MenuItemDateOverride:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            raise KeyError(f"item {item_id} not found for vendor {vendor_id}")
        now = datetime.now(timezone.utc)
        existing = self._overrides.get((item_id, meal_date))
        ov = _OverrideRecord(
            item_id=item_id,
            meal_date=meal_date,
            available=available,
            daily_quota=daily_quota,
            price_cents=price_cents,
            is_recommended=is_recommended,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._overrides[(item_id, meal_date)] = ov
        return _to_override_schema(ov)

    def delete_date_override(
        self, *, vendor_id: int, item_id: int, meal_date: date
    ) -> bool:
        rec = self._rows.get(item_id)
        if rec is None or rec.vendor_id != vendor_id:
            return False
        key = (item_id, meal_date)
        if key not in self._overrides:
            return False
        del self._overrides[key]
        return True
