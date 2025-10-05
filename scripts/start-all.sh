#!/bin/bash

# Start all services in the home server

set -e

echo "Starting all home server services..."

SERVICES_DIR="$(cd "$(dirname "$0")/../services" && pwd)"

for service in "$SERVICES_DIR"/*/ ; do
    if [ -d "$service" ] && [ -f "$service/compose.yml" ]; then
        service_name=$(basename "$service")
        echo ""
        echo "Starting $service_name..."
        cd "$service"
        docker compose up -d
    fi
done

echo ""
echo "All services started!"
echo "Run 'docker ps' to see running containers"
