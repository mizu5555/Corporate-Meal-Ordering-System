-- Demo dataset for staging/preview (SEED_DEMO_DATA=true).
-- Idempotent: safe to run on every startup. Uses ON CONFLICT DO NOTHING
-- and natural-key lookups throughout. The orders block is guarded by an
-- existence check so re-runs do NOT create duplicate orders.

-- ─────────────────────────────────────────────
-- 1. FACILITIES
-- ─────────────────────────────────────────────
INSERT INTO facilities (code, name)
VALUES
  ('F12A', 'Fab 12A'),
  ('F14B', 'Fab 14B'),
  ('F15A', 'Fab 15A')
ON CONFLICT (code) DO NOTHING;

-- ─────────────────────────────────────────────
-- 2. DEMO VENDOR USERS (vendor_manager role)
--    password = "password123" (same bcrypt cost as 003_auth.sql)
-- ─────────────────────────────────────────────
INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'demo.noodle@corpmeal.local',
  'Demo Noodle Manager',
  (SELECT id FROM roles WHERE name = 'vendor_manager'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'demo.greenbowl@corpmeal.local',
  'Demo Green Bowl Manager',
  (SELECT id FROM roles WHERE name = 'vendor_manager'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO NOTHING;

-- Owners for the pending / rejected demo vendors (so applications have a submitter).
INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'demo.pending@corpmeal.local',
  'Demo Pending Manager',
  (SELECT id FROM roles WHERE name = 'vendor_manager'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'demo.rejected@corpmeal.local',
  'Demo Rejected Manager',
  (SELECT id FROM roles WHERE name = 'vendor_manager'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO NOTHING;

-- ─────────────────────────────────────────────
-- 3. DEMO VENDORS (status 'approved')
-- ─────────────────────────────────────────────
INSERT INTO vendors (name, status, contact_email, owner_user_id)
SELECT
  'Demo Noodle House',
  'approved',
  'demo.noodle@corpmeal.local',
  (SELECT id FROM users WHERE email = 'demo.noodle@corpmeal.local')
WHERE NOT EXISTS (SELECT 1 FROM vendors WHERE name = 'Demo Noodle House');

INSERT INTO vendors (name, status, contact_email, owner_user_id)
SELECT
  'Demo Green Bowl',
  'approved',
  'demo.greenbowl@corpmeal.local',
  (SELECT id FROM users WHERE email = 'demo.greenbowl@corpmeal.local')
WHERE NOT EXISTS (SELECT 1 FROM vendors WHERE name = 'Demo Green Bowl');

-- Pending vendor — awaiting admin review (shows in 商家審核 待審 tab).
INSERT INTO vendors (name, status, contact_email, owner_user_id)
SELECT
  'Demo Dumpling Bar',
  'pending',
  'demo.pending@corpmeal.local',
  (SELECT id FROM users WHERE email = 'demo.pending@corpmeal.local')
WHERE NOT EXISTS (SELECT 1 FROM vendors WHERE name = 'Demo Dumpling Bar');

-- Rejected vendor — application was declined with a reason (shows in 商家審核 已駁回).
INSERT INTO vendors (name, status, contact_email, owner_user_id)
SELECT
  'Demo Fast Fry',
  'rejected',
  'demo.rejected@corpmeal.local',
  (SELECT id FROM users WHERE email = 'demo.rejected@corpmeal.local')
WHERE NOT EXISTS (SELECT 1 FROM vendors WHERE name = 'Demo Fast Fry');

-- ─────────────────────────────────────────────
-- 4. VENDOR FACILITIES
--    Sunny Kitchen → F12A (already done by migration 006, kept idempotent)
--    Demo Noodle House → F12A + F14B
--    Demo Green Bowl → F15A
-- ─────────────────────────────────────────────
DO $$
DECLARE
  v_f12a   BIGINT;
  v_f14b   BIGINT;
  v_f15a   BIGINT;
  v_sunny  BIGINT;
  v_noodle BIGINT;
  v_green  BIGINT;
BEGIN
  SELECT id INTO v_f12a   FROM facilities WHERE code = 'F12A';
  SELECT id INTO v_f14b   FROM facilities WHERE code = 'F14B';
  SELECT id INTO v_f15a   FROM facilities WHERE code = 'F15A';
  SELECT id INTO v_sunny  FROM vendors     WHERE name = 'Sunny Kitchen'     LIMIT 1;
  SELECT id INTO v_noodle FROM vendors     WHERE name = 'Demo Noodle House' LIMIT 1;
  SELECT id INTO v_green  FROM vendors     WHERE name = 'Demo Green Bowl'   LIMIT 1;

  IF v_sunny IS NOT NULL THEN
    INSERT INTO vendor_facilities VALUES (v_sunny, v_f12a) ON CONFLICT DO NOTHING;
  END IF;

  IF v_noodle IS NOT NULL THEN
    INSERT INTO vendor_facilities VALUES (v_noodle, v_f12a) ON CONFLICT DO NOTHING;
    INSERT INTO vendor_facilities VALUES (v_noodle, v_f14b) ON CONFLICT DO NOTHING;
  END IF;

  IF v_green IS NOT NULL THEN
    INSERT INTO vendor_facilities VALUES (v_green, v_f15a) ON CONFLICT DO NOTHING;
  END IF;
END $$;

-- ─────────────────────────────────────────────
-- 5. MENU CATEGORIES + ITEMS
--    Sunny Kitchen:     category "Lunch Boxes", 3 items
--    Demo Noodle House: category "Noodles",     4 items
--    Demo Green Bowl:   category "Bowls",       4 items
-- ─────────────────────────────────────────────
DO $$
DECLARE
  v_sunny_id   BIGINT;
  v_noodle_id  BIGINT;
  v_green_id   BIGINT;
  v_cat_sunny  BIGINT;
  v_cat_noodle BIGINT;
  v_cat_green  BIGINT;
BEGIN
  SELECT id INTO v_sunny_id  FROM vendors WHERE name = 'Sunny Kitchen'     LIMIT 1;
  SELECT id INTO v_noodle_id FROM vendors WHERE name = 'Demo Noodle House' LIMIT 1;
  SELECT id INTO v_green_id  FROM vendors WHERE name = 'Demo Green Bowl'   LIMIT 1;

  -- ── Sunny Kitchen ─────────────────────────
  IF v_sunny_id IS NOT NULL THEN
    INSERT INTO menu_categories (vendor_id, name, sort_order)
    VALUES (v_sunny_id, 'Lunch Boxes', 1)
    ON CONFLICT (vendor_id, name) DO NOTHING;

    SELECT id INTO v_cat_sunny
    FROM menu_categories WHERE vendor_id = v_sunny_id AND name = 'Lunch Boxes';

    -- top-seller: Chicken Rice Box (quota 50)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_sunny_id, v_cat_sunny,
           'Chicken Rice Box',
           'Grilled chicken thigh with steamed rice and seasonal vegetables',
           8500, 50, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_sunny_id AND name = 'Chicken Rice Box'
    );

    -- medium-seller: Pork Chop Box (quota 30)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_sunny_id, v_cat_sunny,
           'Pork Chop Box',
           'Crispy fried pork chop with rice and pickled vegetables',
           9000, 30, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_sunny_id AND name = 'Pork Chop Box'
    );

    -- low-seller: Veggie Box (unlimited)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_sunny_id, v_cat_sunny,
           'Veggie Box',
           'Seasonal stir-fried vegetables with tofu over steamed rice',
           7500, NULL, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_sunny_id AND name = 'Veggie Box'
    );
  END IF;

  -- ── Demo Noodle House ──────────────────────
  IF v_noodle_id IS NOT NULL THEN
    INSERT INTO menu_categories (vendor_id, name, sort_order)
    VALUES (v_noodle_id, 'Noodles', 1)
    ON CONFLICT (vendor_id, name) DO NOTHING;

    SELECT id INTO v_cat_noodle
    FROM menu_categories WHERE vendor_id = v_noodle_id AND name = 'Noodles';

    -- top-seller: Beef Noodle Soup (quota 50, cheap)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_noodle_id, v_cat_noodle,
           'Beef Noodle Soup',
           'Rich broth with hand-pulled noodles and slow-braised beef',
           9000, 50, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_noodle_id AND name = 'Beef Noodle Soup'
    );

    -- top-seller: Dan Dan Noodles (quota 50)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_noodle_id, v_cat_noodle,
           'Dan Dan Noodles',
           'Spicy Sichuan sesame noodles with minced pork',
           8500, 50, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_noodle_id AND name = 'Dan Dan Noodles'
    );

    -- medium-seller: Wonton Noodle Soup (quota 20)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_noodle_id, v_cat_noodle,
           'Wonton Noodle Soup',
           'Silky wontons in clear chicken broth with egg noodles',
           8000, 20, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_noodle_id AND name = 'Wonton Noodle Soup'
    );

    -- low-seller: Cold Sesame Noodles (unlimited)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_noodle_id, v_cat_noodle,
           'Cold Sesame Noodles',
           'Chilled noodles tossed in peanut sesame sauce',
           7500, NULL, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_noodle_id AND name = 'Cold Sesame Noodles'
    );
  END IF;

  -- ── Demo Green Bowl ────────────────────────
  IF v_green_id IS NOT NULL THEN
    INSERT INTO menu_categories (vendor_id, name, sort_order)
    VALUES (v_green_id, 'Bowls', 1)
    ON CONFLICT (vendor_id, name) DO NOTHING;

    SELECT id INTO v_cat_green
    FROM menu_categories WHERE vendor_id = v_green_id AND name = 'Bowls';

    -- top-seller: Teriyaki Chicken Bowl (quota 50)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_green_id, v_cat_green,
           'Teriyaki Chicken Bowl',
           'Grilled chicken thigh glazed in house teriyaki over brown rice',
           9500, 50, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_green_id AND name = 'Teriyaki Chicken Bowl'
    );

    -- top-seller: Salmon Poke Bowl (quota 30)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_green_id, v_cat_green,
           'Salmon Poke Bowl',
           'Sushi-grade salmon, avocado, edamame on sushi rice',
           13000, 30, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_green_id AND name = 'Salmon Poke Bowl'
    );

    -- medium-seller: Quinoa Veggie Bowl (unlimited)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_green_id, v_cat_green,
           'Quinoa Veggie Bowl',
           'Tri-color quinoa with roasted seasonal vegetables and tahini',
           8800, NULL, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_green_id AND name = 'Quinoa Veggie Bowl'
    );

    -- low-seller: Tofu Miso Bowl (quota 20)
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available)
    SELECT v_green_id, v_cat_green,
           'Tofu Miso Bowl',
           'Silken tofu and miso-glazed eggplant over steamed rice',
           8000, 20, TRUE
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_green_id AND name = 'Tofu Miso Bowl'
    );
  END IF;
