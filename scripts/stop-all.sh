#!/bin/bash

# Stop all services in the home server

set -e

# Source common configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

echo "Stopping all home server services..."

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
        echo "Stopping $service_name..."
        cd "$service"
        docker compose down
    fi
done

echo ""
echo "All services stopped!"
