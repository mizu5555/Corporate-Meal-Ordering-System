-- Per-(item, date) overrides for availability, quota, and price.
-- NULL in any column means "inherit from the item's base value".
-- A missing row also means "inherit base" for every field.

CREATE TABLE IF NOT EXISTS menu_item_date_overrides (
    id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    meal_date DATE NOT NULL,
    available BOOLEAN,
    daily_quota INT CHECK (daily_quota IS NULL OR daily_quota >= 0),
    price_cents INT CHECK (price_cents IS NULL OR price_cents >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (item_id, meal_date)
);

CREATE INDEX IF NOT EXISTS idx_menu_item_date_overrides_item_date
    ON menu_item_date_overrides (item_id, meal_date);