END $$;

-- ─────────────────────────────────────────────
-- 5b. MENU ENRICHMENT (dietary tags + a sold-out example)
--     Demonstrates the dietary-tag filter and the 今日售完 (sold-out) UI.
--     UPDATEs are idempotent; the sold-out item is guarded by NOT EXISTS.
-- ─────────────────────────────────────────────
DO $$
DECLARE
  v_sunny_id BIGINT;
  v_cat_sunny BIGINT;
BEGIN
  SELECT id INTO v_sunny_id FROM vendors WHERE name = 'Sunny Kitchen' LIMIT 1;
  IF v_sunny_id IS NOT NULL THEN
    SELECT id INTO v_cat_sunny
      FROM menu_categories WHERE vendor_id = v_sunny_id AND name = 'Lunch Boxes';
    -- Sold-out example: daily_quota = 0 → today's remaining is 0 → shows 今日售完.
    INSERT INTO menu_items (vendor_id, category_id, name, description, price_cents, daily_quota, available, dietary_tags)
    SELECT v_sunny_id, v_cat_sunny,
           'Braised Beef Brisket Box',
           'Slow-braised beef brisket over rice (today''s batch is sold out)',
           11000, 0, TRUE, ARRAY['contains_beef']::TEXT[]
    WHERE NOT EXISTS (
      SELECT 1 FROM menu_items WHERE vendor_id = v_sunny_id AND name = 'Braised Beef Brisket Box'
    );
  END IF;
