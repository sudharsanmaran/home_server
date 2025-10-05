# Migration Guide: media-server → home_server

This guide helps you migrate from the old `media-server` repo to the new `home_server` structure.

## What Changed

**Old structure:**
```
/data/code/media-server/
├── compose.yml
├── config/
├── radarr/
└── ...
```

**New structure:**
```
/data/code/home_server/
├── services/
│   └── media/
│       ├── compose.yml
│       ├── config/
│       ├── radarr/
│       └── ...
└── scripts/
```

## Migration Steps

### 1. Stop Current Services

```bash
cd /data/code/media-server
docker compose down
```

### 2. Copy Config Directories

```bash
# Clone the new repo
cd /data/code
git clone <your-repo-url> home_server

# Copy all config directories from old location to new
cp -r media-server/config home_server/services/media/
cp -r media-server/radarr home_server/services/media/
cp -r media-server/sonarr home_server/services/media/
cp -r media-server/prowlarr home_server/services/media/
cp -r media-server/rdtclient home_server/services/media/
cp -r media-server/jellyseerr home_server/services/media/
cp -r media-server/jellystat home_server/services/media/

# Copy environment file
cp media-server/.env home_server/services/media/.env
```

### 3. Start Services with New Setup

```bash
cd /data/code/home_server/services/media
docker compose up -d
```

### 4. Verify Everything Works

```bash
# Check all containers are running
docker ps

# Check logs for any errors
docker compose logs -f
```

Access your services:
- Jellyfin: http://localhost:8096
- Radarr: http://localhost:7878
- Sonarr: http://localhost:8989
- RDTClient: http://localhost:6500
- Prowlarr: http://localhost:9696

### 5. Clean Up Old Directory (Optional)

Once you've confirmed everything works:

```bash
# Backup first (just in case)
cd /data/code
tar -czf media-server-backup.tar.gz media-server/

# Remove old directory
rm -rf media-server/
```

## Rollback (If Needed)

If something goes wrong:

```bash
# Stop new services
cd /data/code/home_server/services/media
docker compose down

# Start old services
cd /data/code/media-server
docker compose up -d
```

## Notes

- **Media files** (`/data/media/`) are **not moved** - they stay in the same location
- **Downloads** (`/data/downloads/`) are **not moved** - they stay in the same location
- Only **config directories** are copied to the new structure
- The new setup uses the same Docker images and ports
- All your existing configurations will work exactly the same

## Benefits of New Structure

- **Better organization**: Services grouped under `services/`
- **Scalability**: Easy to add more services (netbird, immich, nextcloud)
- **Centralized management**: Scripts to manage all services at once
- **Future-proof**: Designed for a complete home server setup
