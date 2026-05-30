-- backend/db/migrations/011_user_badge_code.sql
-- Employee badge (employee number) — an outward-facing identifier distinct from
-- the internal users.id (uid). Only employees are assigned one; vendor managers
-- and admins keep NULL. Format: EMP-NNNN.
ALTER TABLE users ADD COLUMN IF NOT EXISTS badge_code VARCHAR(32);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_badge_code
  ON users (badge_code) WHERE badge_code IS NOT NULL;

-- Sequence backs auto-assignment at registration time (atomic, no MAX(...)+1 race).
CREATE SEQUENCE IF NOT EXISTS employee_badge_seq START 1;
