#!/bin/bash

# Start all services in the home server

set -e

# Source common configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/common.sh"

echo "Starting all home server services..."

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
        echo "Starting $service_name..."
        cd "$service"
        docker compose up -d
    fi
done

echo ""
echo "All services started!"
echo "Run 'docker ps' to see running containers"
