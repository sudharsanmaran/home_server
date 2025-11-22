# Jellyfin Migration Plan: Main → jellyfin-test (v10.10.0)

## Overview

Migrate from the corrupted main Jellyfin instance to `jellyfin-test` (v10.10.0) which works with Infuse and has no SendFileAsync bug.

---

## What is the "Instant Notification" Feature?

You mentioned that when Radarr adds a movie, it instantly appears in Jellyfin. This is **Radarr's "Connect" feature**:

- **Location**: Radarr → Settings → Connect → Emby/Jellyfin
- **What it does**: When Radarr imports a movie, it sends an API call to Jellyfin saying "scan this specific movie folder"
- **Result**: Movie appears in Jellyfin within seconds (no manual library scan needed)
- **Current Config**:
  - Host: `YOUR_SERVER_IP:8096` (Tailscale IP)
  - Update Library: `enabled`
  - Pointing to: Main Jellyfin (port 8096)

---

## Migration Strategy

### ✅ What CAN Be Migrated (Easy)

| Item | Source | Target | Difficulty |
|------|--------|--------|------------|
| **Library Paths** | Already configured | Same paths work | ✅ Easy |
| **Media Files** | `/storage/media`, `/data/alldebrid`, `/data/symlinks` | Same locations | ✅ Already working |
| **Radarr Connection** | Port 8096 | Change to 8097 | ✅ Easy (1 setting) |
| **Network/Remote Access** | system.xml | Copy settings | ✅ Easy |
| **Transcoding Settings** | encoding.xml | Copy settings | ✅ Easy |
| **Plugins** | Copy plugin configs | May need reinstall | ⚠️ Medium |

### ❌ What CANNOT Be Migrated (Corrupted Database)

| Item | Why Not | Workaround |
|------|---------|------------|
| **Watch History** | Database corrupted | Use Jellystat (tracks separately) |
| **User Ratings** | Database corrupted | Re-rate favorites |
| **Collections** | Database corrupted | Recreate (or use Radarr collections) |
| **User Preferences** | Database corrupted | Reconfigure per user |
| **Continue Watching** | Database corrupted | Lost, start fresh |

### ⚠️ What MIGHT Be Migrated (Partial)

| Item | Method | Notes |
|------|--------|-------|
| **User Accounts** | Export/recreate | Need to recreate passwords |
| **API Keys** | Copy from old config | May need to regenerate |
| **Scheduled Tasks** | Copy settings | Should work |

---

## Migration Steps

### Phase 1: Verify jellyfin-test Setup (15 min)

#### 1.1 Check Library Paths
```bash
# Check if libraries are configured
docker exec jellyfin-test ls /data/media/movies
docker exec jellyfin-test ls /data/symlinks/radarr
docker exec jellyfin-test ls /data/alldebrid/magnets
```

#### 1.2 Check Users
```bash
# List existing users in jellyfin-test
docker exec jellyfin-test ls -la /config/data/data/
```

#### 1.3 Get jellyfin-test API Key
- Navigate to: `http://YOUR_IP:8097/web/index.html`
- Dashboard → API Keys → Create new key: `radarr-connect`
- Save this key for Step 2.3

---

### Phase 2: Copy Safe Configuration Files (10 min)

These files are safe to copy because they don't involve the corrupted database:

#### 2.1 Network Settings (Optional)
```bash
# Copy network configuration if needed
cp /data/code/home_server/services/media/config/network.xml \
   /data/code/home_server/services/media/config-test/network.xml
```

#### 2.2 Transcoding Settings
```bash
# Copy transcoding/encoding settings
cp /data/code/home_server/services/media/config/encoding.xml \
   /data/code/home_server/services/media/config-test/encoding.xml

# Restart jellyfin-test to apply
docker compose restart jellyfin-test
```

#### 2.3 Copy Branding/Customization (if any)
```bash
# If you customized branding
cp /data/code/home_server/services/media/config/branding.xml \
   /data/code/home_server/services/media/config-test/branding.xml 2>/dev/null || echo "No branding file"
```

---

### Phase 3: Reconnect Radarr to jellyfin-test (5 min)

#### 3.1 Update Radarr Connection