END $$;

-- Dietary tags on the existing demo items (idempotent UPDATEs; names are unique across demo vendors).
UPDATE menu_items SET dietary_tags = ARRAY['contains_pork']::TEXT[]
  WHERE name IN ('Pork Chop Box', 'Dan Dan Noodles', 'Wonton Noodle Soup');
UPDATE menu_items SET dietary_tags = ARRAY['contains_beef']::TEXT[]
  WHERE name = 'Beef Noodle Soup';
UPDATE menu_items SET dietary_tags = ARRAY['vegetarian']::TEXT[]
  WHERE name IN ('Veggie Box', 'Quinoa Veggie Bowl', 'Tofu Miso Bowl');
UPDATE menu_items SET dietary_tags = ARRAY['ovo_lacto_vegetarian']::TEXT[]
  WHERE name = 'Cold Sesame Noodles';

-- ─────────────────────────────────────────────
-- 6. DEMO EMPLOYEE USERS
--    password = "password123"
-- ─────────────────────────────────────────────
INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'demo.employee1@corpmeal.local',
  'Alice Wang',
  (SELECT id FROM roles WHERE name = 'employee'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'demo.employee2@corpmeal.local',
  'Bob Chen',
  (SELECT id FROM roles WHERE name = 'employee'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'demo.employee3@corpmeal.local',
  'Carol Liu',
  (SELECT id FROM roles WHERE name = 'employee'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO NOTHING;

-- Badge backfill for demo employees (idempotent). Mixed CJK/Western names show
-- vendor-facing name masking works for both.
UPDATE users SET display_name = '王小明', badge_code = 'EMP-0002'
WHERE email = 'demo.employee1@corpmeal.local';
UPDATE users SET display_name = 'John Smith', badge_code = 'EMP-0003'
WHERE email = 'demo.employee2@corpmeal.local';
UPDATE users SET display_name = '李大華', badge_code = 'EMP-0004'
WHERE email = 'demo.employee3@corpmeal.local';

-- Pending employees — registered but not yet enabled by admin (is_active = FALSE).
-- They appear in 使用者審核 待審核 tab for the admin to enable in the demo.
INSERT INTO users (email, display_name, role_id, password_hash, is_active, badge_code)
VALUES (
  'demo.pending.emp1@corpmeal.local',
  '待審 林小美',
  (SELECT id FROM roles WHERE name = 'employee'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG',
  FALSE,
  'EMP-0005'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO users (email, display_name, role_id, password_hash, is_active, badge_code)
VALUES (
  'demo.pending.emp2@corpmeal.local',
  'Pending Dave Lin',
  (SELECT id FROM roles WHERE name = 'employee'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG',
  FALSE,
  'EMP-0006'
)
ON CONFLICT (email) DO NOTHING;

-- ─────────────────────────────────────────────
-- 7. EMPLOYEE FACILITIES
--    employee1 → F12A
--    employee2 → F12A + F14B
--    employee3 → F15A
-- ─────────────────────────────────────────────
DO $$
DECLARE
  v_f12a  BIGINT;
  v_f14b  BIGINT;
  v_f15a  BIGINT;
  v_emp1  BIGINT;
  v_emp2  BIGINT;
  v_emp3  BIGINT;
BEGIN
  SELECT id INTO v_f12a FROM facilities WHERE code = 'F12A';
  SELECT id INTO v_f14b FROM facilities WHERE code = 'F14B';
  SELECT id INTO v_f15a FROM facilities WHERE code = 'F15A';
  SELECT id INTO v_emp1 FROM users WHERE email = 'demo.employee1@corpmeal.local';
  SELECT id INTO v_emp2 FROM users WHERE email = 'demo.employee2@corpmeal.local';
  SELECT id INTO v_emp3 FROM users WHERE email = 'demo.employee3@corpmeal.local';

  IF v_emp1 IS NOT NULL THEN
    INSERT INTO employee_facilities VALUES (v_emp1, v_f12a) ON CONFLICT DO NOTHING;
  END IF;
  IF v_emp2 IS NOT NULL THEN
    INSERT INTO employee_facilities VALUES (v_emp2, v_f12a) ON CONFLICT DO NOTHING;
    INSERT INTO employee_facilities VALUES (v_emp2, v_f14b) ON CONFLICT DO NOTHING;
  END IF;
  IF v_emp3 IS NOT NULL THEN
    INSERT INTO employee_facilities VALUES (v_emp3, v_f15a) ON CONFLICT DO NOTHING;
  END IF;
END $$;

-- ─────────────────────────────────────────────
-- 8. ORDERS + ORDER ITEMS
--    Guarded so re-runs do not create duplicates.
--    ~20 orders spread over last 45 days (current + previous month data).
--    Status mix: mostly delivered, a few pending, a couple cancelled.
--    Item popularity: Beef Noodle Soup + Teriyaki Chicken Bowl are top sellers.
--    All orders satisfy: facility_id ∈ (employee_facilities ∩ vendor_facilities).
--      Sunny Kitchen (F12A):      emp1@F12A, emp2@F12A
--      Demo Noodle House (F12A,F14B): emp1@F12A, emp2@F12A, emp2@F14B
--      Demo Green Bowl (F15A):    emp3@F15A only
-- ─────────────────────────────────────────────
DO $$
DECLARE
  v_emp1       BIGINT;
  v_emp2       BIGINT;
  v_emp3       BIGINT;
  v_sunny      BIGINT;
  v_noodle     BIGINT;
  v_green      BIGINT;
  v_f12a       BIGINT;
  v_f14b       BIGINT;
  v_f15a       BIGINT;

  -- menu item ids (Sunny Kitchen)
  v_chicken_rice   BIGINT;
  v_pork_chop      BIGINT;
  v_veggie_box     BIGINT;
  -- menu item ids (Demo Noodle House)
  v_beef_noodle    BIGINT;
  v_dan_dan        BIGINT;
  v_wonton         BIGINT;
  v_cold_sesame    BIGINT;
  -- menu item ids (Demo Green Bowl)
  v_teriyaki       BIGINT;
  v_salmon_poke    BIGINT;
  v_quinoa         BIGINT;
  v_tofu_miso      BIGINT;

  v_order_id BIGINT;
BEGIN
  -- Guard: only insert orders if none exist for Demo Noodle House yet
  IF EXISTS (
    SELECT 1 FROM orders o
    JOIN vendors v ON v.id = o.vendor_id
    WHERE v.name = 'Demo Noodle House'
  ) THEN
    RETURN;
  END IF;

  -- Resolve IDs
  SELECT id INTO v_emp1   FROM users WHERE email = 'demo.employee1@corpmeal.local';
  SELECT id INTO v_emp2   FROM users WHERE email = 'demo.employee2@corpmeal.local';
  SELECT id INTO v_emp3   FROM users WHERE email = 'demo.employee3@corpmeal.local';
  SELECT id INTO v_sunny  FROM vendors WHERE name = 'Sunny Kitchen'     LIMIT 1;
  SELECT id INTO v_noodle FROM vendors WHERE name = 'Demo Noodle House' LIMIT 1;
  SELECT id INTO v_green  FROM vendors WHERE name = 'Demo Green Bowl'   LIMIT 1;
  SELECT id INTO v_f12a   FROM facilities WHERE code = 'F12A';
  SELECT id INTO v_f14b   FROM facilities WHERE code = 'F14B';
  SELECT id INTO v_f15a   FROM facilities WHERE code = 'F15A';

  SELECT id INTO v_chicken_rice FROM menu_items WHERE vendor_id = v_sunny  AND name = 'Chicken Rice Box';
  SELECT id INTO v_pork_chop    FROM menu_items WHERE vendor_id = v_sunny  AND name = 'Pork Chop Box';
  SELECT id INTO v_veggie_box   FROM menu_items WHERE vendor_id = v_sunny  AND name = 'Veggie Box';
  SELECT id INTO v_beef_noodle  FROM menu_items WHERE vendor_id = v_noodle AND name = 'Beef Noodle Soup';
  SELECT id INTO v_dan_dan      FROM menu_items WHERE vendor_id = v_noodle AND name = 'Dan Dan Noodles';
  SELECT id INTO v_wonton       FROM menu_items WHERE vendor_id = v_noodle AND name = 'Wonton Noodle Soup';
  SELECT id INTO v_cold_sesame  FROM menu_items WHERE vendor_id = v_noodle AND name = 'Cold Sesame Noodles';
  SELECT id INTO v_teriyaki     FROM menu_items WHERE vendor_id = v_green  AND name = 'Teriyaki Chicken Bowl';
  SELECT id INTO v_salmon_poke  FROM menu_items WHERE vendor_id = v_green  AND name = 'Salmon Poke Bowl';
  SELECT id INTO v_quinoa       FROM menu_items WHERE vendor_id = v_green  AND name = 'Quinoa Veggie Bowl';
  SELECT id INTO v_tofu_miso    FROM menu_items WHERE vendor_id = v_green  AND name = 'Tofu Miso Bowl';

  -- ── ORDER 1: employee1 @ Demo Noodle House, 43 days ago, delivered, 2x Beef Noodle Soup ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp1, v_noodle, v_f12a, 'delivered', 18000,
          (NOW() - INTERVAL '43 days')::DATE,
          NOW() - INTERVAL '43 days', NOW() - INTERVAL '43 days',
          NOW() - INTERVAL '43 days', v_emp1)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_beef_noodle, 'Beef Noodle Soup', 2, 9000, 18000);

  -- ── ORDER 2: employee1 @ Demo Noodle House, 40 days ago, delivered, 1x Beef + 1x Dan Dan ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp1, v_noodle, v_f12a, 'delivered', 17500,
          (NOW() - INTERVAL '40 days')::DATE,
          NOW() - INTERVAL '40 days', NOW() - INTERVAL '40 days',
          NOW() - INTERVAL '40 days', v_emp1)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_beef_noodle, 'Beef Noodle Soup', 1, 9000, 9000),
         (v_order_id, v_dan_dan,     'Dan Dan Noodles',  1, 8500, 8500);

  -- ── ORDER 3: employee2 @ Demo Noodle House, 38 days ago, delivered, 1x Wonton ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp2, v_noodle, v_f12a, 'delivered', 8000,
          (NOW() - INTERVAL '38 days')::DATE,
          NOW() - INTERVAL '38 days', NOW() - INTERVAL '38 days',
          NOW() - INTERVAL '38 days', v_emp2)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_wonton, 'Wonton Noodle Soup', 1, 8000, 8000);

  -- ── ORDER 4: employee1 @ Sunny Kitchen, 35 days ago, delivered, 2x Chicken Rice Box ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp1, v_sunny, v_f12a, 'delivered', 17000,
          (NOW() - INTERVAL '35 days')::DATE,
          NOW() - INTERVAL '35 days', NOW() - INTERVAL '35 days',
          NOW() - INTERVAL '35 days', v_emp1)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_chicken_rice, 'Chicken Rice Box', 2, 8500, 17000);

  -- ── ORDER 5: employee3 @ Demo Green Bowl, 33 days ago, delivered, 1x Salmon Poke ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp3, v_green, v_f15a, 'delivered', 13000,
          (NOW() - INTERVAL '33 days')::DATE,
          NOW() - INTERVAL '33 days', NOW() - INTERVAL '33 days',
          NOW() - INTERVAL '33 days', v_emp3)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_salmon_poke, 'Salmon Poke Bowl', 1, 13000, 13000);

  -- ── ORDER 6: employee2 @ Demo Noodle House, 30 days ago, cancelled ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, cancelled_at)
  VALUES (v_emp2, v_noodle, v_f14b, 'cancelled', 9000,
          (NOW() - INTERVAL '30 days')::DATE,
          NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days',
          NOW() - INTERVAL '30 days')
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_beef_noodle, 'Beef Noodle Soup', 1, 9000, 9000);

  -- ── ORDER 7: employee1 @ Demo Noodle House, 28 days ago, delivered, 2x Beef ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp1, v_noodle, v_f12a, 'delivered', 18000,
          (NOW() - INTERVAL '28 days')::DATE,
          NOW() - INTERVAL '28 days', NOW() - INTERVAL '28 days',
          NOW() - INTERVAL '28 days', v_emp1)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_beef_noodle, 'Beef Noodle Soup', 2, 9000, 18000);

  -- ── ORDER 8: employee3 @ Demo Green Bowl, 25 days ago, delivered, 1x Teriyaki + 1x Quinoa ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp3, v_green, v_f15a, 'delivered', 18300,
          (NOW() - INTERVAL '25 days')::DATE,
          NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days',
          NOW() - INTERVAL '25 days', v_emp3)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_teriyaki, 'Teriyaki Chicken Bowl', 1, 9500, 9500),
         (v_order_id, v_quinoa,   'Quinoa Veggie Bowl',    1, 8800, 8800);

  -- ── ORDER 9: employee2 @ Demo Noodle House, 22 days ago, delivered, 1x Dan Dan ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp2, v_noodle, v_f14b, 'delivered', 8500,
          (NOW() - INTERVAL '22 days')::DATE,
          NOW() - INTERVAL '22 days', NOW() - INTERVAL '22 days',
          NOW() - INTERVAL '22 days', v_emp2)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_dan_dan, 'Dan Dan Noodles', 1, 8500, 8500);

  -- ── ORDER 10: employee2 @ Sunny Kitchen, 20 days ago, delivered, 1x Pork Chop Box + 1x Chicken Rice Box ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp2, v_sunny, v_f12a, 'delivered', 17500,
          (NOW() - INTERVAL '20 days')::DATE,
          NOW() - INTERVAL '20 days', NOW() - INTERVAL '20 days',
          NOW() - INTERVAL '20 days', v_emp2)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_pork_chop,    'Pork Chop Box',    1, 9000, 9000),
         (v_order_id, v_chicken_rice, 'Chicken Rice Box', 1, 8500, 8500);

  -- ── ORDER 11: employee3 @ Demo Green Bowl, 18 days ago, delivered, 1x Teriyaki + 1x Tofu Miso ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp3, v_green, v_f15a, 'delivered', 17500,
          (NOW() - INTERVAL '18 days')::DATE,
          NOW() - INTERVAL '18 days', NOW() - INTERVAL '18 days',
          NOW() - INTERVAL '18 days', v_emp3)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_teriyaki,  'Teriyaki Chicken Bowl', 1, 9500, 9500),
         (v_order_id, v_tofu_miso, 'Tofu Miso Bowl',        1, 8000, 8000);

  -- ── ORDER 12: employee1 @ Sunny Kitchen, 15 days ago, delivered, 1x Pork Chop Box ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp1, v_sunny, v_f12a, 'delivered', 9000,
          (NOW() - INTERVAL '15 days')::DATE,
          NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days',
          NOW() - INTERVAL '15 days', v_emp1)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_pork_chop, 'Pork Chop Box', 1, 9000, 9000);

  -- ── ORDER 13: employee1 @ Demo Noodle House, 12 days ago, cancelled ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, cancelled_at)
  VALUES (v_emp1, v_noodle, v_f12a, 'cancelled', 8500,
          (NOW() - INTERVAL '12 days')::DATE,
          NOW() - INTERVAL '12 days', NOW() - INTERVAL '12 days',
          NOW() - INTERVAL '12 days')
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_dan_dan, 'Dan Dan Noodles', 1, 8500, 8500);

  -- ── ORDER 14: employee3 @ Demo Green Bowl, 10 days ago, delivered, 1x Tofu Miso ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp3, v_green, v_f15a, 'delivered', 8000,
          (NOW() - INTERVAL '10 days')::DATE,
          NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days',
          NOW() - INTERVAL '10 days', v_emp3)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_tofu_miso, 'Tofu Miso Bowl', 1, 8000, 8000);

  -- ── ORDER 15: employee2 @ Demo Noodle House, 8 days ago, delivered, 1x Beef + 1x Cold Sesame ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp2, v_noodle, v_f14b, 'delivered', 16500,
          (NOW() - INTERVAL '8 days')::DATE,
          NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days',
          NOW() - INTERVAL '8 days', v_emp2)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_beef_noodle,  'Beef Noodle Soup',  1, 9000, 9000),
         (v_order_id, v_cold_sesame, 'Cold Sesame Noodles', 1, 7500, 7500);

  -- ── ORDER 16: employee2 @ Sunny Kitchen, 6 days ago, delivered, 1x Chicken Rice Box + 1x Veggie Box ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp2, v_sunny, v_f12a, 'delivered', 16000,
          (NOW() - INTERVAL '6 days')::DATE,
          NOW() - INTERVAL '6 days', NOW() - INTERVAL '6 days',
          NOW() - INTERVAL '6 days', v_emp2)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_chicken_rice, 'Chicken Rice Box', 1, 8500, 8500),
         (v_order_id, v_veggie_box,   'Veggie Box',       1, 7500, 7500);

  -- ── ORDER 17: employee3 @ Demo Green Bowl, 5 days ago, delivered, 2x Teriyaki ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp3, v_green, v_f15a, 'delivered', 19000,
          (NOW() - INTERVAL '5 days')::DATE,
          NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days',
          NOW() - INTERVAL '5 days', v_emp3)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_teriyaki, 'Teriyaki Chicken Bowl', 2, 9500, 19000);

  -- ── ORDER 18: employee2 @ Demo Noodle House, 3 days ago, delivered, 1x Beef Noodle + 1x Wonton ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at, pickup_confirmed_at, pickup_confirmed_by_user_id)
  VALUES (v_emp2, v_noodle, v_f14b, 'delivered', 17000,
          (NOW() - INTERVAL '3 days')::DATE,
          NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days',
          NOW() - INTERVAL '3 days', v_emp2)
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_beef_noodle, 'Beef Noodle Soup',   1, 9000, 9000),
         (v_order_id, v_wonton,      'Wonton Noodle Soup', 1, 8000, 8000);

  -- ── ORDER 19: employee1 @ Demo Noodle House, 2 days ago, pending, 1x Beef ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at)
  VALUES (v_emp1, v_noodle, v_f12a, 'pending', 9000,
          (NOW() - INTERVAL '2 days')::DATE,
          NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days')
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_beef_noodle, 'Beef Noodle Soup', 1, 9000, 9000);

  -- ── ORDER 20: employee3 @ Demo Green Bowl, 1 day ago, pending, 1x Teriyaki ──
  INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date,
                      created_at, updated_at)
  VALUES (v_emp3, v_green, v_f15a, 'pending', 9500,
          (NOW() - INTERVAL '1 day')::DATE,
          NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day')
  RETURNING id INTO v_order_id;
  INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price_cents, total_price_cents)
  VALUES (v_order_id, v_teriyaki, 'Teriyaki Chicken Bowl', 1, 9500, 9500);

