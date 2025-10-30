-- Migration 010: Clean up unused database columns
-- Removes columns from Supabase Auth schema that shouldn't be in custom users table
-- Also removes other unused/deprecated columns

-- === USERS TABLE CLEANUP ===
-- This table got polluted with Supabase auth.users columns during migrations
-- We only need: id, email, is_anonymous, created_at, migrated_at, last_login

-- Drop Supabase Auth columns (these belong in auth.users, not public.users)
ALTER TABLE users DROP COLUMN IF EXISTS instance_id;
ALTER TABLE users DROP COLUMN IF EXISTS aud;
ALTER TABLE users DROP COLUMN IF EXISTS role;
ALTER TABLE users DROP COLUMN IF EXISTS encrypted_password;
ALTER TABLE users DROP COLUMN IF EXISTS email_confirmed_at;
ALTER TABLE users DROP COLUMN IF EXISTS invited_at;
ALTER TABLE users DROP COLUMN IF EXISTS confirmation_token;
ALTER TABLE users DROP COLUMN IF EXISTS confirmation_sent_at;
ALTER TABLE users DROP COLUMN IF EXISTS recovery_token;
ALTER TABLE users DROP COLUMN IF EXISTS recovery_sent_at;
ALTER TABLE users DROP COLUMN IF EXISTS email_change_token_new;
ALTER TABLE users DROP COLUMN IF EXISTS email_change;
ALTER TABLE users DROP COLUMN IF EXISTS email_change_sent_at;
ALTER TABLE users DROP COLUMN IF EXISTS last_sign_in_at;
ALTER TABLE users DROP COLUMN IF EXISTS raw_app_meta_data;
ALTER TABLE users DROP COLUMN IF EXISTS raw_user_meta_data;
ALTER TABLE users DROP COLUMN IF EXISTS is_super_admin;
ALTER TABLE users DROP COLUMN IF EXISTS updated_at;
ALTER TABLE users DROP COLUMN IF EXISTS phone;
ALTER TABLE users DROP COLUMN IF EXISTS phone_confirmed_at;
ALTER TABLE users DROP COLUMN IF EXISTS phone_change;
ALTER TABLE users DROP COLUMN IF EXISTS phone_change_token;
ALTER TABLE users DROP COLUMN IF EXISTS phone_change_sent_at;
ALTER TABLE users DROP COLUMN IF EXISTS confirmed_at;
ALTER TABLE users DROP COLUMN IF EXISTS email_change_token_current;
ALTER TABLE users DROP COLUMN IF EXISTS email_change_confirm_status;
ALTER TABLE users DROP COLUMN IF EXISTS banned_until;
ALTER TABLE users DROP COLUMN IF EXISTS reauthentication_token;
ALTER TABLE users DROP COLUMN IF EXISTS reauthentication_sent_at;
ALTER TABLE users DROP COLUMN IF EXISTS is_sso_user;
ALTER TABLE users DROP COLUMN IF EXISTS deleted_at;

-- Drop supabase_user_id (no longer used - we use direct auth.users id now)
ALTER TABLE users DROP COLUMN IF EXISTS supabase_user_id;

-- Drop username (no longer used - replaced with email)
ALTER TABLE users DROP COLUMN IF EXISTS username;

-- Clean final schema should be:
-- users (
--   id uuid PRIMARY KEY,
--   email varchar(255),
--   is_anonymous boolean NOT NULL DEFAULT TRUE,
--   created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
--   migrated_at timestamp,
--   last_login timestamp
-- )

-- === VERIFY FINAL SCHEMA ===
DO $$
DECLARE
    column_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO column_count
    FROM information_schema.columns
    WHERE table_name = 'users';

    IF column_count > 6 THEN
        RAISE WARNING 'Users table still has % columns (expected 6)', column_count;
    ELSE
        RAISE NOTICE '✓ Users table cleaned successfully (% columns)', column_count;
    END IF;
END $$;

-- Migration complete!
-- Users table is now clean with only necessary columns
