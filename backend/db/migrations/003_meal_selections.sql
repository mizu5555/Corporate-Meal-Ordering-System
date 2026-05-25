CREATE TABLE IF NOT EXISTS meal_selections (
  id BIGSERIAL PRIMARY KEY,
  employee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  vendor_id BIGINT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  item_id BIGINT NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
  item_name TEXT NOT NULL,
  quantity INT NOT NULL CHECK (quantity >= 1),
  unit_price_cents INT NOT NULL CHECK (unit_price_cents >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meal_selections_employee
  ON meal_selections (employee_id);

CREATE INDEX IF NOT EXISTS idx_meal_selections_vendor
  ON meal_selections (vendor_id);