END $$;

-- ─────────────────────────────────────────────
-- 9. READY ORDERS FOR BADGE QUICK PICKUP
--    One 'ready' order per demo employee so the by-badge pickup lookup is
--    demonstrable. employee1 & employee2 at Demo Noodle House; employee3 at
--    Demo Green Bowl (proves cross-store isolation in a badge lookup).
--    facility_id chosen from employee_facilities ∩ vendor_facilities:
--      emp1 @ Demo Noodle House → F12A
--      emp2 @ Demo Noodle House → F12A
--      emp3 @ Demo Green Bowl   → F15A
--    Distinct pickup_code suffixes keep them safe under the partial UNIQUE
--    index on orders.pickup_code. Idempotent via ON CONFLICT DO NOTHING.
-- ─────────────────────────────────────────────
INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date, pickup_code)
SELECT u.id, v.id, f.id, 'ready', 1200, CURRENT_DATE, to_char(CURRENT_DATE, 'MMDD') || '-E002'
FROM users u, vendors v, facilities f
WHERE u.email = 'demo.employee1@corpmeal.local' AND v.name = 'Demo Noodle House' AND f.code = 'F12A'
ON CONFLICT DO NOTHING;

INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date, pickup_code)
SELECT u.id, v.id, f.id, 'ready', 900, CURRENT_DATE, to_char(CURRENT_DATE, 'MMDD') || '-E003'
FROM users u, vendors v, facilities f
WHERE u.email = 'demo.employee2@corpmeal.local' AND v.name = 'Demo Noodle House' AND f.code = 'F12A'
ON CONFLICT DO NOTHING;