**Option A: Via Radarr Web UI (Recommended)**
1. Go to: `http://YOUR_IP:7878/settings/connect`
2. Click on existing "Emby / Jellyfin" connection
3. Change:
   - **Port**: `8096` → `8097`
   - **API Key**: Paste the new API key from jellyfin-test
4. Click "Test" → should show success
5. Save

**Option B: Via API**
```bash
# Get the connection ID
curl -s "http://localhost:7878/api/v3/notification" \
  -H "X-Api-Key: YOUR_RADARR_API_KEY" | grep -B5 "Jellyfin"

# Update connection (replace ID and API_KEY)
curl -X PUT "http://localhost:7878/api/v3/notification/1" \
  -H "X-Api-Key: YOUR_RADARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "port": 8097,
    "apiKey": "YOUR_JELLYFIN_TEST_API_KEY"
  }'
```

#### 3.2 Trigger Test Import
```bash
# Trigger Radarr to rescan a movie (replace movieId with actual ID)
curl -X POST "http://localhost:7878/api/v3/command" \
  -H "X-Api-Key: YOUR_RADARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "RescanMovie", "movieId": 123}'
```

Within 5-10 seconds, Vada Chennai should appear in jellyfin-test!

---

### Phase 4: Set Up Libraries in jellyfin-test (10 min)

If libraries aren't configured yet:

#### 4.1 Add Movie Libraries
1. Go to: `http://YOUR_IP:8097`
2. Dashboard → Libraries → Add Library
3. Configure libraries:

**Library 1: Local Movies**
- Content Type: `Movies`
- Display Name: `Movies`
- Folders: `/data/media/movies`

**Library 2: Cloud Movies (AllDebrid)**
- Content Type: `Movies`
- Display Name: `Cloud Movies`
- Folders: `/data/symlinks/radarr`

**Library 3: Tamil Movies (Optional)**
- Content Type: `Movies`
- Display Name: `Tamil Movies`
- Folders: `/data/media/movies-tamil`

#### 4.2 Configure Library Settings
For each library:
- Enable: `Allow embedded metadata`, `Download images`, `Automatically refresh metadata`
- Set Preferred Language: `Tamil` (for Tamil library)
- Set Country: `India` (for Tamil library)

---

### Phase 5: Recreate User Accounts (15 min)

Since the database is corrupted, manually recreate users:

#### 5.1 Create Admin User (if needed)
1. Dashboard → Users → Add User
2. Username: `admin`
3. Set password
4. Enable all permissions

#### 5.2 Create Other Users
For each user, recreate:
- Username
- Password
- Library access permissions
- Playback settings (transcoding limits, etc.)

---

### Phase 6: Optional Enhancements

#### 6.1 Install Plugins (if needed)
If you had plugins on the old Jellyfin:

**Common Plugins**:
- Webhook (for smart download automation)
- Playback Reporting
- TMDb Box Sets
- Intro Skipper

Install via: Dashboard → Plugins → Catalog

#### 6.2 Copy Plugin Configurations
```bash
# Only if plugins are identical versions
cp -r /data/code/home_server/services/media/config/plugins/* \
      /data/code/home_server/services/media/config-test/plugins/

docker compose restart jellyfin-test
```

#### 6.3 Set Up Scheduled Tasks
Dashboard → Scheduled Tasks:
- Library scan: Every 6 hours
- Backup: Daily at 3 AM
- Clean cache: Weekly

---

### Phase 7: Decommission Old Jellyfin (Later)

Once jellyfin-test is working perfectly:

#### 7.1 Stop Main Jellyfin
```bash
# Stop the broken container
docker compose stop jellyfin
```

#### 7.2 Rename jellyfin-test → jellyfin (Optional)

If you want jellyfin-test to become the main instance:

**Update compose.yml**:
```yaml
# Rename service
jellyfin:  # was jellyfin-test
  image: lscr.io/linuxserver/jellyfin:10.10.0
  container_name: jellyfin
  ports:
    - 8096:8096  # Use main port
```

**Update Radarr connection** back to port 8096.

#### 7.3 Archive Old Config
```bash
# Backup the broken config
mkdir -p /data/code/home_server/services/media/config-backup-corrupted
mv /data/code/home_server/services/media/config/* \
   /data/code/home_server/services/media/config-backup-corrupted/
```

