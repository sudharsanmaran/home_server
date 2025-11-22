#!/bin/bash

# Immich GPU Setup Script
# This script configures Intel iGPU access for hardware acceleration

set -e

echo "=========================================="
echo "Immich GPU Hardware Acceleration Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root${NC}"
    echo "Run it as your regular user, it will prompt for sudo password when needed"
    exit 1
fi

echo "Step 1: Checking GPU availability..."
if [ ! -d "/dev/dri" ]; then
    echo -e "${RED}ERROR: /dev/dri not found. No GPU detected.${NC}"
    exit 1
fi

ls -la /dev/dri
echo -e "${GREEN}✓ GPU devices found${NC}"
echo ""

echo "Step 2: Checking current user groups..."
CURRENT_GROUPS=$(groups)
echo "Current groups: $CURRENT_GROUPS"

NEEDS_RENDER=false
NEEDS_VIDEO=false

if ! groups | grep -q "render"; then
    echo -e "${YELLOW}! User not in 'render' group${NC}"
    NEEDS_RENDER=true
fi

if ! groups | grep -q "video"; then
    echo -e "${YELLOW}! User not in 'video' group${NC}"
    NEEDS_VIDEO=true
fi

if [ "$NEEDS_RENDER" = true ] || [ "$NEEDS_VIDEO" = true ]; then
    echo ""
    echo "Adding user to required groups..."

    if [ "$NEEDS_RENDER" = true ]; then
        sudo usermod -aG render $USER
        echo -e "${GREEN}✓ Added to render group${NC}"
    fi

    if [ "$NEEDS_VIDEO" = true ]; then
        sudo usermod -aG video $USER
        echo -e "${GREEN}✓ Added to video group${NC}"
    fi

    echo ""
    echo -e "${YELLOW}IMPORTANT: Group changes require logout/login to take effect${NC}"
    echo "After running this script:"
    echo "  1. Logout and login again (or restart)"
    echo "  2. Verify with: groups"
    echo "  3. Then start Immich services"
else
    echo -e "${GREEN}✓ User already in render and video groups${NC}"
fi
echo ""

echo "Step 3: Checking VA-API drivers..."
if ! command -v vainfo &> /dev/null; then
    echo -e "${YELLOW}vainfo not found. Installing VA-API tools...${NC}"
    sudo apt update
    sudo apt install -y vainfo intel-media-va-driver-non-free libva-drm2
    echo -e "${GREEN}✓ VA-API tools installed${NC}"
else
    echo -e "${GREEN}✓ vainfo already installed${NC}"
fi
echo ""

echo "Step 4: Testing VA-API..."
if vainfo &> /dev/null; then
    echo -e "${GREEN}✓ VA-API is working${NC}"
    echo ""
    echo "Supported codecs:"
    vainfo 2>&1 | grep -i "VAProfile" | head -10
else
    echo -e "${YELLOW}! VA-API test failed. This might work after logout/login${NC}"
fi
echo ""

echo "Step 5: Checking Intel GPU monitoring tools..."
if ! command -v intel_gpu_top &> /dev/null; then
    echo -e "${YELLOW}intel_gpu_top not found. Installing...${NC}"
    sudo apt install -y intel-gpu-tools
    echo -e "${GREEN}✓ intel_gpu_tools installed${NC}"
else
    echo -e "${GREEN}✓ intel_gpu_top already available${NC}"
fi
echo ""

echo "=========================================="
echo "Setup Summary"
echo "=========================================="
echo ""
echo "GPU Configuration: ${GREEN}COMPLETE${NC}"
echo ""
echo "Next Steps:"
echo "  1. If you were added to groups, LOGOUT and LOGIN again"
echo "  2. Verify groups: groups | grep -E 'render|video'"
echo "  3. Start Immich: cd /data/code/home_server/services/immich && docker compose up -d"
echo "  4. Monitor GPU usage: watch -n 1 intel_gpu_top"
echo ""
echo "Verification Commands:"
echo "  • Check groups: groups"
echo "  • Check VA-API: vainfo"
echo "  • GPU in container: docker exec immich-server vainfo"
echo "  • GPU usage: intel_gpu_top"
echo ""
echo "For more details, see: /data/code/home_server/services/immich/README.md"
echo ""
