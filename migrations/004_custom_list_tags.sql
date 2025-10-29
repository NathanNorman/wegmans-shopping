-- Migration 004: Add custom name tagging to auto-saved lists
-- Purpose: Allow users to tag date-based lists with custom names (e.g., "Thanksgiving")
--          instead of creating duplicate lists
-- Created: October 29, 2025

-- Add custom_name column for tagging lists
ALTER TABLE saved_lists
    ADD COLUMN IF NOT EXISTS custom_name TEXT;

-- Create index for filtering by custom names
CREATE INDEX IF NOT EXISTS idx_custom_named_lists
    ON saved_lists(user_id, custom_name)
    WHERE custom_name IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN saved_lists.custom_name IS 'Optional custom tag for lists (e.g., "Thanksgiving Dinner"). When set, displays prominently alongside date.';
