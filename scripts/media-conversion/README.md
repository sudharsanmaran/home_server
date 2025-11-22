# Media Conversion Scripts

Automated MKV to MP4 conversion with Radarr integration for self-healing downloads and comprehensive corruption tracking.

## Features

- ✅ **Integrity Verification** - Validates files before and after conversion
- ✅ **Safe Deletion** - Only deletes originals after verifying output
- ✅ **Radarr Integration** - Auto-blocklists bad releases and triggers re-downloads
- ✅ **Size Validation** - Ensures output isn't corrupted or incomplete
- ✅ **Jellyfin Integration** - Triggers library scans after conversion
- ✅ **Smart Codec Handling** - Skips slow conversions (AV1)
- ✅ **Corruption Tracking** - SQLite database with detailed corruption analytics
- ✅ **HDR/DV Detection** - Tracks HDR10, HLG, and Dolby Vision metadata
- ✅ **Publisher Analytics** - Identifies problematic release groups
- ✅ **Format Statistics** - Analyzes corruption by codec, source, and format

## Setup

### 1. Install Dependencies

```bash
# Python is required
python3 --version

# FFmpeg is required
sudo apt install ffmpeg

# Python requests library (for API calls)
pip3 install requests
```

### 2. Configure Radarr Integration

**Option A: Using config file (recommended)**

```bash
# Copy example config
cp radarr_config.json.example radarr_config.json

# Edit with your Radarr API key
nano radarr_config.json
```

Get your Radarr API key from: `Radarr → Settings → General → Security → API Key`

**Option B: Using environment variables**

```bash
# Copy example .env
cp .env.example .env

# Edit with your credentials
nano .env

# Load environment
source .env
```

### 3. Test the Script

```bash
# Test with a sample MKV file
python3 convert_mkv_to_mp4.py /path/to/movie.mkv
```

## Configuration Files

### radarr_config.json
```json
{
  "url": "http://localhost:7878",
  "api_key": "your_radarr_api_key_here"
}
```

