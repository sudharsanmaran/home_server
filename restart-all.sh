#!/bin/bash
# Restart all home server services after a reboot
# Usage: sudo ./restart-all.sh
#
# This script brings up all docker compose stacks cleanly,
# removing orphaned containers to prevent "name is reserved" errors.
#
# Priority stacks start first (in order), then any remaining stacks
# are auto-discovered and started. Adding a new services/<name>/compose.yml
# directory is all you need — no script changes required.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICES_DIR="$SCRIPT_DIR/services"

# Priority order: these start first, in this exact sequence
# - tailscale: networking must be up first
# - dns: AdGuard + Unbound must be up before anything needs DNS
# - management: Caddy reverse proxy, portainer, glances
PRIORITY_STACKS=(tailscale dns management)

echo "=== Home Server Recovery ==="

# Track what we've started
declare -A started

# Start priority stacks in order
for stack in "${PRIORITY_STACKS[@]}"; do
    dir="$SERVICES_DIR/$stack"
    if [ -f "$dir/compose.yml" ] || [ -f "$dir/docker-compose.yml" ]; then
        echo ""
        echo "--- Starting: $stack (priority) ---"
        cd "$dir"
        docker compose down --remove-orphans 2>/dev/null || true
        docker compose up -d --remove-orphans
        echo "--- $stack: UP ---"
        started[$stack]=1
    fi
done

# Auto-discover and start remaining stacks
for dir in "$SERVICES_DIR"/*/; do
    [ -d "$dir" ] || continue
    stack=$(basename "$dir")

    # Skip if already started as priority
    [ "${started[$stack]}" = "1" ] && continue

    if [ -f "$dir/compose.yml" ] || [ -f "$dir/docker-compose.yml" ]; then
        echo ""
        echo "--- Starting: $stack ---"
        cd "$dir"
        docker compose down --remove-orphans 2>/dev/null || true
        docker compose up -d --remove-orphans
        echo "--- $stack: UP ---"
    fi
done

echo ""
echo "=== All stacks started. Checking health... ==="
sleep 10
docker ps -a --format "table {{.Names}}\t{{.Status}}" | sort