INSERT INTO orders (employee_id, vendor_id, facility_id, status, total_price_cents, meal_date, pickup_code)
SELECT u.id, v.id, f.id, 'ready', 1500, CURRENT_DATE, to_char(CURRENT_DATE, 'MMDD') || '-E004'
FROM users u, vendors v, facilities f
WHERE u.email = 'demo.employee3@corpmeal.local' AND v.name = 'Demo Green Bowl' AND f.code = 'F15A'
ON CONFLICT DO NOTHING;

-- ─────────────────────────────────────────────
-- 10. VENDOR APPLICATIONS (mirror the real apply→review flow)
--   Approved: the 3 live vendors, reviewed by admin.
--   Pending:  Demo Dumpling Bar, awaiting review.
--   Rejected: Demo Fast Fry, declined with a reason.
-- Idempotent: one application per vendor (guarded on vendor_id).
-- ─────────────────────────────────────────────
INSERT INTO vendor_applications
  (vendor_id, submitted_by_user_id, status, reviewed_by_user_id, reviewed_at, created_at, updated_at)
SELECT v.id, v.owner_user_id, 'approved',
  (SELECT id FROM users WHERE email = 'admin@corpmeal.local'),
  NOW() - INTERVAL '20 days', NOW() - INTERVAL '22 days', NOW() - INTERVAL '20 days'
