-- Migration 009: Remove custom_name column (old tagging system)
-- Simplifies to just two list types:
-- 1. Auto-saved (is_auto_saved=TRUE) - Date-based shopping history
-- 2. Custom saved (is_auto_saved=FALSE) - User-named lists

-- Drop the custom_name column
ALTER TABLE saved_lists DROP COLUMN IF EXISTS custom_name;

-- Drop the last_updated column (no longer needed without tagging)
ALTER TABLE saved_lists DROP COLUMN IF EXISTS last_updated;

-- Migration complete!
-- Now we have a simple two-category system:
-- - is_auto_saved=TRUE: Shopping History (dates)
-- - is_auto_saved=FALSE: My Custom Lists (user names)
