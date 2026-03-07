#!/bin/bash
# Restart all home server services after a reboot
# Usage: sudo ./restart-all.sh
#
# This script brings up all docker compose stacks cleanly,
# removing orphaned containers to prevent "name is reserved" errors.

set -e

SERVICES_DIR="/data/code/home_server/services"

# Order matters: tailscale first (networking), then dns, then management, then media, then immich
STACKS=(tailscale dns management media immich)

echo "=== Home Server Recovery ==="

for stack in "${STACKS[@]}"; do
    dir="$SERVICES_DIR/$stack"
    if [ -f "$dir/compose.yml" ] || [ -f "$dir/docker-compose.yml" ]; then
        echo ""
        echo "--- Starting: $stack ---"
        cd "$dir"
        docker compose down --remove-orphans 2>/dev/null || true
        docker compose up -d --remove-orphans
        echo "--- $stack: UP ---"
    else
        echo "--- Skipping $stack (no compose file) ---"
    fi
done

echo ""
echo "=== All stacks started. Checking health... ==="
sleep 10
docker ps -a --format "table {{.Names}}\t{{.Status}}" | sort
