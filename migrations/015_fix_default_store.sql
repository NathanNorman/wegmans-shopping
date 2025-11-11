-- Migration 015: Fix default store to Raleigh, NC
-- Store 86 is Amherst, NY (incorrect)
-- Store 108 is Raleigh, NC (correct)
-- Date: November 11, 2025

-- Update all users currently on store 86 to store 108 (Raleigh, NC)
UPDATE users SET store_number = 108 WHERE store_number = 86;

-- Update all data associated with store 86 to store 108
UPDATE shopping_carts SET store_number = 108 WHERE store_number = 86;
UPDATE frequent_items SET store_number = 108 WHERE store_number = 86;
UPDATE saved_lists SET store_number = 108 WHERE store_number = 86;
UPDATE recipes SET store_number = 108 WHERE store_number = 86;
UPDATE search_cache SET store_number = 108 WHERE store_number = 86;

-- Change default for future users
ALTER TABLE users ALTER COLUMN store_number SET DEFAULT 108;
ALTER TABLE shopping_carts ALTER COLUMN store_number SET DEFAULT 108;
ALTER TABLE frequent_items ALTER COLUMN store_number SET DEFAULT 108;
ALTER TABLE saved_lists ALTER COLUMN store_number SET DEFAULT 108;
ALTER TABLE recipes ALTER COLUMN store_number SET DEFAULT 108;
ALTER TABLE search_cache ALTER COLUMN store_number SET DEFAULT 108;

-- Migration complete!
-- All existing store 86 data moved to store 108 (Raleigh, NC)
-- Future data will default to store 108
