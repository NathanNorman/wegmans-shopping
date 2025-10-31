-- Rollback: Remove sell_by_unit column if needed
-- Date: 2025-10-31
-- Description: Removes sell_by_unit columns from all tables (use only if migration needs to be reverted)

ALTER TABLE shopping_carts DROP COLUMN IF EXISTS sell_by_unit;
ALTER TABLE saved_list_items DROP COLUMN IF EXISTS sell_by_unit;
ALTER TABLE frequent_items DROP COLUMN IF EXISTS sell_by_unit;
ALTER TABLE recipe_items DROP COLUMN IF EXISTS sell_by_unit;
