-- Migration 011: Rebuild users table (fix duplicate columns issue)
--
-- Problem: users table has duplicate columns (2x id, 2x email, 2x created_at, 2x is_anonymous)
-- Solution: Create clean table, migrate data, swap tables
--
-- IMPORTANT: This migration is DESTRUCTIVE. Backup database first!
--
-- Steps:
-- 1. Create new clean table
-- 2. Copy data (handling duplicates)
-- 3. Verify data integrity
-- 4. Swap tables
-- 5. Drop old table

BEGIN;

-- Step 1: Create new clean users table
CREATE TABLE IF NOT EXISTS users_new (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    is_anonymous BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    migrated_at TIMESTAMP,
    last_login TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_new_email ON users_new(email);
CREATE INDEX IF NOT EXISTS idx_users_new_anonymous ON users_new(is_anonymous);

-- Step 2: Copy data from old table (deduplicating)
-- Use DISTINCT ON to handle duplicate columns
INSERT INTO users_new (id, email, is_anonymous, created_at, migrated_at, last_login)
SELECT DISTINCT ON (u.id)
    u.id,
    u.email,
    COALESCE(u.is_anonymous, TRUE) as is_anonymous,
    COALESCE(u.created_at, CURRENT_TIMESTAMP) as created_at,
    u.migrated_at,
    u.last_login
FROM users u
WHERE u.id IS NOT NULL
ORDER BY u.id, u.created_at NULLS LAST
ON CONFLICT (id) DO NOTHING;

-- Step 3: Verify data integrity
DO $$
DECLARE
    old_count INTEGER;
    new_count INTEGER;
    active_users_old INTEGER;
    active_users_new INTEGER;
BEGIN
    -- Count total users
    SELECT COUNT(DISTINCT id) INTO old_count FROM users WHERE id IS NOT NULL;
    SELECT COUNT(*) INTO new_count FROM users_new;

    RAISE NOTICE 'Old table: % unique users', old_count;
    RAISE NOTICE 'New table: % users', new_count;

    -- Count active users (with cart items)
    SELECT COUNT(DISTINCT user_id) INTO active_users_old
    FROM shopping_carts
    WHERE user_id IN (SELECT id FROM users WHERE id IS NOT NULL);

    SELECT COUNT(DISTINCT user_id) INTO active_users_new
    FROM shopping_carts
    WHERE user_id IN (SELECT id FROM users_new);

    RAISE NOTICE 'Active users (old): %', active_users_old;
    RAISE NOTICE 'Active users (new): %', active_users_new;

    -- Verify no active users lost
    IF active_users_new < active_users_old THEN
        RAISE EXCEPTION 'Data loss detected! Active users: % -> %', active_users_old, active_users_new;
    END IF;

    -- Verify reasonable migration
    IF new_count = 0 THEN
        RAISE EXCEPTION 'No users migrated! Check old table structure';
    END IF;

    IF new_count < (old_count * 0.9) THEN
        RAISE WARNING 'Lost more than 10%% of users (% -> %). Review manually', old_count, new_count;
    END IF;

    RAISE NOTICE '✓ Data integrity verified';
END $$;

-- Step 4: Drop old foreign keys
ALTER TABLE shopping_carts DROP CONSTRAINT IF EXISTS shopping_carts_user_id_fkey;
ALTER TABLE saved_lists DROP CONSTRAINT IF EXISTS saved_lists_user_id_fkey;
ALTER TABLE recipes DROP CONSTRAINT IF EXISTS recipes_user_id_fkey;
ALTER TABLE frequent_items DROP CONSTRAINT IF EXISTS frequent_items_user_id_fkey;

-- Step 5: Rename tables
ALTER TABLE users RENAME TO users_old_backup;
ALTER TABLE users_new RENAME TO users;

-- Step 6: Recreate foreign keys
ALTER TABLE shopping_carts
ADD CONSTRAINT shopping_carts_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE saved_lists
ADD CONSTRAINT saved_lists_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE recipes
ADD CONSTRAINT recipes_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE frequent_items
ADD CONSTRAINT frequent_items_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Step 7: Verify foreign keys work
DO $$
DECLARE
    orphaned_carts INTEGER;
    orphaned_lists INTEGER;
    orphaned_recipes INTEGER;
    orphaned_frequent INTEGER;
BEGIN
    -- Check for orphaned records
    SELECT COUNT(*) INTO orphaned_carts
    FROM shopping_carts
    WHERE user_id NOT IN (SELECT id FROM users);

    SELECT COUNT(*) INTO orphaned_lists
    FROM saved_lists
    WHERE user_id NOT IN (SELECT id FROM users);

    SELECT COUNT(*) INTO orphaned_recipes
    FROM recipes
    WHERE user_id NOT IN (SELECT id FROM users);

    SELECT COUNT(*) INTO orphaned_frequent
    FROM frequent_items
    WHERE user_id NOT IN (SELECT id FROM users);

    IF orphaned_carts > 0 OR orphaned_lists > 0 OR orphaned_recipes > 0 OR orphaned_frequent > 0 THEN
        RAISE WARNING 'Found orphaned records: carts=%, lists=%, recipes=%, frequent=%',
            orphaned_carts, orphaned_lists, orphaned_recipes, orphaned_frequent;
    ELSE
        RAISE NOTICE '✓ No orphaned records';
    END IF;
END $$;

-- Step 8: Final verification
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'users';

    RAISE NOTICE 'Final users table has % columns', col_count;

    IF col_count != 6 THEN
        RAISE WARNING 'Expected 6 columns, got %', col_count;
    ELSE
        RAISE NOTICE '✓ Users table cleaned successfully!';
    END IF;
END $$;

COMMIT;

-- Migration complete!
-- OLD TABLE (users_old_backup) is preserved for safety
-- Drop it manually after 24-48 hours of verification:
-- DROP TABLE IF EXISTS users_old_backup CASCADE;
