-- Migration 002: Add auto-save tracking to lists
-- Purpose: Enable automatic daily list saves with date-based names
-- Created: October 28, 2025

-- Add auto-save tracking columns
ALTER TABLE saved_lists
    ADD COLUMN IF NOT EXISTS is_auto_saved BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create index for finding today's auto-saved list
-- This optimizes the frequent query: "get today's auto-saved list for this user"
CREATE INDEX IF NOT EXISTS idx_auto_saved_lists
    ON saved_lists(user_id, is_auto_saved, last_updated DESC);

-- Update existing lists as manual saves (not auto-saved)
UPDATE saved_lists SET is_auto_saved = FALSE WHERE is_auto_saved IS NULL;

-- Make is_auto_saved NOT NULL after setting defaults
ALTER TABLE saved_lists
    ALTER COLUMN is_auto_saved SET NOT NULL;
