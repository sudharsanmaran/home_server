#!/bin/bash

# Stop all services in the home server

set -e

echo "Stopping all home server services..."

SERVICES_DIR="$(cd "$(dirname "$0")/../services" && pwd)"

for service in "$SERVICES_DIR"/*/ ; do
    if [ -d "$service" ] && [ -f "$service/compose.yml" ]; then
        service_name=$(basename "$service")
        echo ""
        echo "Stopping $service_name..."
        cd "$service"
        docker compose down
    fi
done

echo ""
echo "All services stopped!"
