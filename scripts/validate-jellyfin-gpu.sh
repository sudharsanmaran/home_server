#!/bin/bash
# GPU Validation Script for Jellyfin
# This script tests if hardware acceleration will work before enabling it

set -e

echo "=== Jellyfin GPU Validation ==="
echo ""

# Check if GPU devices exist
echo "[1/4] Checking GPU devices..."
if [ ! -e /dev/dri/renderD128 ]; then
    echo "❌ ERROR: /dev/dri/renderD128 not found"
    echo "   Hardware acceleration cannot be enabled"
    exit 1
fi
echo "✅ GPU devices found"
echo ""

# Check if Jellyfin container is running
echo "[2/4] Checking Jellyfin container..."
if ! docker ps --format '{{.Names}}' | grep -q "^jellyfin$"; then
    echo "❌ ERROR: Jellyfin container is not running"
    echo "   Start it with: cd /data/code/home_server/services/media && docker compose up -d jellyfin"
    exit 1
fi
echo "✅ Jellyfin container is running"
echo ""

# Check if GPU is accessible in container
echo "[3/4] Checking GPU access in container..."
if ! docker exec jellyfin test -e /dev/dri/renderD128; then
    echo "❌ ERROR: GPU not accessible in container"
    echo "   Check docker compose configuration"
    exit 1
fi
echo "✅ GPU accessible in container"
echo ""

# Test ffmpeg with GPU
echo "[4/4] Testing ffmpeg with GPU (30s timeout)..."
timeout 30s docker exec jellyfin ffmpeg -hide_banner \
    -hwaccel vaapi \
    -hwaccel_device /dev/dri/renderD128 \
    -hwaccel_output_format vaapi \
    -f lavfi -i testsrc=duration=1:size=1920x1080:rate=1 \
    -vf 'format=nv12,hwupload' \
    -c:v h264_vaapi \
    -t 1 -f null - 2>&1 | tee /tmp/vaapi-test.log

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS: Hardware acceleration is working!"
    echo ""
    echo "You can safely enable VA-API in Jellyfin:"
    echo "  Dashboard → Playback → Hardware Acceleration"
    echo "  Select 'Video Acceleration API (VA-API)'"
    exit 0
else
    echo ""
    echo "❌ FAILED: Hardware acceleration test failed or timed out"
    echo ""
    echo "See errors above. Common issues:"
    echo "  1. AMD GPU drivers not properly installed on host"
    echo "  2. VA-API libraries missing in container"
    echo "  3. GPU not supported for video encoding"
    echo ""
    echo "Recommendation: Keep hardware acceleration disabled"
    echo "  Jellyfin will work fine with CPU transcoding"
    exit 1
fi
