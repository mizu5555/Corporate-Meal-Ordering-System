CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  employee_id BIGINT NOT NULL REFERENCES users(id),
  vendor_id BIGINT NOT NULL REFERENCES vendors(id),
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  total_price_cents INT NOT NULL DEFAULT 0 CHECK (total_price_cents >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  cancelled_at TIMESTAMPTZ,
  CHECK (status IN ('pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_orders_employee_created
  ON orders (employee_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_orders_vendor_status_created
  ON orders (vendor_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS order_items (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  item_id BIGINT REFERENCES menu_items(id) ON DELETE SET NULL,
  item_name TEXT NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  unit_price_cents INT NOT NULL CHECK (unit_price_cents >= 0),
  total_price_cents INT NOT NULL CHECK (total_price_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order
  ON order_items (order_id);
