# Troubleshooting Guide

Common issues encountered with the media stack and their solutions.

## Table of Contents
- [RDTClient Issues](#rdtclient-issues)
- [Rclone Mount Issues](#rclone-mount-issues)
- [Jellyfin Issues](#jellyfin-issues)
- [Jellyseerr Issues](#jellyseerr-issues)
- [General Tips](#general-tips)

---

## RDTClient Issues

### Mount Path Does Not Exist
**Error:** `Mount path /mnt/rd does not exist!`

**Cause:** RDTClient's `RcloneMountPath` setting doesn't match the actual mount location.

**Solution:**
1. Go to RDTClient UI → Settings → Download Client
2. Set `Rclone Mount Path` to `/data/alldebrid`
3. Save and restart RDTClient

Or via SQLite:
```bash
docker run --rm -v ./rdtclient:/db alpine sh -c \
  "apk add --quiet sqlite && sqlite3 /db/rdtclient.db \
  \"UPDATE Settings SET Value='/data/alldebrid' WHERE SettingId='DownloadClient:RcloneMountPath';\""
docker restart rdtclient
```

---

### Could Not Find File from Rclone Mount
**Error:** `Could not find file from rclone mount!`

**Cause:** RDTClient searches specific paths but AllDebrid stores files in subfolders (`magnets/`, `history/`, `links/`).

**Solution:** Use rclone union remote to merge folders. See [Rclone Union Mount](#rclone-union-mount-for-alldebrid).

---

### Downloads Stuck / One File at a Time
**Cause:** `Provider:MaxParallelDownloads` set to 0.

**Solution:**
```bash
# Update parallel downloads setting
docker run --rm -v ./rdtclient:/db alpine sh -c \
  "apk add --quiet sqlite && sqlite3 /db/rdtclient.db \
  \"UPDATE Settings SET Value='8' WHERE SettingId='Provider:MaxParallelDownloads';\""
docker restart rdtclient
```

---

## Rclone Mount Issues

### Rclone Union Mount for AllDebrid
AllDebrid stores files in multiple folders:
- `magnets/` - torrent/magnet downloads
- `history/` - completed/older items
- `links/` - direct file links

**Solution:** Create a union remote that combines these folders.

**rclone.conf:**
```conf
[alldebrid]
type = webdav
url = https://webdav.debrid.it/
vendor = other
user = YOUR_API_KEY
pass = YOUR_ENCRYPTED_PASS

[alldebrid-union]
type = union
upstreams = alldebrid:magnets alldebrid:history
```

**compose.yml:**
```yaml
rclone:
  command: >
    mount alldebrid-union:
    /data
    --config=/config/rclone/rclone.conf
    # ... other options
```

---

### Stale FUSE Mount After Rclone Restart
**Issue:** Containers have stale mount references after rclone restarts, causing "Transport endpoint is not connected" errors.

**Solution:** Always restart dependent containers after rclone:
```bash
/path/to/scripts/restart-rclone.sh
```

Or manually:
```bash
docker compose restart rclone
sleep 5
docker compose restart jellyfin rdtclient radarr sonarr
```

---

### Broken Symlinks After Mount Path Change
**Issue:** Symlinks point to old path (e.g., `/data/alldebrid/magnets/...`) after changing to union mount.

**Solution:**
1. Delete broken symlinks:
   ```bash
   rm -rf /data/symlinks/radarr/*
   rm -rf /data/symlinks/sonarr/*
   ```
2. Delete and re-add torrents in RDTClient
3. New symlinks will use correct paths

---

## Jellyfin Issues

### Infuse Compatibility Issues (10.11.x)
**Issue:** Jellyfin 10.11.x has known issues with Infuse:
- Resume position stuck at 10:00 mark
- Playback errors
- Content-Length mismatch errors

**Solution:** Downgrade to Jellyfin 10.10.7:

1. Stop and backup:
   ```bash
   docker stop jellyfin
   mv ./jellyfin ./jellyfin-backup
   mkdir ./jellyfin
   ```

2. Update compose.yml:
   ```yaml
   jellyfin:
     image: lscr.io/linuxserver/jellyfin:10.10.7
   ```

3. Recreate container:
   ```bash
   docker compose up -d jellyfin
   ```

**Note:** Downgrading requires fresh config - database schemas are incompatible.

---

### Playback Errors / Streaming Issues
**Error:** `Response Content-Length mismatch: too few bytes written`

**Causes:**
- Broken symlinks
- Stale rclone mount
- Rclone cache not warmed up

**Solution:**
1. Restart the full stack:
   ```bash
   /path/to/scripts/restart-rclone.sh
   ```
2. Verify symlinks are valid:
   ```bash
   # Check if symlink target exists
   readlink -f /data/symlinks/movies/*/
   ```

---

### Invalid Password After Fresh Install
**Issue:** Login prompt appears instead of setup wizard after wiping config.

**Solution:** Complete container removal and recreation:
```bash
docker stop jellyfin
docker rm jellyfin
rm -rf ./jellyfin
mkdir ./jellyfin
docker compose up -d jellyfin
```

Clear browser cache or use incognito window.

---

## Jellyseerr Issues

### Undefined Hostname Error
**Error:** `"hostname":"http://undefined:undefinedundefined"`

**Cause:** Corrupted configuration.

**Solution:** Full reset:
```bash
docker stop jellyseerr
docker run --rm -v ./jellyseerr:/config alpine sh -c "rm -rf /config/*"
docker start jellyseerr
```

---

## General Tips

### Restart Order Matters
When restarting services, always restart rclone first:
1. rclone (FUSE mount)
2. Wait 5 seconds for mount to be ready
3. All dependent services (jellyfin, rdtclient, radarr, sonarr)

### Check Container Logs
```bash
# Recent logs
docker logs <container> --tail 50

# Follow logs
docker logs <container> -f

# Logs since specific time
docker logs <container> --since 5m
```

### Verify Mounts from Inside Container
```bash
# Check if container can access rclone mount
docker exec jellyfin ls /data/alldebrid/
docker exec rdtclient ls /data/alldebrid/
```

### SQLite Database Access for RDTClient
```bash
# View all settings
docker run --rm -v ./rdtclient:/db alpine sh -c \
  "apk add --quiet sqlite && sqlite3 /db/rdtclient.db 'SELECT * FROM Settings;'"
```

### UPnP - Don't Enable
UPnP automatic port mapping is a security risk. Use Tailscale/VPN for remote access instead.
