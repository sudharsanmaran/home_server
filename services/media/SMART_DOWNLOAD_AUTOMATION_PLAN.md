# Smart Download Automation System - Complete Implementation Plan

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Data Flow](#data-flow)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Installation Steps](#installation-steps)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Monitoring & Maintenance](#monitoring--maintenance)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

### Purpose
Automatically download movies from AllDebrid cloud to local HDD storage based on watch patterns and content rarity, optimizing storage usage while ensuring favorite content is permanently available.

### Goals
- ✅ **Smart Storage**: Only download content worth keeping
- ✅ **Automatic Detection**: Track rewatches and identify favorites
- ✅ **Rare Content Preservation**: Download hard-to-find content immediately
- ✅ **User-Specific**: Track your viewing habits, not guests
- ✅ **Zero Manual Work**: Fully automated after setup

### Key Metrics
- **Target**: Save ~70% HDD space vs downloading everything
- **Download Threshold**: 2 rewatches within 90 days
- **Rare Content**: IMDb ≥8.5 OR <10 seeders OR special editions
- **Processing Time**: <5 seconds per playback event

---

## 🏗️ Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        PLAYBACK EVENT                            │
│                User watches movie in Infuse                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    JELLYFIN SERVER                               │
│  - Tracks playback (start, progress, stop)                      │
│  - Updates watch count in database                              │
│  - Triggers webhook plugin                                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ HTTP POST (JSON payload)
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  WEBHOOK SERVER (Flask)                          │
│  Port: 5000                                                      │
│  - Receives playback events                                     │
│  - Validates event (PlaybackStop, >90% watched)                 │
│  - Calls smart_download.py script                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Executes Python script
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              SMART DOWNLOAD SCRIPT (Python)                      │
│  Logic Flow:                                                     │
│  1. Extract user, movie, IP from webhook payload                │
│  2. Check if tracked user (you vs guests)                       │
│  3. Query watch count (Jellystat or Jellyfin API)              │
│  4. Check if rare content (keywords, year, IMDb)                │
│  5. Apply decision rules                                        │
│  6. Trigger download if criteria met                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
┌──────────────────┐    ┌──────────────────────┐
│  JELLYSTAT API   │    │   JELLYFIN API       │
│  Get watch count │    │   Get movie metadata │
│  User: admin     │    │   PlayCount, Rating  │
└──────────────────┘    └──────────────────────┘
          │                        │
          └───────────┬────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DECISION ENGINE                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ TIER 1: Instant Download (High Priority)              │    │
│  │ - IMDb ≥ 8.5 (classics)                                │    │
│  │ - Rare content (old, foreign, special editions)       │    │
│  │ - Manually marked "favorite" in Radarr                │    │
│  │ - Family/Animation genre                              │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ TIER 2: After Rewatch (Medium Priority)               │    │
│  │ - Watch count ≥ 2 within 90 days                      │    │
│  │ - IMDb 7.0-8.4                                         │    │
│  │ - User = tracked user (you)                           │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ TIER 3: Never Download (Stream Only)                  │    │
│  │ - IMDb < 7.0                                           │    │
│  │ - Watched once only                                    │    │
│  │ - TV shows (too much space)                           │    │
│  │ - Guest users (not your content)                      │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
              YES: Download
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RADARR API                                   │
│  POST /api/v3/command                                           │
│  {                                                               │
│    "name": "MoviesSearch",                                      │
│    "movieIds": [85]                                             │
│  }                                                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RDTCLIENT (Download)                          │
│  - Searches for movie in AllDebrid                              │
│  - Already available (added when streaming)                     │
│  - Downloads via aria2 to /data/downloads                       │
│  - 20 minute download (limited by internet speed)               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RADARR (Import)                               │
│  - Detects completed download                                   │
│  - Renames and organizes file                                   │
│  - Moves to /storage/media/movies/                              │
│  - Updates Jellyfin library                                     │
│  - File now permanent on HDD                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Components

### 1. Jellyfin Webhook Plugin
- **Purpose**: Sends playback events to webhook server
- **Events**: PlaybackStart, PlaybackProgress, PlaybackStop
- **Format**: JSON over HTTP POST
- **Version**: Latest from Jellyfin plugin catalog

### 2. Webhook Server (Flask)
- **Technology**: Python Flask
- **Port**: 5000 (internal Docker network)
- **Endpoints**:
  - `/health` - Health check
  - `/jellyfin/playback` - Playback event receiver
  - `/jellyfin/generic` - Generic event receiver (future use)
- **Container**: Runs in media-converter container

### 3. Smart Download Script
- **Language**: Python 3
- **Dependencies**: requests, json, logging
- **Location**: `/app/smart_download.py`
- **Execution**: Triggered by webhook server
- **Logs**: `/var/log/conversions/smart_download.log`

### 4. Jellystat
- **Purpose**: Watch history analytics
- **Database**: PostgreSQL
- **Port**: 3000
- **API**: RESTful endpoints for query

### 5. Radarr
- **Purpose**: Movie management & download orchestration
- **API**: v3 REST API
- **Port**: 7878
- **API Key**: Get from Radarr → Settings → General → API Key

---

## 📊 Data Flow

### Phase 1: Playback Detection (Real-time)

```json
// Jellyfin Webhook Payload Example
{
  "Event": "PlaybackStop",
  "User": {
    "Name": "admin",
    "Id": "user-uuid-here"
  },
  "UserId": "user-uuid-here",
  "ItemId": "item-uuid-here",
  "Item": {
    "Name": "The Long Walk",
    "Type": "Movie",
    "ProductionYear": 2025,
    "RunTimeTicks": 91234567890
  },
  "PlaybackInfo": {
    "PositionTicks": 85234567890,
    "PlayMethod": "DirectPlay"
  },
  "Session": {
    "RemoteEndPoint": "192.168.x.x",
    "Client": "Infuse",
    "DeviceName": "iPhone"
  }
}
```

### Phase 2: Data Enrichment (API Queries)

**Jellystat API Call:**
```bash
GET http://jellystat:3000/api/getItemHistory?itemId={item_id}&userId={user_id}

Response:
[
  {
    "timestamp": "2025-11-15T10:30:00Z",
    "playDuration": 7200000,
    "percentWatched": 95
  },
  {
    "timestamp": "2025-11-10T20:15:00Z",
    "playDuration": 7200000,
    "percentWatched": 100
  }
]

Watch Count: 2
```

**Jellyfin API Call:**
```bash
GET http://jellyfin:8096/Users/{user_id}/Items/{item_id}
Headers: X-MediaBrowser-Token: {api_key}

Response:
{
  "Name": "The Long Walk",
  "ProductionYear": 2025,
  "CommunityRating": 7.8,  // IMDb rating
  "Genres": ["Thriller", "Sci-Fi"],
  "UserData": {
    "PlayCount": 2,
    "IsFavorite": false
  }
}
```

**Radarr API Call:**
```bash
GET http://radarr:7878/api/v3/movie
Headers: X-Api-Key: {api_key}

Response:
[
  {
    "id": 85,
    "title": "The Long Walk",
    "year": 2025,
    "tmdbId": 123456,
    "path": "/data/symlinks/radarr/The Long Walk (2025)",
    "hasFile": true,
    "tags": []
  }
]
```

### Phase 3: Decision Logic

```python
# Simplified decision tree
def should_download(movie_data):
    user = movie_data['user']
    watch_count = movie_data['watch_count']
    imdb_rating = movie_data['imdb_rating']
    year = movie_data['year']
    genres = movie_data['genres']

    # TIER 1: Instant Download
    if imdb_rating >= 8.5:
        return True, "IMDb ≥8.5 (classic)"

    if is_rare_content(movie_data):
        return True, "Rare/special content"

    if 'Animation' in genres or 'Family' in genres:
        return True, "Family/kids content"

    # TIER 2: After Rewatch
    if user == TRACKED_USER and watch_count >= 2:
        return True, f"Rewatched {watch_count} times"

    # TIER 3: Stream Only
    return False, "One-time watch"
```

### Phase 4: Download Trigger

```bash
POST http://radarr:7878/api/v3/command
Headers: X-Api-Key: {api_key}
Content-Type: application/json

{
  "name": "MoviesSearch",
  "movieIds": [85]
}

Response:
{
  "id": 1234,
  "name": "MoviesSearch",
  "state": "queued",
  "started": "2025-11-15T12:00:00Z"
}
```

---

## 📚 API Endpoints Reference

### Jellyfin API

| Endpoint | Method | Purpose | Headers |
|----------|--------|---------|---------|
| `/Users/{userId}/Items/{itemId}` | GET | Get movie metadata | `X-MediaBrowser-Token` |
| `/Users/{userId}/Items` | GET | Get user library | `X-MediaBrowser-Token` |
| `/System/Info` | GET | Server info | `X-MediaBrowser-Token` |

**API Key Location**: Jellyfin Dashboard → API Keys

### Jellystat API

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/api/getItemHistory` | GET | Item watch history | API Key (optional) |
| `/api/getUserHistory` | GET | User watch history | API Key (optional) |
| `/api/getHistory` | GET | General history | API Key (optional) |

**API Key**: Settings → API Key (in Jellystat web UI)

### Radarr API

| Endpoint | Method | Purpose | Headers |
|----------|--------|---------|---------|
| `/api/v3/movie` | GET | List all movies | `X-Api-Key` |
| `/api/v3/movie/{id}` | GET | Get movie details | `X-Api-Key` |
| `/api/v3/command` | POST | Execute command | `X-Api-Key` |
| `/api/v3/tag` | GET | List tags | `X-Api-Key` |

**Available Commands**:
- `MoviesSearch` - Search for specific movies
- `MissingMoviesSearch` - Search all missing
- `RefreshMovie` - Refresh metadata

---

## 🚀 Installation Steps

### Step 1: Install Jellyfin Webhook Plugin

1. **Navigate to Jellyfin Dashboard**
   ```
   http://YOUR_SERVER_IP:8097 → Dashboard → Plugins
   ```

2. **Install from Catalog**
   - Scroll to "Notifications" section
   - Find "Webhook" plugin
   - Click Install
   - **Restart Jellyfin** (very important!)

3. **Verify Installation**
   ```
   Dashboard → Plugins → My Plugins → Should see "Webhook"
   ```

### Step 2: Update media-converter Container

**Edit `/data/code/home_server/services/media/compose.yml`:**

```yaml
media-converter:
  build: /data/code/home_server/scripts/media-conversion
  container_name: media-converter
  restart: unless-stopped
  environment:
    - PUID=${PUID}
    - PGID=${PGID}
    - TZ=${TZ}
    - RADARR_URL=http://radarr:7878
    - RADARR_API_KEY=${RADARR_API_KEY}
    - JELLYFIN_URL=http://jellyfin-test:8096
    - JELLYFIN_API_KEY=  # Get from Jellyfin Dashboard → API Keys
    - JELLYSTAT_URL=http://jellystat:3000
    - TRACKED_USER_NAME=admin  # Your Jellyfin username
    - WATCH_COUNT_THRESHOLD=2  # Download after 2 watches
    - FLASK_APP=webhook_server.py
  volumes:
    - /data/code/home_server/scripts/media-conversion:/app
    - /storage/media:/data/media
    - /data/code/home_server/services/media/media-converter/logs:/var/log/conversions
  ports:
    - 5000:5000  # Webhook server port
  depends_on:
    - radarr
    - jellyfin-test
    - jellystat
```

### Step 3: Create Dockerfile for Webhook Server

**Create `/data/code/home_server/scripts/media-conversion/Dockerfile`:**

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN pip install --no-cache-dir flask requests

# Set working directory
WORKDIR /app

# Copy scripts
COPY smart_download.py /app/
COPY webhook_server.py /app/

# Make executable
RUN chmod +x /app/*.py

# Create log directory
RUN mkdir -p /var/log/conversions

# Expose webhook port
EXPOSE 5000

# Start webhook server
CMD ["python3", "/app/webhook_server.py"]
```

### Step 4: Get Jellyfin API Key

1. **Open Jellyfin Dashboard**
   ```
   http://YOUR_SERVER_IP:8097 → Dashboard
   ```

2. **Navigate to API Keys**
   ```
   Dashboard → Advanced → API Keys → Add
   ```

3. **Create New Key**
   - App Name: `Smart Download Automation`
   - Click Save
   - **Copy the API key** (you won't see it again!)

4. **Update .env file**
   ```bash
   echo "JELLYFIN_API_KEY=your-api-key-here" >> /data/code/home_server/services/media/.env
   ```

### Step 5: Build and Start Containers

```bash
cd /data/code/home_server/services/media

# Build media-converter with webhook server
docker compose build media-converter

# Start all services
docker compose up -d

# Verify webhook server is running
docker logs media-converter --tail 50

# Should see:
# * Running on all addresses (0.0.0.0)
# * Running on http://127.0.0.1:5000
# * Running on http://172.x.x.x:5000
```

### Step 6: Configure Jellyfin Webhook

1. **Open Webhook Plugin Settings**
   ```
   Jellyfin Dashboard → Plugins → My Plugins → Webhook → Settings
   ```

2. **Add Generic Destination**
   - Click "Add Generic Destination"
   - **Webhook Name**: `Smart Download Automation`
   - **Webhook URL**: `http://media-converter:5000/jellyfin/playback`
   - **Notification Type**: Enable ONLY:
     - ✅ `Playback Stop`
   - **User Filter**: Select ONLY your user (e.g., "admin")
   - **Send All Properties**: ✅ Enabled

3. **Template Configuration** (Optional - use default)

4. **Save Settings**

### Step 7: Test the System

**Test webhook connectivity:**
```bash
# From your server
curl -X POST http://localhost:5000/health

# Expected response:
# {"status":"healthy"}
```

**Test with sample playback event:**
```bash
docker exec media-converter python3 /app/smart_download.py test

# Check logs
docker logs media-converter --tail 20
```

---

## ⚙️ Configuration

### Environment Variables

Create or update `/data/code/home_server/services/media/.env`:

```bash
# Jellyfin Configuration
JELLYFIN_API_KEY=your-jellyfin-api-key-here

# User Tracking
TRACKED_USER_NAME=admin  # Your Jellyfin username

# Download Thresholds
WATCH_COUNT_THRESHOLD=2      # Download after N watches
MIN_SEEDERS_RARE=10          # <N seeders = rare content

# Network Detection (simplified - not used if using user-based tracking)
LOCAL_NETWORK=192.168.       # Your local network prefix
TAILSCALE_NETWORK=100.64.    # Tailscale network prefix
```

### Threshold Recommendations

| Threshold | Value | Reasoning |
|-----------|-------|-----------|
| **Watch Count** | 2 | Balances storage vs convenience. 1 = too eager, 3 = you'll forget |
| **IMDb Rating** | 8.5 | All-time classics worth keeping |
| **IMDb Rating (Good)** | 7.0 | Decent movies, download after rewatch |
| **Min Seeders (Rare)** | 10 | Low availability = download immediately |
| **Watch Completion** | 90% | Must watch at least 90% to count |
| **Time Window** | 90 days | Rewatches within 3 months = favorite |

### Rare Content Detection Rules

The system automatically detects rare content based on:

1. **Keywords in title:**
   - "criterion", "director's cut", "restored"
   - "remastered", "limited edition", "uncut"
   - "extended", "collector's edition", "special edition"

2. **Age + Language:**
   - Year < 1990 AND not English = rare

3. **IMDb Metrics:**
   - Rating ≥ 8.0 AND votes < 50,000 = hidden gem

4. **Genre:**
   - "Foreign", "World Cinema", "Silent"

5. **Future: Torrent Seeders** (requires Prowlarr integration)
   - Seeders < 10 = rare

---

## 🧪 Testing

### Phase 1: Component Testing

#### Test 1: Webhook Server Health
```bash
curl http://localhost:5000/health

# Expected: {"status":"healthy"}
```

#### Test 2: Smart Download Script
```bash
docker exec media-converter python3 /app/smart_download.py test

# Check logs:
docker logs media-converter | grep "DOWNLOAD TRIGGERED"
```

#### Test 3: Jellyfin API Access
```bash
# Get your user ID
curl -H "X-MediaBrowser-Token: YOUR_API_KEY" \
  http://localhost:8097/Users

# Get a movie
curl -H "X-MediaBrowser-Token: YOUR_API_KEY" \
  "http://localhost:8097/Users/USER_ID/Items?IncludeItemTypes=Movie&Limit=1"
```

#### Test 4: Radarr API Access
```bash
curl -H "X-Api-Key: YOUR_RADARR_API_KEY" \
  http://localhost:7878/api/v3/movie | jq '.[0]'
```

### Phase 2: Integration Testing

#### Test 5: End-to-End Playback Event

1. **Watch a movie in Infuse** (watch >90%)
2. **Check webhook received:**
   ```bash
   docker logs media-converter | grep "Received playback event"
   ```
3. **Check decision made:**
   ```bash
   docker logs media-converter | grep "DOWNLOAD TRIGGERED\|No download needed"
   ```

#### Test 6: Trigger Download Manually

**Force a download for testing:**
```python
# Create test file: /tmp/test_download.py
import requests

radarr_url = "http://localhost:7878"
api_key = "YOUR_RADARR_API_KEY"

# Get first movie ID
movies = requests.get(
    f"{radarr_url}/api/v3/movie",
    headers={"X-Api-Key": api_key}
).json()

movie_id = movies[0]['id']

# Trigger search
response = requests.post(
    f"{radarr_url}/api/v3/command",
    headers={"X-Api-Key": api_key},
    json={"name": "MoviesSearch", "movieIds": [movie_id]}
)

print(response.json())
```

Run:
```bash
python3 /tmp/test_download.py
```

### Phase 3: Load Testing

#### Test 7: Multiple Playback Events
```bash
# Simulate 10 playback events
for i in {1..10}; do
  docker exec media-converter python3 /app/smart_download.py test
  sleep 2
done

# Check logs for performance
docker logs media-converter | grep "processing time"
```

---

## 📊 Monitoring & Maintenance

### Log Files

All logs stored in: `/data/code/home_server/services/media/media-converter/logs/`

1. **`smart_download.log`** - Download decisions
   ```bash
   tail -f /data/code/home_server/services/media/media-converter/logs/smart_download.log
   ```

2. **`webhook_server.log`** - Webhook events
   ```bash
   tail -f /data/code/home_server/services/media/media-converter/logs/webhook_server.log
   ```

### Key Metrics to Monitor

```bash
# Download trigger rate (per day)
grep "DOWNLOAD TRIGGERED" smart_download.log | grep "$(date +%Y-%m-%d)" | wc -l

# Rejection rate (stream-only)
grep "No download needed" smart_download.log | grep "$(date +%Y-%m-%d)" | wc -l

# Watch count distribution
grep "Watch count for" smart_download.log | awk '{print $NF}' | sort | uniq -c
```

### Dashboard (Optional - Future Enhancement)

Create Grafana dashboard using log data:
- Download trigger rate over time
- Top rewatched movies
- Storage saved (estimated)
- User watch patterns

### Maintenance Tasks

#### Weekly:
- Review `smart_download.log` for unexpected behavior
- Check download queue in Radarr
- Verify HDD space usage

#### Monthly:
- Rotate logs (auto-configured)
- Review and adjust thresholds if needed
- Check for Jellyfin/Radarr plugin updates

#### Quarterly:
- Analyze which movies were downloaded but never rewatched
- Consider removing low-value downloads
- Optimize rules based on actual usage

---

## 🔍 Troubleshooting

### Issue 1: Webhook Not Triggering

**Symptoms:**
- Movie playback stops but nothing in logs
- No "Received playback event" messages

**Diagnosis:**
```bash
# Check webhook server is running
docker ps | grep media-converter

# Check webhook server logs
docker logs media-converter | grep "Running on"

# Check Jellyfin webhook config
# Jellyfin Dashboard → Plugins → Webhook → Settings
# Verify URL: http://media-converter:5000/jellyfin/playback
```

**Solutions:**
1. Restart media-converter: `docker compose restart media-converter`
2. Verify webhook plugin is installed and enabled
3. Check Jellyfin logs: `docker logs jellyfin-test | grep -i webhook`
4. Test webhook manually:
   ```bash
   docker exec jellyfin-test curl -X POST http://media-converter:5000/health
   ```

### Issue 2: Watch Count Always 0

**Symptoms:**
- Logs show "Watch count for Movie: 0" even after watching

**Diagnosis:**
```bash
# Check if Jellyfin is tracking playback
curl -H "X-MediaBrowser-Token: YOUR_API_KEY" \
  "http://localhost:8097/Users/USER_ID/Items/ITEM_ID" | jq '.UserData'

# Check Jellystat database
docker exec jellystat-db psql -U postgres -d jellystat \
  -c "SELECT * FROM playback_activity ORDER BY date DESC LIMIT 5;"
```

**Solutions:**
1. Ensure movie was watched >90%
2. Check user ID matches in script
3. Verify Jellystat is syncing with Jellyfin
4. Use Jellyfin API as fallback (already in script)

### Issue 3: Downloads Not Triggering in Radarr

**Symptoms:**
- Logs show "DOWNLOAD TRIGGERED" but Radarr doesn't download

**Diagnosis:**
```bash
# Check Radarr queue
curl -H "X-Api-Key: YOUR_RADARR_API_KEY" \
  http://localhost:7878/api/v3/queue | jq

# Check Radarr command history
curl -H "X-Api-Key: YOUR_RADARR_API_KEY" \
  http://localhost:7878/api/v3/command | jq
```

**Solutions:**
1. Verify movie exists in Radarr library
2. Check movie isn't already downloaded to HDD
3. Verify rdtclient is connected to Radarr
4. Check Radarr logs: `docker logs radarr | tail -50`

### Issue 4: High CPU/Memory Usage

**Symptoms:**
- media-converter container using >10% CPU constantly

**Diagnosis:**
```bash
docker stats media-converter

# Check for webhook spam
docker logs media-converter | grep "Received playback event" | tail -20
```

**Solutions:**
1. Add rate limiting to webhook server
2. Check for playback loops (same movie repeating)
3. Increase `WATCH_COUNT_THRESHOLD` to reduce processing

### Issue 5: False Positives (Downloading Everything)

**Symptoms:**
- Too many movies being downloaded
- HDD filling up quickly

**Diagnosis:**
```bash
# Check decision reasons
grep "DOWNLOAD TRIGGERED" smart_download.log | awk -F'Reason: ' '{print $2}' | sort | uniq -c
```

**Solutions:**
1. Increase `WATCH_COUNT_THRESHOLD` from 2 to 3
2. Disable rare content detection temporarily
3. Add genre exclusions (e.g., skip "Documentary")
4. Require higher IMDb rating threshold

### Issue 6: Missing Dependencies

**Symptoms:**
- `ModuleNotFoundError: No module named 'flask'`

**Solution:**
```bash
# Rebuild container
docker compose build media-converter --no-cache
docker compose up -d media-converter
```

---

## 📈 Expected Outcomes

### Storage Savings

**Scenario: 100 Movies Per Year**

| Without Automation | With Automation | Savings |
|-------------------|-----------------|---------|
| 100 movies × 15GB | 30 movies × 15GB | **70% saved** |
| = 1.5TB used | = 450GB used | = 1TB freed |

### Workflow Impact

**Before:**
```
Watch movie → Manually decide → Tag in Radarr → Wait 20 mins → Check if downloaded
Time: 5 minutes of manual work per decision
```

**After:**
```
Watch movie → System decides automatically → Downloads if needed
Time: 0 minutes of manual work
```

### User Experience

- ✅ **No manual tagging** required
- ✅ **Favorites always available** on HDD after 2nd watch
- ✅ **Classics downloaded** immediately (IMDb 8.5+)
- ✅ **Rare content preserved** before it disappears
- ✅ **HDD space optimized** - only keep what matters
- ✅ **Zero maintenance** after initial setup

---

## 🎯 Future Enhancements

### Phase 2 Features (Optional)

1. **Prowlarr Seeder Integration**
   - Query actual torrent seeders via Prowlarr API
   - More accurate rare content detection

2. **Multi-User Support**
   - Track family members separately
   - Different thresholds per user
   - "Dad's rewatches" vs "Kids' rewatches"

3. **Smart Deletion**
   - Remove HDD content not watched in 180 days
   - Keep high-rated content forever
   - Free space automatically

4. **Notification System**
   - Discord/Telegram alerts when downloading
   - Weekly summary of downloads
   - Storage usage reports

5. **Machine Learning**
   - Learn your preferences over time
   - Predict which movies you'll rewatch
   - Auto-adjust thresholds

6. **Web Dashboard**
   - View download decisions in real-time
   - Override rules per movie
   - Statistics and analytics

---

## 📞 Support & Resources

### Documentation
- [Jellyfin Webhook Plugin](https://github.com/jellyfin/jellyfin-plugin-webhook)
- [Radarr API Docs](https://radarr.video/docs/api/)
- [Jellystat GitHub](https://github.com/CyferShepard/Jellystat)

### Log Locations
- Smart Download: `/data/code/home_server/services/media/media-converter/logs/smart_download.log`
- Webhook Server: `/data/code/home_server/services/media/media-converter/logs/webhook_server.log`
- Jellyfin: `docker logs jellyfin-test`
- Radarr: `docker logs radarr`

### Configuration Files
- Docker Compose: `/data/code/home_server/services/media/compose.yml`
- Environment: `/data/code/home_server/services/media/.env`
- Scripts: `/data/code/home_server/scripts/media-conversion/`

---

## ✅ Pre-Implementation Checklist

Before starting installation:

- [ ] Jellyfin 10.10.0 working with Infuse
- [ ] Jellystat installed and syncing
- [ ] Radarr managing movies successfully
- [ ] AllDebrid + rclone mount operational
- [ ] rdtclient-symlink creating symlinks
- [ ] HDD has sufficient space (500GB+ recommended)
- [ ] Backup current Jellyfin/Radarr config
- [ ] Test internet speed (needed for downloads)
- [ ] Understand the automation logic (read this doc!)

---

## 🎬 Quick Start Command Summary

```bash
# 1. Install Jellyfin Webhook Plugin
# Manual: Jellyfin Dashboard → Plugins → Install Webhook → Restart

# 2. Get Jellyfin API Key
# Manual: Jellyfin Dashboard → API Keys → Add New

# 3. Update environment
cd /data/code/home_server/services/media
nano .env
# Add: JELLYFIN_API_KEY=your-key-here

# 4. Build and start
docker compose build media-converter
docker compose up -d

# 5. Configure webhook
# Manual: Jellyfin → Plugins → Webhook → Settings
# URL: http://media-converter:5000/jellyfin/playback
# Event: Playback Stop only
# User: Your username only

# 6. Test
curl http://localhost:5000/health
docker exec media-converter python3 /app/smart_download.py test

# 7. Monitor logs
docker logs media-converter --tail 50 -f

# 8. Watch a movie and verify!
```

---

**Ready to implement? Let's start with Step 1: Installing the Jellyfin Webhook Plugin!**
