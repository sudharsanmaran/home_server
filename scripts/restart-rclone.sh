#!/bin/bash

# Restart rclone and all dependent services
# This is necessary because when rclone remounts, containers with stale mount references need to restart

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MEDIA_DIR="$PROJECT_ROOT/services/media"

echo "==========================================="
echo "Restarting rclone and dependent services"
echo "==========================================="
echo ""

cd "$MEDIA_DIR"

# Restart rclone first
echo "📦 Restarting rclone..."
docker compose restart rclone

# Wait for rclone to be ready
echo "⏳ Waiting for rclone mount to be ready..."
sleep 5

# Check if mount is accessible
if docker exec rclone ls /data >/dev/null 2>&1; then
    echo "✅ Rclone mount is ready"
else
    echo "⚠️  Warning: rclone mount may not be ready yet"
fi

echo ""
echo "📦 Restarting dependent services..."

# Restart all services that depend on the rclone mount
docker compose restart \
    jellyfin \
    jellyfin-test \
    rdtclient-symlink \
    radarr \
    sonarr

echo ""
echo "✅ All services restarted successfully"
echo ""
echo "Services restarted:"
echo "  - rclone (FUSE mount for AllDebrid)"
echo "  - jellyfin (media server)"
echo "  - jellyfin-test (test instance)"
echo "  - rdtclient-symlink (symlink creator)"
echo "  - radarr (movie management)"
echo "  - sonarr (TV show management)"
echo ""
echo "==========================================="
