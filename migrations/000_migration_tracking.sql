-- Migration 000: Create migration tracking table
-- This table tracks which migrations have been applied to prevent double-execution

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "001", "002", etc.
    name VARCHAR(255) NOT NULL,            -- e.g., "init", "auto_save_lists", etc.
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)                   -- Optional: SHA-256 of migration file
);

CREATE INDEX idx_migrations_version ON schema_migrations(version);

-- Insert migration 000 itself as applied
INSERT INTO schema_migrations (version, name, applied_at)
VALUES ('000', 'migration_tracking', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

-- Migration tracking is now active!
-- All future migrations should register themselves in this table
