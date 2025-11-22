# Immich Photo Management Service

High-performance self-hosted photo and video management solution with AI-powered features.

## Overview

Immich is a modern, self-hosted alternative to Google Photos with:
- **AI-powered search** - Face detection, object recognition, CLIP semantic search
- **Hardware acceleration** - Intel Quick Sync for fast video transcoding
- **Mobile apps** - iOS and Android with automatic photo backup
- **High performance** - Redis caching, NVMe storage, GPU acceleration
- **External libraries** - Import existing photos without copying

## Architecture

### Services
- **immich-postgres** - PostgreSQL 16 with pgvecto.rs for vector search
- **immich-redis** - Redis cache for thumbnails and API responses
- **immich-server** - Main API server and web interface
- **immich-microservices** - Background jobs (thumbnails, video encoding)
- **immich-machine-learning** - AI models for face/object detection

### Storage Layout (All on NVMe for Maximum Performance)
```
/data/code/home_server/services/immich/
├── postgres/              # Database (~2-5GB)
├── redis/                 # Cache persistence (~500MB)
├── machine-learning/      # ML models cache (~1-2GB)
└── upload/                # Photo library (~500GB)
    ├── library/           # Original photos and videos
    ├── thumbs/            # Thumbnails (fast loading)
    ├── encoded-video/     # Web-optimized videos
    └── profile/           # User profile pictures
```

**Estimated Total:** 500-600GB for 300-400GB photo library

### Hardware Acceleration
- **iGPU**: Intel integrated GPU via `/dev/dri`
- **Video Encoding**: VA-API (H.264, HEVC)
- **ML Inference**: OpenVINO acceleration (optional)
- **Performance**: 3-5x faster video transcoding, 2-3x faster face detection

## Prerequisites

1. **GPU Drivers**
   ```bash
   # Check if iGPU is available
   ls -la /dev/dri

   # Install VA-API tools
   sudo apt update
   sudo apt install -y vainfo intel-media-va-driver-non-free

   # Verify hardware acceleration
   vainfo
   ```

2. **User Permissions**
   ```bash
   # Add user to render and video groups for GPU access
   sudo usermod -aG render $USER
   sudo usermod -aG video $USER

   # Logout and login for changes to take effect
   ```

3. **Disk Space**
   - Ensure at least 500GB free on `/data` NVMe

## Setup Instructions

### 1. Configure Environment Variables

Edit `.env` file:
```bash
cd /data/code/home_server/services/immich
nano .env
```

**Required changes:**
- `DB_PASSWORD` - Set a strong database password
- `IMMICH_SERVER_URL` - Update with your server IP or domain
- `TZ` - Verify timezone is correct

### 2. Create Data Directories

```bash
# Docker Compose will create these automatically, but you can pre-create them
mkdir -p postgres redis machine-learning upload
```

### 3. Start Services

```bash
# From the immich directory
docker compose up -d

# Or use the main control scripts
cd /data/code/home_server
./scripts/start-all.sh
```

### 4. Initial Setup

1. **Access Web Interface**
   - Open browser: `http://YOUR_SERVER_IP:2283`
   - Or use your configured domain

2. **Create Admin Account**
   - First user is automatically admin
   - Use a strong password

3. **Configure Settings**
   - Go to Administration > Settings
   - **Video Transcoding**: Select "VAAPI" for hardware acceleration
   - **Machine Learning**: Enable desired features
     - Facial recognition
     - Object detection
     - CLIP search
   - **Storage Template**: Customize organization (optional)

4. **Install Mobile Apps**
   - **iOS**: Download from App Store
   - **Android**: Download from Google Play
   - Configure server URL and login

## Configuration

### Hardware Acceleration

**Enable VA-API Transcoding:**
1. Web UI → Administration → Settings → Video Transcoding
2. Set **Target Resolution**: 1080p (or desired quality)
3. Set **Codec**: H.264 or HEVC
4. Set **Hardware Acceleration**: VAAPI
5. Set **CRF**: 23 (lower = better quality, higher size)

**Verify GPU Usage:**
```bash
# While transcoding/analyzing videos
watch -n 1 'intel_gpu_top'
```

### External Library Setup

To import existing photos without copying:

1. **Add Volume Mount** to `compose.yml`:
   ```yaml
   immich-server:
     volumes:
       - /path/to/existing/photos:/external/photos:ro
   ```

2. **Restart Services**:
   ```bash
   docker compose down && docker compose up -d
   ```

3. **Add External Library** in Web UI:
   - Settings → Libraries → Create External Library
   - Path: `/external/photos`
   - Import Strategy: Choose based on needs

### Machine Learning Performance

**GPU Acceleration** (OpenVINO):
- Automatically enabled when iGPU is available
- Check logs: `docker logs immich-machine-learning`
- Should see: "OpenVINO device: GPU"

