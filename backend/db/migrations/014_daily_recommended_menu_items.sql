-- Daily vendor-picked menu recommendations.
-- Vendors can mark per-date menu overrides as recommended, while admins
-- configure how many recommendations each vendor may use per day.

ALTER TABLE vendors
    ADD COLUMN IF NOT EXISTS daily_recommendation_limit INT NOT NULL DEFAULT 3
    CHECK (daily_recommendation_limit BETWEEN 1 AND 3);

ALTER TABLE menu_item_date_overrides
    ADD COLUMN IF NOT EXISTS is_recommended BOOLEAN;

CREATE INDEX IF NOT EXISTS idx_menu_item_date_overrides_recommended
    ON menu_item_date_overrides (meal_date, is_recommended);
