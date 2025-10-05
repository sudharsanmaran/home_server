#!/bin/bash

# Backup all service configurations (not media files)

set -e

BACKUP_DIR="$(cd "$(dirname "$0")/.." && pwd)/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/home_server_backup_$TIMESTAMP.tar.gz"

echo "Creating backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Change to repo root
cd "$(dirname "$0")/.."

# Create backup excluding media files and container data
tar -czf "$BACKUP_FILE" \
    --exclude='backups' \
    --exclude='services/*/data' \
    --exclude='services/*/downloads' \
    --exclude='services/*/config/cache' \
    --exclude='services/*/config/logs' \
    --exclude='.git' \
    .env \
    services/ \
    scripts/ \
    README.md

echo ""
echo "Backup created: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
echo "To restore: tar -xzf $BACKUP_FILE"
