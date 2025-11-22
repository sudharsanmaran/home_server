#!/bin/bash

# Script to forcefully kill stuck Docker containers
# Usage: ./kill-stuck-container.sh <container_id_or_name>

if [ -z "$1" ]; then
    echo "Usage: $0 <container_id_or_name>"
    echo "Example: $0 jellyfin"
    exit 1
fi

CONTAINER=$1

# Check if container exists
if ! docker ps -a | grep -q "$CONTAINER"; then
    echo "Error: Container '$CONTAINER' not found"
    exit 1
fi

# Get full container ID
CONTAINER_ID=$(docker ps -a | grep "$CONTAINER" | awk '{print $1}' | head -1)

echo "=== Killing stuck container: $CONTAINER_ID ==="

# Get the main PID
MAIN_PID=$(docker inspect "$CONTAINER_ID" 2>/dev/null | grep '"Pid":' | head -1 | awk '{print $2}' | tr -d ',')

if [ -z "$MAIN_PID" ] || [ "$MAIN_PID" = "0" ]; then
    echo "Container has no running process, trying to remove directly..."
    docker rm -f "$CONTAINER_ID"
    exit $?
fi

echo "Main PID: $MAIN_PID"

# Find containerd-shim parent process
PARENT_PID=$(ps -o ppid= -p "$MAIN_PID" 2>/dev/null | tr -d ' ')
echo "Parent (containerd-shim) PID: $PARENT_PID"

# Find all child processes
CHILD_PIDS=$(pgrep -P "$MAIN_PID" 2>/dev/null | tr '\n' ' ')
echo "Child PIDs: $CHILD_PIDS"

# Collect all PIDs to kill
ALL_PIDS="$PARENT_PID $MAIN_PID $CHILD_PIDS"
echo ""
echo "=== Killing all processes ==="
echo "PIDs to kill: $ALL_PIDS"

# Kill all processes
for pid in $ALL_PIDS; do
    if [ ! -z "$pid" ]; then
        echo "Killing PID $pid..."
        sudo kill -9 "$pid" 2>/dev/null
    fi
done

# Wait a moment for processes to die
sleep 2

# Verify processes are dead
echo ""
echo "=== Verifying processes are dead ==="
for pid in $ALL_PIDS; do
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "WARNING: PID $pid is still alive!"
    else
        echo "PID $pid is dead ✓"
    fi
done

# Try to remove the container
echo ""
echo "=== Removing container ==="
if docker rm -f "$CONTAINER_ID"; then
    echo "✓ Container $CONTAINER_ID removed successfully"
else
    echo "✗ Failed to remove container. You may need to restart Docker daemon:"
    echo "  sudo systemctl restart docker"
    exit 1
fi
