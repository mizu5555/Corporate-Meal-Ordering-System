ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS pickup_code VARCHAR(24),
  ADD COLUMN IF NOT EXISTS pickup_confirmed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS pickup_confirmed_by_user_id BIGINT REFERENCES users(id);

UPDATE orders
SET pickup_code = CONCAT(
  COALESCE(TO_CHAR(meal_date, 'MMDD'), 'P'),
  '-',
  LPAD(id::TEXT, 4, '0')
)
WHERE pickup_code IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_pickup_code
  ON orders (pickup_code)
  WHERE pickup_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orders_pickup_flow
  ON orders (vendor_id, meal_date, status, pickup_code);
