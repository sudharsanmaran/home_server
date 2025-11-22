# Analytics Guide

## Quick Commands

All analytics commands must be run from inside the container:

```bash
# View overall summary
docker exec media-converter python3 /app/corruption_analytics.py summary

# View successful conversions
docker exec media-converter python3 /app/corruption_analytics.py success-summary

# View recommended publishers
docker exec media-converter python3 /app/corruption_analytics.py recommended

# View HDR/Dolby Vision analysis
docker exec media-converter python3 /app/corruption_analytics.py hdr

# View quality scores
docker exec media-converter python3 /app/corruption_analytics.py quality-scores

# View recent activity
docker exec media-converter python3 /app/corruption_analytics.py recent
```

## Current Stats

Based on your data (as of Oct 14):

**Overall:**
- Total Files: 18
- Successful: 17 (94.44%)
- Failed: 1 (5.56%)

**By HDR Type:**
- SDR: 8 files, 1 failed (12.5%)
- Dolby Vision: 9 files, 0 failed (0%)
- HDR10: 1 file, 0 failed (0%)

**Average:**
- File Size: 9.33 GB
- Duration: 127 minutes (~2 hours)

**Activity:**
- Oct 14: 1 file (failed)
- Oct 13: 1 file (succeeded - Primitive War)
- Oct 11: 16 files (all succeeded)

## Analytics Database Location

**Inside container:** `/var/log/conversions/corruption_tracker.db`
**On host:** `/data/code/home_server/services/media/media-converter/logs/corruption_tracker.db`

## View Database Directly

```bash
# Open database
sqlite3 /data/code/home_server/services/media/media-converter/logs/corruption_tracker.db

# Example queries
SELECT * FROM corruption_events ORDER BY timestamp DESC LIMIT 5;
SELECT release_group, COUNT(*) as total FROM corruption_events GROUP BY release_group;
```

## Conversion Logs

```bash
# Today's log
docker exec media-converter cat /var/log/conversions/conversion_$(date +%Y%m%d).log

# Or from host
cat /data/code/home_server/services/media/media-converter/logs/conversion_$(date +%Y%m%d).log
```

## Key Insights

Your Dolby Vision files have **0% failure rate** - they convert perfectly!
SDR files have slightly higher failure (12.5%) but still good.

After more conversions, the analytics will show:
- Which publishers to prefer
- Which release groups to avoid
- HDR reliability by group
- Quality scores
