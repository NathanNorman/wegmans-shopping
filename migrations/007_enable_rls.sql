-- Migration 007: Enable Row Level Security (RLS) policies
-- RLS provides database-level authorization as defense-in-depth

-- STEP 1: Enable RLS on all user-specific tables
ALTER TABLE shopping_carts ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_list_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_items ENABLE ROW LEVEL SECURITY;

-- Note: frequent_items is global (no user_id), so no RLS needed
-- Note: search_cache is global, no RLS needed
-- Note: users table doesn't need RLS (managed by Supabase Auth)

-- STEP 2: Create RLS policies for shopping_carts
CREATE POLICY "Users can manage own cart"
ON shopping_carts
FOR ALL
USING (user_id = auth.uid()::uuid)
WITH CHECK (user_id = auth.uid()::uuid);

-- STEP 3: Create RLS policies for saved_lists
CREATE POLICY "Users can manage own lists"
ON saved_lists
FOR ALL
USING (user_id = auth.uid()::uuid)
WITH CHECK (user_id = auth.uid()::uuid);

-- STEP 4: Create RLS policies for saved_list_items
-- Users can only access items in their own lists
CREATE POLICY "Users can manage own list items"
ON saved_list_items
FOR ALL
USING (
    list_id IN (
        SELECT id FROM saved_lists WHERE user_id = auth.uid()::uuid
    )
);

-- STEP 5: Create RLS policies for recipes
CREATE POLICY "Users can manage own recipes"
ON recipes
FOR ALL
USING (user_id = auth.uid()::uuid)
WITH CHECK (user_id = auth.uid()::uuid);

-- STEP 6: Create RLS policies for recipe_items
-- Users can only access items in their own recipes
CREATE POLICY "Users can manage own recipe items"
ON recipe_items
FOR ALL
USING (
    recipe_id IN (
        SELECT id FROM recipes WHERE user_id = auth.uid()::uuid
    )
);

-- RLS enabled!
-- Note: RLS acts as secondary defense. Backend still filters by user_id.
-- RLS prevents:
-- - Direct database queries bypassing API
-- - SQL injection returning other users' data
-- - Admin panel mistakes
