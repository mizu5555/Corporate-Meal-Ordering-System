ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS facility_id BIGINT REFERENCES facilities(id);

CREATE INDEX IF NOT EXISTS idx_orders_facility_created
  ON orders (facility_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_vendor_facility_status_created
  ON orders (vendor_id, facility_id, status, created_at DESC);