**Model Downloads** (first run):
- Face detection: ~100MB
- CLIP: ~500MB
- Object detection: ~300MB
- Total: ~1-2GB in `/machine-learning/` cache

## Usage

### Uploading Photos

**Web Upload:**
- Drag and drop or click Upload button
- Supports bulk upload

**Mobile Auto-Backup:**
- Enable in mobile app settings
- Choose backup frequency and network (WiFi/cellular)

**CLI Upload** (bulk import):
```bash
# Using immich-cli (install separately)
npm i -g @immich/cli

# Login
immich login http://YOUR_SERVER_IP:2283

# Upload directory
immich upload /path/to/photos
```

### Search Features

- **Text Search**: "beach sunset", "birthday party"
- **Face Search**: Click detected faces
- **Object Search**: "car", "dog", "mountain"
- **Date/Location**: Timeline and map views
- **Smart Albums**: Auto-organized by content

### Sharing

- **Albums**: Create and share collections
- **Public Links**: Share individual photos/albums
- **Partner Sharing**: Share library with family

## Maintenance

### Backup Strategy

**Critical** (backup daily):
```bash
# Database backup
docker exec immich-postgres pg_dump -U postgres immich > immich-db-backup.sql
```

**Important** (backup weekly):
```bash
# Photo library
rsync -av /data/code/home_server/services/immich/upload/ /backup/immich-photos/
```

**Regenerable** (no backup needed):
- Thumbnails (will regenerate)
- Encoded videos (will regenerate)
- ML cache (will re-download models)

### Updates

```bash
# Pull latest images
cd /data/code/home_server/services/immich
docker compose pull

# Restart with new images
docker compose down && docker compose up -d

# Check logs
docker compose logs -f
```

### Monitoring

```bash
# Service status
docker compose ps

# Real-time logs
docker compose logs -f

# Check disk usage
du -sh /data/code/home_server/services/immich/*

# Database size
docker exec immich-postgres psql -U postgres -d immich -c "SELECT pg_size_pretty(pg_database_size('immich'));"
```

## Troubleshooting

### GPU Not Working

```bash
# Check device access
docker exec immich-server ls -la /dev/dri

# Check render group
docker exec immich-server id

# Verify VA-API inside container
docker exec immich-server vainfo
```

**Fix**: Ensure user in render/video groups, restart Docker daemon

### Slow Thumbnail Generation

1. Check GPU is being used: `intel_gpu_top`
2. Increase workers in Settings → Jobs
3. Monitor: `docker stats immich-microservices`

### Database Connection Errors

```bash
# Check database health
docker compose ps immich-postgres

# Check logs
docker logs immich-postgres

# Verify credentials in .env match
```

### Out of Disk Space

```bash
# Check usage
df -h /data

# Clear old thumbnails (will regenerate)
docker exec immich-server rm -rf /usr/src/app/upload/thumbs/*

# Restart microservices to regenerate
docker restart immich-microservices
```

### Machine Learning Not Working

```bash
# Check ML service logs
docker logs immich-machine-learning

# Verify models downloaded
ls -lh /data/code/home_server/services/immich/machine-learning/

# Test ML service health
docker exec immich-machine-learning curl http://localhost:3003/ping
```

## Performance Tips

1. **Use mobile app auto-backup** instead of web upload (more reliable)
2. **Enable Redis caching** (already configured)
3. **Use hardware transcoding** for videos (VA-API)
4. **Regular database maintenance**:
   ```bash
   docker exec immich-postgres vacuumdb -U postgres -d immich -z -v
   ```
5. **Monitor disk usage** and archive old photos to HDD if needed

## Security Recommendations

1. **Change default passwords** in `.env`
2. **Use Tailscale** for secure remote access
3. **Enable 2FA** in user settings (when accessing externally)
4. **Regular backups** of database
5. **Keep Immich updated** for security patches

## Advanced Configuration

### PostgreSQL Performance Tuning

For even better performance, edit `compose.yml` postgres command:
```yaml
command: >
  postgres
  -c shared_preload_libraries=vectors.so
  -c 'search_path="$$user", public, vectors'
  -c max_wal_size=2GB
  -c shared_buffers=1GB          # Increase for more RAM
  -c effective_cache_size=4GB    # Set to ~50% of system RAM
  -c random_page_cost=1.1        # Optimized for NVMe SSD
```

### Redis Memory Limit

If using Redis for many thumbnails:
```yaml
command: >
  redis-server
  --maxmemory 2gb
  --maxmemory-policy allkeys-lru
```

## Resources

- **Official Docs**: https://immich.app/docs
- **GitHub**: https://github.com/immich-app/immich
- **Discord**: https://discord.immich.app
- **Mobile Apps**: https://immich.app/docs/install/mobile

## Port Reference

- **2283** - Immich web interface and API
- **5432** - PostgreSQL (internal only)
- **6379** - Redis (internal only)
- **3003** - Machine Learning service (internal only)
