#!/bin/bash

# Update all services by pulling latest images and recreating containers

set -e

# Source common configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

echo "Updating all home server services..."

SERVICES_DIR="$(cd "$(dirname "$0")/../services" && pwd)"

for service in "$SERVICES_DIR"/*/ ; do
    if [ -d "$service" ] && [ -f "$service/compose.yml" ]; then
        service_name=$(basename "$service")

        # Check if service is in blocklist
        if [[ " ${BLOCKLIST[@]} " =~ " ${service_name} " ]]; then
            echo ""
            echo "Skipping $service_name (not yet developed)..."
            continue
        fi

        echo ""
        echo "Updating $service_name..."
        cd "$service"
        docker compose pull
        docker compose up -d
    fi
done

echo ""
echo "All services updated!"
echo ""
echo "Cleaning up old images..."
docker image prune -f

echo "Done!"
