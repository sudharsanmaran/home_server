#!/bin/bash
# Radarr Custom Script Hook
# This script runs on the host and calls the converter inside the Docker container

MOVIE_PATH="$1"

if [ -z "$MOVIE_PATH" ]; then
    echo "Error: No movie path provided"
    echo "Usage: $0 <movie_file_path>"
    exit 1
fi

echo "==================================================================="
echo "Radarr Hook: Processing movie"
echo "==================================================================="
echo "File: $MOVIE_PATH"
echo "Container: media-converter"
echo ""

# Execute the conversion script inside the container
docker exec media-converter python3 /app/convert_mkv_to_mp4.py "$MOVIE_PATH"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ Conversion completed successfully"
else
    echo ""
    echo "✗ Conversion failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
