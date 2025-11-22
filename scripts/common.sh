#!/bin/bash

# Common configuration for home server scripts
# This file is sourced by start-all.sh, stop-all.sh, and update-all.sh

# Blocklist of services to skip (not yet developed or disabled)
BLOCKLIST=(
    "netbird"
    "nginx-proxy-manager"
)
