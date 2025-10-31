-- Migration 012: Add manual favorites support
-- Allows users to manually favorite items with immediate value
-- Distinguishes manual favorites from auto-learned frequent items

-- STEP 1: Add is_manual column to track manually favorited items
ALTER TABLE frequent_items ADD COLUMN IF NOT EXISTS is_manual BOOLEAN DEFAULT FALSE;

-- STEP 2: Create index for performance (manual favorites queries)
CREATE INDEX IF NOT EXISTS idx_frequent_items_manual ON frequent_items(user_id, is_manual);

-- STEP 3: Add comment for documentation
COMMENT ON COLUMN frequent_items.is_manual IS 'TRUE if user manually favorited, FALSE if auto-learned from purchase history';

-- Migration complete!
-- Manual favorites will use purchase_count=999 to ensure they sort to top
-- RLS policies already exist from migration 008, no changes needed
