#!/usr/bin/env python3
"""
Database migration runner

Usage:
    python migrations/migrate.py status    # Show which migrations are applied
    python migrations/migrate.py up        # Apply all pending migrations
    python migrations/migrate.py up 005    # Apply specific migration
    python migrations/migrate.py list      # List all migration files

Features:
- Tracks applied migrations in schema_migrations table
- Prevents double-execution
- Shows which migrations are pending
- Applies migrations in order
"""
import os
import sys
import hashlib
import subprocess
import psycopg2
from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


def get_db_connection():
    """Get database connection from macOS Keychain"""
    whoami = subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip()
    password = subprocess.run(
        ['security', 'find-generic-password', '-a', whoami, '-s', 'supabase-wegmans-password', '-w'],
        capture_output=True, text=True
    ).stdout.strip()

    if not password:
        # Try loading from .env file as fallback
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
        conn_str = os.getenv("DATABASE_URL")
        if not conn_str:
            raise Exception("Cannot find database credentials in Keychain or .env")
        return psycopg2.connect(conn_str)

    conn_str = f"postgresql://postgres.pisakkjmyeobvcgxbmhk:{quote_plus(password)}@aws-1-us-east-2.pooler.supabase.com:5432/postgres"
    return psycopg2.connect(conn_str)


def get_migration_files():
    """Get all .sql migration files sorted by version"""
    files = []
    for file_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        # Extract version from filename (e.g., "001_init.sql" -> "001")
        filename = file_path.name
        if filename[0].isdigit():
            version = filename.split('_')[0]
            name = filename.replace('.sql', '').replace(f"{version}_", "")
            files.append({
                'version': version,
                'name': name,
                'filename': filename,
                'path': file_path
            })
    return files


def get_applied_migrations(conn):
    """Get list of applied migrations from database"""
    cursor = conn.cursor()

    # Check if migrations table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'schema_migrations'
        )
    """)

    if not cursor.fetchone()[0]:
        print("⚠️  Migration tracking table doesn't exist yet")
        return []

    cursor.execute("SELECT version, name, applied_at FROM schema_migrations ORDER BY version")
    return cursor.fetchall()


def calculate_checksum(file_path):
    """Calculate SHA-256 checksum of migration file"""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def apply_migration(conn, migration):
    """Apply a single migration"""
    print(f"📝 Applying migration {migration['version']}: {migration['name']}")

    # Read migration file
    with open(migration['path'], 'r') as f:
        sql = f.read()

    cursor = conn.cursor()

    try:
        # Execute migration
        cursor.execute(sql)

        # Record in migrations table (if it exists and this isn't migration 000)
        if migration['version'] != '000':
            checksum = calculate_checksum(migration['path'])
            cursor.execute("""
                INSERT INTO schema_migrations (version, name, applied_at, checksum)
                VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
                ON CONFLICT (version) DO NOTHING
            """, (migration['version'], migration['name'], checksum))

        conn.commit()
        print(f"✅ Migration {migration['version']} applied successfully")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration {migration['version']} failed: {e}")
        return False


def cmd_status():
    """Show migration status"""
    print("📊 Migration Status\n")

    conn = get_db_connection()
    applied = {m[0]: m for m in get_applied_migrations(conn)}
    all_migrations = get_migration_files()

    print(f"{'Version':<10} {'Name':<30} {'Status':<15} {'Applied At'}")
    print("-" * 80)

    for migration in all_migrations:
        version = migration['version']
        if version in applied:
            applied_at = applied[version][2].strftime("%Y-%m-%d %H:%M")
            print(f"{version:<10} {migration['name']:<30} {'✅ Applied':<15} {applied_at}")
        else:
            print(f"{version:<10} {migration['name']:<30} {'⏳ Pending':<15} {'N/A'}")

    conn.close()

    pending_count = len(all_migrations) - len(applied)
    print(f"\n📈 Total: {len(all_migrations)} migrations, {len(applied)} applied, {pending_count} pending")


def cmd_list():
    """List all migration files"""
    migrations = get_migration_files()

    print("📄 Available Migrations:\n")
    for m in migrations:
        print(f"  {m['version']} - {m['name']} ({m['filename']})")
    print(f"\nTotal: {len(migrations)} migrations")


def cmd_up(target_version=None):
    """Apply pending migrations"""
    conn = get_db_connection()
    applied = {m[0] for m in get_applied_migrations(conn)}
    all_migrations = get_migration_files()

    # Filter to pending migrations
    pending = [m for m in all_migrations if m['version'] not in applied]

    if target_version:
        # Apply only specific migration
        pending = [m for m in pending if m['version'] == target_version]
        if not pending:
            print(f"❌ Migration {target_version} not found or already applied")
            conn.close()
            return

    if not pending:
        print("✅ All migrations are already applied!")
        conn.close()
        return

    print(f"🚀 Applying {len(pending)} pending migration(s)...\n")

    success_count = 0
    for migration in pending:
        if apply_migration(conn, migration):
            success_count += 1
        else:
            print(f"\n❌ Stopping due to migration failure")
            break

    conn.close()
    print(f"\n✅ Applied {success_count}/{len(pending)} migrations successfully")


def main():
    if len(sys.argv) < 2:
        print("Usage: python migrations/migrate.py [status|list|up] [version]")
        print("\nCommands:")
        print("  status       Show which migrations are applied")
        print("  list         List all migration files")
        print("  up           Apply all pending migrations")
        print("  up <version> Apply specific migration (e.g., 'up 005')")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "status":
            cmd_status()
        elif command == "list":
            cmd_list()
        elif command == "up":
            target = sys.argv[2] if len(sys.argv) > 2 else None
            cmd_up(target)
        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