FROM vendors v
WHERE v.name IN ('Sunny Kitchen', 'Demo Noodle House', 'Demo Green Bowl')
  AND NOT EXISTS (SELECT 1 FROM vendor_applications a WHERE a.vendor_id = v.id);

INSERT INTO vendor_applications
  (vendor_id, submitted_by_user_id, status, created_at, updated_at)
SELECT v.id, v.owner_user_id, 'pending', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days'
FROM vendors v
WHERE v.name = 'Demo Dumpling Bar'
  AND NOT EXISTS (SELECT 1 FROM vendor_applications a WHERE a.vendor_id = v.id);

INSERT INTO vendor_applications
  (vendor_id, submitted_by_user_id, status, review_reason, reviewed_by_user_id, reviewed_at, created_at, updated_at)
SELECT v.id, v.owner_user_id, 'rejected',
  'Incomplete food-safety documentation; please resubmit with HACCP certificate.',
  (SELECT id FROM users WHERE email = 'admin@corpmeal.local'),
  NOW() - INTERVAL '5 days', NOW() - INTERVAL '8 days', NOW() - INTERVAL '5 days'
FROM vendors v
WHERE v.name = 'Demo Fast Fry'
  AND NOT EXISTS (SELECT 1 FROM vendor_applications a WHERE a.vendor_id = v.id);

