-- Migration 008: Add user_id to frequent_items table
-- Makes frequent items user-specific instead of global

-- STEP 1: Add user_id column
ALTER TABLE frequent_items ADD COLUMN user_id UUID;

-- STEP 2: For existing data, we can't assign to specific users, so delete it
-- (This resets everyone's frequent items, but that's better than mixed data)
DELETE FROM frequent_items;

-- STEP 3: Make user_id NOT NULL for future inserts
ALTER TABLE frequent_items ALTER COLUMN user_id SET NOT NULL;

-- STEP 4: Add foreign key constraint
ALTER TABLE frequent_items
ADD CONSTRAINT frequent_items_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- STEP 5: Update unique constraint (was product_name, now user_id + product_name)
ALTER TABLE frequent_items DROP CONSTRAINT IF EXISTS frequent_items_product_name_key;
ALTER TABLE frequent_items ADD CONSTRAINT frequent_items_user_product_key
UNIQUE (user_id, product_name);

-- STEP 6: Add index for performance
CREATE INDEX idx_frequent_items_user ON frequent_items(user_id);

-- STEP 7: Enable RLS on frequent_items
ALTER TABLE frequent_items ENABLE ROW LEVEL SECURITY;

-- STEP 8: Create RLS policy
CREATE POLICY "Users can manage own frequent items"
ON frequent_items
FOR ALL
USING (user_id = auth.uid()::uuid)
WITH CHECK (user_id = auth.uid()::uuid);

-- Migration complete!
-- Frequent items are now user-specific and protected by RLS
