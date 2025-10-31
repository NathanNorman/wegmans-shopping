-- Migration 013: Add multi-store support
-- Allows users to switch between Wegmans stores
-- All product data becomes store-specific
-- Date: October 31, 2025

-- ============================================================
-- PHASE 1: Add store_number columns
-- ============================================================

-- Users: Add default store preference
ALTER TABLE users ADD COLUMN IF NOT EXISTS store_number INTEGER DEFAULT 86;
CREATE INDEX IF NOT EXISTS idx_users_store ON users(store_number);
COMMENT ON COLUMN users.store_number IS 'User primary Wegmans store number';

-- Shopping carts: Add store context
ALTER TABLE shopping_carts ADD COLUMN IF NOT EXISTS store_number INTEGER NOT NULL DEFAULT 86;
COMMENT ON COLUMN shopping_carts.store_number IS 'Which store this cart is for';

-- Frequent items: Add store context
ALTER TABLE frequent_items ADD COLUMN IF NOT EXISTS store_number INTEGER NOT NULL DEFAULT 86;
COMMENT ON COLUMN frequent_items.store_number IS 'Store-specific favorites and frequent items';

-- Saved lists: Add store context
ALTER TABLE saved_lists ADD COLUMN IF NOT EXISTS store_number INTEGER NOT NULL DEFAULT 86;
COMMENT ON COLUMN saved_lists.store_number IS 'Which store this list was created for';

-- Recipes: Add store context
ALTER TABLE recipes ADD COLUMN IF NOT EXISTS store_number INTEGER NOT NULL DEFAULT 86;
COMMENT ON COLUMN recipes.store_number IS 'Which store this recipe is for';

-- Search cache: Add store context
ALTER TABLE search_cache ADD COLUMN IF NOT EXISTS store_number INTEGER NOT NULL DEFAULT 86;
COMMENT ON COLUMN search_cache.store_number IS 'Search results are store-specific';

-- ============================================================
-- PHASE 2: Update unique constraints
-- ============================================================

-- Shopping carts: (user + product) → (user + store + product)
ALTER TABLE shopping_carts DROP CONSTRAINT IF EXISTS shopping_carts_user_id_product_name_key;
ALTER TABLE shopping_carts ADD CONSTRAINT shopping_carts_user_store_product_key
UNIQUE (user_id, store_number, product_name);

-- Frequent items: (user + product) → (user + store + product)
ALTER TABLE frequent_items DROP CONSTRAINT IF EXISTS frequent_items_user_product_key;
ALTER TABLE frequent_items ADD CONSTRAINT frequent_items_user_store_product_key
UNIQUE (user_id, store_number, product_name);

-- Search cache: (search_term) → (store + search_term)
ALTER TABLE search_cache DROP CONSTRAINT IF EXISTS search_cache_search_term_key;
ALTER TABLE search_cache ADD CONSTRAINT search_cache_store_term_key
UNIQUE (store_number, search_term);

-- ============================================================
-- PHASE 3: Add performance indexes
-- ============================================================

-- Shopping carts
CREATE INDEX IF NOT EXISTS idx_cart_user_store ON shopping_carts(user_id, store_number);

-- Frequent items
DROP INDEX IF EXISTS idx_frequent_items_user;
CREATE INDEX IF NOT EXISTS idx_frequent_items_user_store ON frequent_items(user_id, store_number);

DROP INDEX IF EXISTS idx_frequent_items_manual;
CREATE INDEX IF NOT EXISTS idx_frequent_items_user_store_manual
ON frequent_items(user_id, store_number, is_manual);

-- Saved lists
CREATE INDEX IF NOT EXISTS idx_saved_lists_user_store ON saved_lists(user_id, store_number);

-- Recipes
CREATE INDEX IF NOT EXISTS idx_recipes_user_store ON recipes(user_id, store_number);

-- Search cache
DROP INDEX IF EXISTS idx_search_term;
CREATE INDEX IF NOT EXISTS idx_search_cache_store_term ON search_cache(store_number, search_term);

-- ============================================================
-- PHASE 4: Update RLS policies (if needed)
-- ============================================================

-- Frequent items RLS may need updating if it references constraints
-- The RLS policy should continue to work as it filters by user_id
-- No changes needed as the policy doesn't reference the UNIQUE constraint

-- Migration complete!
-- All tables now support multi-store
-- Existing data defaults to store 86 (Raleigh)
