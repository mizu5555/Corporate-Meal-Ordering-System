-- Add password_hash column to users
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- Seed test users (password: "password123")
INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'employee@corpmeal.local',
  'Ting Lin',
  (SELECT id FROM roles WHERE name = 'employee'),
  '$2b$12$V92j2Sanc/Ie9L.w1HsXh.Go4a4oDKcq1sovHfObRIsOJ.5F/hxhG'
)
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  updated_at    = NOW();

INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'vendor@corpmeal.local',
  'Sunny Kitchen Manager',
  (SELECT id FROM roles WHERE name = 'vendor_manager'),
  '$2b$12$qHeFtKof4TfckdBqHgFSZeM2fR1F/0T98dLbDs/UDTuszkU2UB5MC'
)
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  updated_at    = NOW();

INSERT INTO users (email, display_name, role_id, password_hash)
VALUES (
  'admin@corpmeal.local',
  'Committee Admin',
  (SELECT id FROM roles WHERE name = 'admin'),
  '$2b$12$LmpKI6ohiFhb4XXzgqSbYetNpRsfj2AwoG4u89jxov0w0H/e4Zyoa'
)
ON CONFLICT (email) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  updated_at    = NOW();

-- Seed approved vendor linked to vendor@corpmeal.local
INSERT INTO vendors (name, status, contact_email, owner_user_id)
VALUES (
  'Sunny Kitchen',
  'approved',
  'vendor@corpmeal.local',
  (SELECT id FROM users WHERE email = 'vendor@corpmeal.local')
)
ON CONFLICT DO NOTHING;
