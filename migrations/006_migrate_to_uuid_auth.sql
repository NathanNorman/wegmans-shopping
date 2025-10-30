-- Migration 006: Migrate to UUID-based authentication for Supabase Auth compatibility
-- This migration converts user_id from BIGINT to UUID across all tables

-- STEP 1: Add UUID columns to all tables
ALTER TABLE users ADD COLUMN user_uuid UUID DEFAULT gen_random_uuid();
ALTER TABLE shopping_carts ADD COLUMN user_uuid UUID;
ALTER TABLE saved_lists ADD COLUMN user_uuid UUID;
ALTER TABLE recipes ADD COLUMN user_uuid UUID;

-- STEP 2: Create UUID mapping for existing users
UPDATE users SET user_uuid = gen_random_uuid() WHERE user_uuid IS NULL;

-- STEP 3: Populate foreign key UUIDs by joining with users table
UPDATE shopping_carts sc
SET user_uuid = u.user_uuid
FROM users u
WHERE sc.user_id = u.id;

UPDATE saved_lists sl
SET user_uuid = u.user_uuid
FROM users u
WHERE sl.user_id = u.id;

UPDATE recipes r
SET user_uuid = u.user_uuid
FROM users u
WHERE r.user_id = u.id;

-- STEP 4: Make UUID columns NOT NULL
ALTER TABLE users ALTER COLUMN user_uuid SET NOT NULL;
ALTER TABLE shopping_carts ALTER COLUMN user_uuid SET NOT NULL;
ALTER TABLE saved_lists ALTER COLUMN user_uuid SET NOT NULL;
ALTER TABLE recipes ALTER COLUMN user_uuid SET NOT NULL;

-- STEP 5: Add unique constraint to user_uuid
ALTER TABLE users ADD CONSTRAINT users_user_uuid_unique UNIQUE (user_uuid);

-- STEP 6: Drop old foreign key constraints
ALTER TABLE shopping_carts DROP CONSTRAINT IF EXISTS shopping_carts_user_id_fkey;
ALTER TABLE saved_lists DROP CONSTRAINT IF EXISTS saved_lists_user_id_fkey;
ALTER TABLE recipes DROP CONSTRAINT IF EXISTS recipes_user_id_fkey;

-- STEP 7: Drop old BIGINT id/user_id columns
ALTER TABLE shopping_carts DROP COLUMN user_id;
ALTER TABLE saved_lists DROP COLUMN user_id;
ALTER TABLE recipes DROP COLUMN user_id;
ALTER TABLE users DROP COLUMN id;

-- STEP 8: Rename user_uuid → id (for users) and user_uuid → user_id (for other tables)
ALTER TABLE users RENAME COLUMN user_uuid TO id;
ALTER TABLE shopping_carts RENAME COLUMN user_uuid TO user_id;
ALTER TABLE saved_lists RENAME COLUMN user_uuid TO user_id;
ALTER TABLE recipes RENAME COLUMN user_uuid TO user_id;

-- STEP 9: Set users.id as PRIMARY KEY
ALTER TABLE users ADD PRIMARY KEY (id);

-- STEP 10: Recreate foreign key constraints
ALTER TABLE shopping_carts
ADD CONSTRAINT shopping_carts_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE saved_lists
ADD CONSTRAINT saved_lists_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE recipes
ADD CONSTRAINT recipes_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- STEP 11: Add authentication columns to users table
ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN is_anonymous BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN supabase_user_id UUID UNIQUE; -- Link to Supabase auth.users
ALTER TABLE users ADD COLUMN migrated_at TIMESTAMP;
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;

-- STEP 11.5: Make username nullable (no longer required for auth users)
ALTER TABLE users ALTER COLUMN username DROP NOT NULL;

-- STEP 12: Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_supabase_user_id ON users(supabase_user_id);

-- STEP 13: Update shopping_carts unique constraint
-- This prevents duplicate items per user (product_name should be unique per user)
ALTER TABLE shopping_carts DROP CONSTRAINT IF EXISTS shopping_carts_user_id_product_name_key;
ALTER TABLE shopping_carts ADD CONSTRAINT shopping_carts_user_id_product_name_key
UNIQUE (user_id, product_name);

-- Migration complete!
-- Next steps:
-- 1. Configure Supabase Auth
-- 2. Update backend to use Supabase client
-- 3. Enable RLS policies