-- Audit rows for the reviewed applications, mirroring VendorReviewService
-- (action 'vendor.review', target_type 'vendor_application'). Idempotent on (action, target_id).
INSERT INTO audit_logs (actor_user_id, actor_role, action, target_type, target_id, metadata, created_at)
SELECT
  (SELECT id FROM users WHERE email = 'admin@corpmeal.local'),
  'admin', 'vendor.review', 'vendor_application', a.id,
  jsonb_build_object('decision', a.status),
  a.reviewed_at
FROM vendor_applications a
JOIN vendors v ON v.id = a.vendor_id
WHERE v.name IN ('Sunny Kitchen', 'Demo Noodle House', 'Demo Green Bowl', 'Demo Fast Fry')
  AND a.status IN ('approved', 'rejected')
  AND NOT EXISTS (
    SELECT 1 FROM audit_logs al
    WHERE al.action = 'vendor.review' AND al.target_type = 'vendor_application' AND al.target_id = a.id
  );

-- Advance the sequence past any badge already assigned by seeds/backfill so a
-- freshly registered employee never collides with a pre-seeded EMP-NNNN
-- (demo_seed assigns EMP-0002..0004 via explicit UPDATEs, not nextval).
SELECT setval(
    'employee_badge_seq',
    GREATEST(
        (SELECT COALESCE(MAX(CAST(SUBSTRING(badge_code FROM 'EMP-([0-9]+)$') AS INTEGER)), 0)
         FROM users WHERE badge_code ~ '^EMP-[0-9]+$'),
        1
    )
);