- **url**: Radarr base URL (default: http://localhost:7878)
- **api_key**: Your Radarr API key (leave empty to disable Radarr integration)

### Environment Variables

You can also use environment variables instead of the config file:

- `RADARR_URL` - Radarr base URL
- `RADARR_API_KEY` - Radarr API key
- `JELLYFIN_URL` - Jellyfin base URL
- `JELLYFIN_API_KEY` - Jellyfin API key

## Usage

### Basic Usage

```bash
# Convert a single file
python3 convert_mkv_to_mp4.py /path/to/movie.mkv

# Test corruption tracker
python3 corruption_tracker.py /path/to/movie.mkv

# View analytics
python3 corruption_analytics.py summary
```

### Radarr Post-Processing

Add to Radarr custom script:

1. Go to: `Radarr → Settings → Connect → + → Custom Script`
2. Set:
   - **Name**: MKV to MP4 Converter
   - **On Import**: ✅ Enabled
   - **Path**: `/data/code/home_server/scripts/media-conversion/convert_mkv_to_mp4.py`
   - **Arguments**: `{movie_path}`

The script will automatically:
- Check file integrity
- Extract detailed metadata (HDR/DV info, publisher, codec)
- Convert to MP4 if possible
- Log all events to SQLite database
- Blocklist corrupted releases and trigger re-downloads

## How It Works

### Normal Workflow
```
Download → Convert → Verify → Delete MKV → Keep MP4 ✅
```

### Auto-Healing Workflow (Corrupted File)
```
Download → Detect Corruption → Keep MKV safe 🛡️
    ↓
Blocklist bad release 🚫
    ↓
Trigger auto-search 🔍
    ↓
Download better version ⬇️
    ↓
Convert successfully ✅
```

## Safety Features

### Input Validation
- Checks file integrity before conversion
- Detects corrupted or incomplete downloads
- Validates video streams are readable

### Output Validation
- Verifies output file size (90-105% of input)
- Checks output file integrity
- Ensures output is playable

### Safe Deletion
- **Never** deletes original until output is verified
- Multiple integrity checks before deletion
- Preserves original on any validation failure

### Radarr Recovery
- Automatically blocklists corrupted releases
- Triggers automatic search for better version
- Removes bad file from Radarr database
- Zero manual intervention needed

## What Gets Blocklisted

✅ **Auto-blocklisted:**
- Corrupted input files
- Files that fail conversion
- Incomplete conversions (output too small)
- Output files that fail integrity check
- Any conversion errors

❌ **NOT blocklisted:**
- AV1 files (just skipped, not bad)
- Files already as MP4
- Valid conversions

## Analytics and Reporting

### View Corruption Statistics

**Quick wrapper script:**
```bash
# Use the analyze.sh wrapper for quick access
./analyze.sh                    # Show all available commands
./analyze.sh summary            # Overall summary
./analyze.sh success            # Success statistics
./analyze.sh recommended        # Show recommended publishers
./analyze.sh quality            # Quality scores
./analyze.sh hdr-reliable       # Best HDR/DV publishers
./analyze.sh export-radarr recommended.txt  # Export for Radarr
```

**Direct Python commands:**
```bash
# Overall summary with HDR/DV breakdown
python3 corruption_analytics.py summary

# SUCCESS TRACKING (NEW!)
python3 corruption_analytics.py success-summary
python3 corruption_analytics.py recommended
python3 corruption_analytics.py quality-scores
python3 corruption_analytics.py hdr-reliable

# Show worst publishers (highest corruption rate)
python3 corruption_analytics.py worst-publishers

# Show most reliable publishers
python3 corruption_analytics.py best-publishers

# Analyze by video format (codec + HDR)
python3 corruption_analytics.py formats

# Analyze by source type (REMUX, WEB-DL, etc.)
python3 corruption_analytics.py sources

# Detailed HDR/Dolby Vision analysis
python3 corruption_analytics.py hdr

# Show corruption type breakdown
python3 corruption_analytics.py corruption-types

# Recent corrupted files
python3 corruption_analytics.py recent

# Search for specific publisher
python3 corruption_analytics.py search "PUBLISHER_NAME"

# Export all data to JSON
python3 corruption_analytics.py export data.json

# Export Radarr configuration with preferred publishers
python3 corruption_analytics.py export-radarr radarr_config.txt

# Run all reports
python3 corruption_analytics.py all
```

### Example Output

**Success Summary:**
```
================================================================================
                              SUCCESS SUMMARY
================================================================================
  Total Successful Conversions:  142
  Unique Publishers:             15
  HDR Successes:                 45
  Dolby Vision Successes:        28
  Average File Size:             38.5 GB
  Average Duration:              125.3 minutes
```

**Overall Summary:**
```
================================================================================
                              OVERALL SUMMARY
================================================================================
  Total Files Processed:    150
  Successful Conversions:   142
  Corrupted/Failed Files:   8
  Overall Corruption Rate:  5.33%
```

**Recommended Publishers:**
```
================================================================================
      RECOMMENDED PUBLISHERS (min 5 files, max 5.0% failure)
================================================================================
  Publisher/Group         Total  Success  Failed  Rate    Avg Size (GB)
  ---------------------------------------------------------------------
  FraMeSToR              15     15       0       0.0%    42.5
  HQMUX                  12     12       0       0.0%    38.2
  CMRG                   8      8        0       0.0%    35.1

================================================================================
                    RADARR CONFIGURATION SUGGESTIONS
================================================================================

Add these publishers to Radarr Preferred Words:
(Settings → Profiles → Release Profiles → Preferred)

  FraMeSToR                      +10
  HQMUX                          +10
  CMRG                           +10
```

**Quality Scores:**
```
================================================================================
          TOP 50 PUBLISHERS BY QUALITY SCORE (min 3 files)
================================================================================
  Publisher/Group    Total  Success  Success Rate  Quality Score  HDR  DV
  ------------------------------------------------------------------------
  FraMeSToR         15     15       100.0%        120.0          10   8
  HQMUX             12     12       100.0%        116.0          8    6
```

**Format Analysis:**
```
================================================================================
                      CORRUPTION BY VIDEO FORMAT
================================================================================
  Codec   HDR Format       Total  Corrupted  Rate    Avg Size (GB)
  ------------------------------------------------------------------
  hevc    Dolby Vision     25     5          20.0%   45.32
  hevc    HDR10           50     2          4.0%    35.21
  hevc    SDR             75     1          1.33%   25.15
```

## Logs and Database

### Log Files

Logs are stored in: `/var/log/conversions/`

```bash
# View today's log
tail -f /var/log/conversions/conversion_$(date +%Y%m%d).log

# Search for errors
grep "ERROR" /var/log/conversions/*.log

# Check Radarr recovery actions
grep "RADARR RECOVERY" /var/log/conversions/*.log
```

### Corruption Database

Database location: `/var/log/conversions/corruption_tracker.db`

The database tracks:
- **File metadata**: Codec, resolution, HDR format, bit depth
- **HDR/DV info**: Dolby Vision detection, HDR10, HLG, color metadata
- **Release info**: Publisher/group, source type (REMUX, WEB-DL, etc.)
- **Corruption details**: Type, stage, error messages
- **Recovery actions**: Blocklist status, redownload triggers

Direct database access:
```bash
sqlite3 /var/log/conversions/corruption_tracker.db

# Example queries
sqlite> SELECT release_group, COUNT(*) as total FROM corruption_events GROUP BY release_group;
sqlite> SELECT * FROM corruption_events WHERE is_dolby_vision = 1 AND status = 'corrupted';
```

## Troubleshooting

### Radarr Integration Not Working

```bash
# Test if config is loaded
python3 -c "
import sys
sys.path.insert(0, '.')
from convert_mkv_to_mp4 import get_radarr_config
print(get_radarr_config())
"
```

### Check Radarr API Connection

```bash
# Test API connectivity (replace with your API key)
curl -H "X-Api-Key: YOUR_API_KEY" http://localhost:7878/api/v3/system/status
```

### Manual Radarr Recovery

If automatic recovery fails:

1. **Check Blocklist**: `Radarr → Activity → Blocklist`
2. **Remove from Blocklist**: Click X next to the release
3. **Manual Search**: `Radarr → Movies → [Movie] → 🔍 Search`
4. **Select Different Release**: Choose a different quality or group

### Disable Radarr Integration

To temporarily disable automatic blocklisting:

```bash
# Option 1: Empty the API key in config
echo '{"url": "http://localhost:7878", "api_key": ""}' > radarr_config.json

# Option 2: Set empty environment variable
export RADARR_API_KEY=""
```

## File Structure

```
scripts/media-conversion/
├── convert_mkv_to_mp4.py      # Main conversion script with Radarr integration
├── corruption_tracker.py       # Corruption tracking library and metadata extraction
├── corruption_analytics.py     # Analytics dashboard and query tool
├── analyze.sh                  # Quick command wrapper
├── radarr_config.json          # Radarr configuration (gitignored)
├── .env.example                # Environment variable template
├── README.md                   # This file (overview)
├── SETUP_GUIDE.md             # Step-by-step setup instructions
└── FINE_TUNING_GUIDE.md       # Guide for optimizing Radarr with analytics

/var/log/conversions/
├── conversion_YYYYMMDD.log     # Daily conversion logs
└── corruption_tracker.db       # SQLite database with all corruption data
```

## Fine-Tuning Radarr

The system tracks **both successful and failed conversions**, allowing you to optimize Radarr:

### Quick Fine-Tuning Commands

```bash
# Find best publishers
./analyze.sh recommended

# Export Radarr configuration
./analyze.sh export-radarr radarr_preferred.txt

# Check quality scores
./analyze.sh quality

# Best HDR/DV publishers
./analyze.sh hdr-reliable
```

📖 **See [FINE_TUNING_GUIDE.md](FINE_TUNING_GUIDE.md) for complete optimization guide**

## Advanced Usage

### Identifying Problem Publishers

After collecting data from several downloads, you can identify publishers to avoid:

```bash
# Find publishers with >20% corruption rate
python3 corruption_analytics.py worst-publishers --limit 50

# Search specific publisher history
python3 corruption_analytics.py search "SomeGroup"
```

**Example workflow:**
1. Script detects corrupted DV file from "BadGroup"
2. File is auto-blocklisted in Radarr
3. Analytics shows BadGroup has 60% corruption rate on DV files
4. You can manually add BadGroup to Radarr's restricted list
5. Radarr won't download from BadGroup anymore

### Format Insights

Identify problematic format combinations:

```bash
# See which codec+HDR combinations fail most
python3 corruption_analytics.py formats

# Detailed HDR/DV analysis
python3 corruption_analytics.py hdr
```

**Use cases:**
- Avoid Dolby Vision from certain sources if consistently corrupt
- Prefer WEB-DL over REMUX if REMUXes are corrupt
- Identify if HDR10 is more reliable than DV for your setup

### Monitoring Automation

Set up a cron job to email weekly reports:

```bash
# Add to crontab
0 9 * * 1 cd /data/code/home_server/scripts/media-conversion && python3 corruption_analytics.py all > /tmp/corruption_report.txt && mail -s "Weekly Corruption Report" you@example.com < /tmp/corruption_report.txt
```

## Examples

### Test with Corrupted File

```bash
# Create fake corrupted file for testing
mkdir -p "/data/media/movies/Test Movie (2024)"
dd if=/dev/urandom of="/data/media/movies/Test Movie (2024)/Test.mkv" bs=1M count=100

# Run conversion (will detect corruption and trigger Radarr recovery)
python3 convert_mkv_to_mp4.py "/data/media/movies/Test Movie (2024)/Test.mkv"
```

**Expected Output:**
```
======================================================================
INITIATING RADARR RECOVERY PROCESS
======================================================================
Attempting to blocklist release in Radarr...
Movie: Test Movie (2024)
Found movie in Radarr (ID: 123)
✓ Release added to blocklist
✓ Automatic search triggered
  Radarr will search for a better release
✓ File removed from Radarr
✓ Recovery process completed
```

## Support

For issues or questions:
- Check logs in `/var/log/conversions/`
- Verify Radarr API connectivity
- Ensure FFmpeg is installed
- Check file permissions

## License

MIT License - Feel free to modify and use
