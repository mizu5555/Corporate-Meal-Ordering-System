CREATE TABLE IF NOT EXISTS employee_facilities (
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  facility_id BIGINT NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, facility_id)
);

CREATE INDEX IF NOT EXISTS idx_employee_facilities_facility_id
  ON employee_facilities (facility_id);

INSERT INTO facilities (code, name)
VALUES
  ('F12A', 'Fab 12A'),
  ('F14B', 'Fab 14B')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name;

INSERT INTO employee_facilities (user_id, facility_id)
SELECT u.id, f.id
FROM users AS u
JOIN facilities AS f ON f.code = 'F12A'
WHERE u.email = 'employee@corpmeal.local'
ON CONFLICT DO NOTHING;

INSERT INTO vendor_facilities (vendor_id, facility_id)
SELECT v.id, f.id
FROM vendors AS v
JOIN users AS u ON u.id = v.owner_user_id
JOIN facilities AS f ON f.code = 'F12A'
WHERE u.email = 'vendor@corpmeal.local'
ON CONFLICT DO NOTHING;
