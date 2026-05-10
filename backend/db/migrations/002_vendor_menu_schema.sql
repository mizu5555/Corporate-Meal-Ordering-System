ALTER TABLE vendors
  ADD COLUMN IF NOT EXISTS address TEXT,
  ADD COLUMN IF NOT EXISTS business_hours TEXT,
  ADD COLUMN IF NOT EXISTS contact_phone TEXT,
  ADD COLUMN IF NOT EXISTS owner_user_id BIGINT REFERENCES users(id);

CREATE TABLE IF NOT EXISTS facilities (
  id BIGSERIAL PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_facilities (
  vendor_id BIGINT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  facility_id BIGINT NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
  PRIMARY KEY (vendor_id, facility_id)
);

CREATE INDEX IF NOT EXISTS idx_vendor_facilities_facility_id
  ON vendor_facilities (facility_id);

CREATE TABLE IF NOT EXISTS menu_categories (
  id BIGSERIAL PRIMARY KEY,
  vendor_id BIGINT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (vendor_id, name)
);

CREATE INDEX IF NOT EXISTS idx_menu_categories_vendor_sort
  ON menu_categories (vendor_id, sort_order);

CREATE TABLE IF NOT EXISTS menu_items (
  id BIGSERIAL PRIMARY KEY,
  vendor_id BIGINT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  category_id BIGINT REFERENCES menu_categories(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  description TEXT,
  price_cents INT NOT NULL CHECK (price_cents >= 0),
  available BOOLEAN NOT NULL DEFAULT TRUE,
  daily_quota INT CHECK (daily_quota IS NULL OR daily_quota >= 0),
  photo_path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_menu_items_vendor_category
  ON menu_items (vendor_id, category_id);

CREATE INDEX IF NOT EXISTS idx_menu_items_vendor_available
  ON menu_items (vendor_id)
  WHERE available;
