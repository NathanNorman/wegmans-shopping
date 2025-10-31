-- Migration: Add sell_by_unit column to support proper unit display
-- Date: 2025-10-31
-- Description: Store unit names (lb, oz, pkg, Each) for accurate display of weight-based items

-- Add sell_by_unit column to shopping_carts
ALTER TABLE shopping_carts
ADD COLUMN IF NOT EXISTS sell_by_unit TEXT DEFAULT 'Each';

-- Add sell_by_unit column to saved_list_items
ALTER TABLE saved_list_items
ADD COLUMN IF NOT EXISTS sell_by_unit TEXT DEFAULT 'Each';

-- Add sell_by_unit column to frequent_items
ALTER TABLE frequent_items
ADD COLUMN IF NOT EXISTS sell_by_unit TEXT DEFAULT 'Each';

-- Add sell_by_unit column to recipe_items
ALTER TABLE recipe_items
ADD COLUMN IF NOT EXISTS sell_by_unit TEXT DEFAULT 'Each';

-- Set reasonable defaults for existing weight items
-- Assume weight items without unit are sold by pound
UPDATE shopping_carts
SET sell_by_unit = 'lb'
WHERE is_sold_by_weight = TRUE AND sell_by_unit = 'Each';

UPDATE saved_list_items
SET sell_by_unit = 'lb'
WHERE is_sold_by_weight = TRUE AND sell_by_unit = 'Each';

UPDATE frequent_items
SET sell_by_unit = 'lb'
WHERE is_sold_by_weight = TRUE AND sell_by_unit = 'Each';

UPDATE recipe_items
SET sell_by_unit = 'lb'
WHERE is_sold_by_weight = TRUE AND sell_by_unit = 'Each';

-- Add comments for documentation
COMMENT ON COLUMN shopping_carts.sell_by_unit IS 'Unit name for display: lb, oz, pkg, Each, etc.';
COMMENT ON COLUMN saved_list_items.sell_by_unit IS 'Unit name for display: lb, oz, pkg, Each, etc.';
COMMENT ON COLUMN frequent_items.sell_by_unit IS 'Unit name for display: lb, oz, pkg, Each, etc.';
COMMENT ON COLUMN recipe_items.sell_by_unit IS 'Unit name for display: lb, oz, pkg, Each, etc.';
