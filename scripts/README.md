# Maintenance Scripts

This directory contains maintenance and cleanup scripts for the Wegmans Shopping App.

## Anonymous User Cleanup

**Script**: `cleanup_anonymous_users.py`

Removes stale anonymous users who haven't been active for 30+ days and have no data (empty cart, no lists, no recipes).

### Usage

```bash
# Show statistics only
python scripts/cleanup_anonymous_users.py --stats

# Dry run (show what would be deleted)
python scripts/cleanup_anonymous_users.py --dry-run

# Actually run cleanup (30+ days old)
python scripts/cleanup_anonymous_users.py

# Custom age threshold (60 days)
python scripts/cleanup_anonymous_users.py --days 60
```

### Output Example

```
📊 Anonymous User Statistics
--------------------------------------------------
Total anonymous users: 1250
Active (last 7 days):  340
Active (last 30 days): 580
Stale (30+ days old):  670

🧹 Anonymous User Cleanup
--------------------------------------------------
Age threshold: 30 days
Dry run: False

✅ Deleted 487 stale anonymous users
```

### Automated Cleanup (Cron Job)

**Recommended**: Run daily at 2 AM

#### Local Development (macOS/Linux)

Add to crontab:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path to your project)
0 2 * * * cd /path/to/wegmans-shopping && python3 scripts/cleanup_anonymous_users.py >> logs/cleanup.log 2>&1
```

#### Production (Render.com)

Add as a Cron Job service:

1. Go to Render Dashboard
2. Click "New +" → "Cron Job"
3. Connect same GitHub repo
4. Configure:
   - **Name**: `wegmans-cleanup-anonymous`
   - **Schedule**: `0 2 * * *` (daily at 2 AM UTC)
   - **Command**: `python scripts/cleanup_anonymous_users.py`
   - **Environment**: Same as web service (DATABASE_URL, etc.)

#### Docker Deployment

Add to `docker-compose.yml`:

```yaml
services:
  cleanup:
    build: .
    command: >
      sh -c "
        while true; do
          python scripts/cleanup_anonymous_users.py
          sleep 86400
        done
      "
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
```

### Monitoring

**Logs**: Check cleanup logs for issues

```bash
# View recent cleanup runs
tail -f logs/cleanup.log

# Check for errors
grep "ERROR" logs/cleanup.log
```

**Metrics to Track**:
- Number of users deleted per run
- Total anonymous users over time
- Active vs stale ratio

### Safety

**Safeguards in place**:
- Only deletes users with `is_anonymous=TRUE`
- Only deletes users with no activity (empty cart, no lists, no recipes)
- Age threshold prevents deleting recent users
- Uses database CASCADE to clean up related data

**Recovery**:
- Anonymous users are ephemeral by design
- No critical data is stored in anonymous accounts
- Users should sign up before data is important to them

### Configuration

**Environment Variables**:
- `DATABASE_URL` - Required for database connection
- No additional config needed (uses same settings as main app)

**Defaults**:
- Age threshold: 30 days
- Runs: Manual (add to cron for automation)

### Troubleshooting

**Script fails with database error**:
- Check DATABASE_URL is set correctly
- Verify database credentials
- Test connection: `python -c "from src.database import get_db; get_db()"`

**No users deleted but expecting some**:
- Check if users have activity: `--stats` flag shows breakdown
- Users with ANY cart items, lists, or recipes are kept
- Only users with ALL empty data are deleted

**Want to delete users with data**:
- Don't use this script (it's designed to be safe)
- Manually write SQL queries if truly needed
- Consider adding a "last_activity" column for better tracking

---

## Future Scripts

**Planned maintenance scripts**:
- `cleanup_expired_search_cache.py` - Remove cache entries older than 7 days
- `analyze_frequent_items.py` - Rebuild frequent items from saved lists
- `backup_database.py` - Daily database backup to S3
- `optimize_images.py` - Compress and optimize product images

---

## Best Practices

1. **Always test with --dry-run first**
2. **Monitor logs after adding to cron**
3. **Set up alerts for failures**
4. **Review statistics periodically**
5. **Adjust age threshold based on usage patterns**

---

## Contributing

When adding new maintenance scripts:
1. Add to this README
2. Include `--dry-run` option
3. Add comprehensive logging
4. Test thoroughly on development database
5. Document cron job setup
