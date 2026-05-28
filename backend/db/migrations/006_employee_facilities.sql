-- Issue #65: facility-based employee/vendor visibility
-- Add employee_facilities join table so each employee can be assigned to one or more
-- facilities; vendor visibility is then filtered to the intersection of facilities.

CREATE TABLE IF NOT EXISTS employee_facilities (
  employee_id  BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  facility_id  BIGINT NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
  PRIMARY KEY (employee_id, facility_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_facilities_facility_id
  ON employee_facilities (facility_id);

-- Seed: ensure F12A facility exists (safe if already inserted by other migration)
INSERT INTO facilities (code, name)
VALUES ('F12A', 'Fab 12A')
ON CONFLICT (code) DO NOTHING;

-- Seed: assign the default vendor ("Sunny Kitchen") to F12A, and
-- the default employee account to F12A so they keep seeing each other.
-- Uses subqueries to stay ID-agnostic across environments.
DO $$
DECLARE
  v_facility_id BIGINT;
  v_vendor_id   BIGINT;
  v_employee_id BIGINT;
BEGIN
  SELECT id INTO v_facility_id FROM facilities WHERE code = 'F12A';

  -- Vendor seed (only if "Sunny Kitchen" exists)
  SELECT id INTO v_vendor_id FROM vendors WHERE name = 'Sunny Kitchen' LIMIT 1;
  IF v_vendor_id IS NOT NULL AND v_facility_id IS NOT NULL THEN
    INSERT INTO vendor_facilities (vendor_id, facility_id)
    VALUES (v_vendor_id, v_facility_id)
    ON CONFLICT DO NOTHING;
  END IF;

  -- Employee seed: first user with role "employee"
  SELECT u.id INTO v_employee_id
  FROM users u
  JOIN roles r ON r.id = u.role_id
  WHERE r.name = 'employee'
  ORDER BY u.id
  LIMIT 1;
  IF v_employee_id IS NOT NULL AND v_facility_id IS NOT NULL THEN
    INSERT INTO employee_facilities (employee_id, facility_id)
    VALUES (v_employee_id, v_facility_id)
    ON CONFLICT DO NOTHING;
  END IF;
END $$;
