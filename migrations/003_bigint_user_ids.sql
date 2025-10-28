-- Migration 003: Change user_id columns to BIGINT to support large UUID-based IDs
-- Purpose: Fix "integer out of range" error when using UUID-generated user IDs
-- Created: October 28, 2025

-- Change users table id to BIGINT
ALTER TABLE users ALTER COLUMN id TYPE BIGINT;

-- Change all foreign key references to BIGINT
ALTER TABLE shopping_carts ALTER COLUMN user_id TYPE BIGINT;
ALTER TABLE saved_lists ALTER COLUMN user_id TYPE BIGINT;

-- Update the sequence to use BIGINT range
ALTER SEQUENCE users_id_seq AS BIGINT;
