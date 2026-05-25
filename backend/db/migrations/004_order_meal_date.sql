ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS meal_date DATE;

CREATE INDEX IF NOT EXISTS idx_orders_meal_date_vendor_status
  ON orders (meal_date, vendor_id, status);
