-- Issue #49: enforce one vendor per owner_user_id.
--
-- The root cause of duplicate seeded vendors (migrations applied by both the
-- initdb path and run_migrations) is fixed by removing the initdb COPY. This
-- migration is the defensive complement: it collapses any pre-existing
-- duplicate vendor rows that share an owner_user_id, then adds a UNIQUE
-- constraint so a duplicate can never be inserted again.
--
-- Duplicate definition: two vendor rows with the same non-NULL owner_user_id.
-- NULL owner_user_id (pending applications without an assigned manager) are
-- left untouched — Postgres treats NULLs as distinct under UNIQUE, which is the
-- desired semantics.

DO $$
DECLARE
  dup RECORD;
BEGIN
  FOR dup IN
    SELECT owner_user_id, MIN(id) AS keeper, array_agg(id) AS all_ids
    FROM vendors
    WHERE owner_user_id IS NOT NULL
    GROUP BY owner_user_id
    HAVING count(*) > 1
  LOOP
    -- Re-point children of the duplicate rows onto the keeper (preserve data
    -- rather than relying on ON DELETE CASCADE, which would drop it).

    -- Non-cascade FKs (would otherwise block the DELETE below).
    UPDATE vendor_applications SET vendor_id = dup.keeper
      WHERE vendor_id = ANY(dup.all_ids) AND vendor_id <> dup.keeper;
    UPDATE orders SET vendor_id = dup.keeper
      WHERE vendor_id = ANY(dup.all_ids) AND vendor_id <> dup.keeper;

    -- Cascade FKs (re-point to keep the rows).
    UPDATE menu_items SET vendor_id = dup.keeper
      WHERE vendor_id = ANY(dup.all_ids) AND vendor_id <> dup.keeper;
    UPDATE meal_selections SET vendor_id = dup.keeper
      WHERE vendor_id = ANY(dup.all_ids) AND vendor_id <> dup.keeper;

    -- menu_categories has UNIQUE (vendor_id, name): move only names the keeper
    -- does not already have; colliding categories are dropped with their row.
    UPDATE menu_categories mc SET vendor_id = dup.keeper
      WHERE mc.vendor_id = ANY(dup.all_ids) AND mc.vendor_id <> dup.keeper
        AND NOT EXISTS (
          SELECT 1 FROM menu_categories k
          WHERE k.vendor_id = dup.keeper AND k.name = mc.name
        );

    -- vendor_facilities has PK (vendor_id, facility_id): copy missing links to
    -- the keeper, then the duplicates are removed by the cascade on DELETE.
    INSERT INTO vendor_facilities (vendor_id, facility_id)
      SELECT dup.keeper, facility_id FROM vendor_facilities
      WHERE vendor_id = ANY(dup.all_ids) AND vendor_id <> dup.keeper
      ON CONFLICT DO NOTHING;

    DELETE FROM vendors WHERE id = ANY(dup.all_ids) AND id <> dup.keeper;
  END LOOP;
END $$;

ALTER TABLE vendors
  ADD CONSTRAINT vendors_owner_user_id_key UNIQUE (owner_user_id);
