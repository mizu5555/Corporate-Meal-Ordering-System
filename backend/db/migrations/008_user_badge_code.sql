ALTER TABLE users
  ADD COLUMN IF NOT EXISTS badge_code VARCHAR(32);

UPDATE users
SET badge_code = 'EMP-' || LPAD(id::text, 4, '0')
WHERE badge_code IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_badge_code
  ON users (badge_code)
  WHERE badge_code IS NOT NULL;
