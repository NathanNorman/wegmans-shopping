#!/usr/bin/env python3
"""
Anonymous User Cleanup Script

Removes stale anonymous users who:
- Haven't been active for 30+ days
- Have no cart items, saved lists, or recipes

Run as cron job: 0 2 * * * (daily at 2 AM)

Usage:
    python scripts/cleanup_anonymous_users.py [--days DAYS] [--dry-run] [--stats]

Options:
    --days DAYS    Age threshold in days (default: 30)
    --dry-run      Show what would be deleted without deleting
    --stats        Show anonymous user statistics
"""
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import cleanup_stale_anonymous_users, get_anonymous_user_stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def show_stats():
    """Show anonymous user statistics"""
    logger.info("📊 Anonymous User Statistics")
    logger.info("-" * 50)

    try:
        stats = get_anonymous_user_stats()

        logger.info(f"Total anonymous users: {stats['total_anonymous']}")
        logger.info(f"Active (last 7 days):  {stats['active_7d']}")
        logger.info(f"Active (last 30 days): {stats['active_30d']}")
        logger.info(f"Stale (30+ days old):  {stats['stale_30d']}")

        return stats

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return None


def cleanup(days_old: int = 30, dry_run: bool = False):
    """Run cleanup with specified parameters"""
    logger.info("🧹 Anonymous User Cleanup")
    logger.info("-" * 50)
    logger.info(f"Age threshold: {days_old} days")
    logger.info(f"Dry run: {dry_run}")
    logger.info("")

    try:
        if dry_run:
            # Show stats only
            stats = get_anonymous_user_stats()
            logger.info(f"Would delete approximately {stats['stale_30d']} stale users")
            logger.info("(Run without --dry-run to actually delete)")
            return 0
        else:
            # Actually delete
            deleted_count = cleanup_stale_anonymous_users(days_old)

            if deleted_count == 0:
                logger.info("✅ No stale anonymous users found")
            else:
                logger.info(f"✅ Deleted {deleted_count} stale anonymous users")

            return deleted_count

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return -1


def main():
    parser = argparse.ArgumentParser(
        description="Clean up stale anonymous users"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Age threshold in days (default: 30)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without deleting'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show anonymous user statistics'
    )

    args = parser.parse_args()

    # Show stats if requested
    if args.stats:
        show_stats()
        sys.exit(0)

    # Run cleanup
    result = cleanup(args.days, args.dry_run)

    if result < 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
