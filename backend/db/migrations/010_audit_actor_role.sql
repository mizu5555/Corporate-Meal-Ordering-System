-- Issue #56: record the actor's role on each audit entry.
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS actor_role VARCHAR(50);
