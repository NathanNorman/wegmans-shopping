# Database Migrations

This directory contains SQL migration files for the Wegmans Shopping App database schema.

## Migration Tracking System

Migrations are tracked in the `schema_migrations` table to prevent double-execution and ensure consistency across environments.

## File Naming Convention

Migrations are named with a numeric prefix followed by a descriptive name:

```
000_migration_tracking.sql
001_init.sql
002_auto_save_lists.sql
003_bigint_user_ids.sql
...
```

**Important**: Always use zero-padded 3-digit version numbers (001, 002, etc.) to ensure proper sorting.

## Migration Tool

Use `migrate.py` to manage migrations:

### Check Migration Status

```bash
python migrations/migrate.py status
```

Shows which migrations have been applied and which are pending:

```
📊 Migration Status

Version    Name                           Status          Applied At
--------------------------------------------------------------------------------
000        migration_tracking             ✅ Applied       2025-01-30 15:23
001        init                           ✅ Applied       2025-01-30 15:24
002        auto_save_lists                ✅ Applied       2025-01-30 15:24
003        bigint_user_ids                ⏳ Pending       N/A
...
```

### List Available Migrations

```bash
python migrations/migrate.py list
```

### Apply Pending Migrations

```bash
# Apply all pending migrations
python migrations/migrate.py up

# Apply specific migration
python migrations/migrate.py up 003
```

## Manual Migration Execution

If you need to run migrations manually (not recommended):

```bash
python3 << 'EOF'
import subprocess, psycopg2
from urllib.parse import quote_plus

whoami = subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip()
password = subprocess.run(['security', 'find-generic-password', '-a', whoami, '-s', 'supabase-wegmans-password', '-w'], capture_output=True, text=True).stdout.strip()
conn_str = f"postgresql://postgres.pisakkjmyeobvcgxbmhk:{quote_plus(password)}@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

with open('migrations/003_bigint_user_ids.sql', 'r') as f:
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute(f.read())
    conn.commit()
    print("✅ Migration applied")
EOF
```

## Creating New Migrations

1. **Number the migration**: Use the next available number (e.g., if last is 009, use 010)
2. **Descriptive name**: Use snake_case (e.g., `010_add_user_preferences.sql`)
3. **Write idempotent SQL**: Use `IF NOT EXISTS`, `IF EXISTS`, etc. to allow re-running
4. **Test locally**: Always test on local database before production
5. **Document changes**: Add comments explaining what the migration does

### Migration Template

```sql
-- Migration XXX: Brief description of what this migration does
--
-- Changes:
-- - List specific changes
-- - Each on its own line

-- Example: Add new column
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}'::jsonb;

-- Example: Create new table
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);

-- Example: Create index
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- Migration complete!
```

## Migration Order

Migrations in this directory (in execution order):

- `000_migration_tracking.sql` - Creates the migration tracking table
- `001_init.sql` - Initial schema (users, carts, lists, cache, frequent_items)
- `002_auto_save_lists.sql` - Adds auto-save functionality
- `003_bigint_user_ids.sql` - Converts user IDs to BIGINT
- `004_custom_list_tags.sql` - Adds custom list tagging
- `005_recipes.sql` - Adds recipe feature
- `006_migrate_to_uuid_auth.sql` - Migrates to UUID-based Supabase Auth
- `007_enable_rls.sql` - Enables Row-Level Security
- `008_user_frequent_items.sql` - Makes frequent_items user-specific
- `009_remove_custom_name_tagging.sql` - Simplifies list system

## Best Practices

1. **Never modify applied migrations** - Create a new migration to make changes
2. **Keep migrations small** - One logical change per migration
3. **Test rollback** - Consider adding `_down.sql` files for reversibility
4. **Use transactions** - Most PostgreSQL DDL is transactional
5. **Backup before production** - Always backup production DB before migrations

## Troubleshooting

### Migration tracking table doesn't exist

Run migration 000 first:

```bash
python migrations/migrate.py up 000
```

### Migration shows as pending but was applied manually

Mark it as applied:

```sql
INSERT INTO schema_migrations (version, name)
VALUES ('003', 'bigint_user_ids');
```

### Need to re-run a migration

Remove from tracking table (use with caution!):

```sql
DELETE FROM schema_migrations WHERE version = '003';
```

Then apply again with `python migrations/migrate.py up 003`