---

## Verification Checklist

After migration, verify:

- [ ] All libraries visible in jellyfin-test
- [ ] Vada Chennai appears in library
- [ ] Vada Chennai plays in web browser
- [ ] Vada Chennai plays in Infuse (Mac/iPhone)
- [ ] Radarr connection test succeeds
- [ ] New movie import → appears instantly in Jellyfin
- [ ] User accounts work
- [ ] Remote access works (Tailscale)
- [ ] Transcoding works (if needed)
- [ ] Hardware acceleration enabled (Intel QSV)

---

## Expected Timeline

| Phase | Time | Can Skip? |
|-------|------|-----------|
| Phase 1: Verify Setup | 15 min | No |
| Phase 2: Copy Config | 10 min | Partial |
| Phase 3: Radarr Connect | 5 min | **No** (Critical) |
| Phase 4: Libraries | 10 min | No |
| Phase 5: User Accounts | 15 min | No |
| Phase 6: Plugins | 20 min | Yes |
| Phase 7: Decommission | 10 min | Later |
| **Total (Minimum)** | **~45 min** | Core migration |
| **Total (Complete)** | **~85 min** | With plugins |

---

## What You'll Lose (from corrupted database)

❌ **Lost Forever**:
- Watch history (what you've watched)
- Continue watching positions
- User ratings
- Custom collections
- Playback resume points

✅ **Preserved**:
- All media files
- Library structure
- Radarr integration
- Infuse compatibility
- Remote access
- Future watch tracking (Jellystat)

---

## Post-Migration: Prevent Future Issues

### Use Jellystat for Watch Tracking
Jellystat already tracks watch history separately from Jellyfin database. This gives you:
- Backup of watch data
- Analytics
- Independent tracking even if Jellyfin database breaks

### Regular Backups
```bash
# Create backup script
cat > /data/code/home_server/scripts/backup-jellyfin.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/data/backups/jellyfin"
mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup config (excluding cache)
tar -czf "$BACKUP_DIR/jellyfin-config-$DATE.tar.gz" \
  --exclude='cache' \
  --exclude='transcodes' \
  /data/code/home_server/services/media/config-test/

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/jellyfin-config-*.tar.gz | tail -n +8 | xargs -r rm
EOF

chmod +x /data/code/home_server/scripts/backup-jellyfin.sh

# Add to crontab
echo "0 3 * * * /data/code/home_server/scripts/backup-jellyfin.sh" | crontab -
```

---

## Troubleshooting

### Issue: Radarr connection test fails
**Solution**:
- Check jellyfin-test is running: `docker ps | grep jellyfin-test`
- Verify API key is correct
- Check port 8097 is accessible: `curl http://localhost:8097/health`

### Issue: Movies don't appear instantly
**Solution**:
- Verify "Update Library" is enabled in Radarr connection
- Check Radarr logs: `docker logs radarr 2>&1 | grep Jellyfin`
- Manually trigger: RescanMovie in Radarr

### Issue: Infuse won't connect
**Solution**:
- Use port 8097 in Infuse settings
- Verify Direct Play is enabled (no transcoding)
- Check network access (Tailscale IP or local IP)

---

## Next Steps After Migration

Once jellyfin-test is stable:

1. **Complete smart download automation** (from SMART_DOWNLOAD_AUTOMATION_PLAN.md)
   - Install Jellyfin Webhook plugin on jellyfin-test
   - Configure webhook to point to media-converter container
   - Test Vada Chennai playback tracking

2. **Configure Sonarr** (TV shows)
   - Same AllDebrid setup as Radarr
   - Connect to jellyfin-test

3. **Monitor Jellystat**
   - Ensure it's tracking jellyfin-test instead of main Jellyfin
   - Update connection if needed

---

## Summary

**Simple Migration Path** (45 min):
1. Get jellyfin-test API key
2. Update Radarr connection: port `8097`, new API key
3. Set up libraries in jellyfin-test
4. Recreate user accounts
5. Verify Vada Chennai appears and plays

**Result**: Working Jellyfin v10.10.0 with:
- ✅ Infuse compatibility
- ✅ Radarr instant notifications
- ✅ All AllDebrid sources (history, links, magnets)
- ✅ No SendFileAsync bug
