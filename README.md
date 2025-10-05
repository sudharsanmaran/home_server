# Home Server

Self-hosted home server infrastructure running multiple services in Docker containers with free SSL certificates and secure remote access.

## Getting Started

**New to this repo?** Start here:
1. [Deployment Guide](DEPLOYMENT.md) - Complete step-by-step setup
2. [DuckDNS Setup](DUCKDNS_SETUP.md) - Free domain configuration
3. [Migration Guide](MIGRATION.md) - Moving from old media-server repo

**Quick deploy:**
```bash
# Create Docker network
docker network create home_server_network

# Deploy Nginx Proxy Manager
cd services/nginx-proxy-manager && docker compose up -d

# Deploy Netbird VPN
cd ../netbird && docker compose up -d

# Deploy Media Server
cd ../media && docker compose up -d
```

## Services

### Nginx Proxy Manager
Reverse proxy with SSL certificate management for clean URLs and HTTPS access.

**Location**: `services/nginx-proxy-manager/`
**Documentation**: [NPM README](services/nginx-proxy-manager/README.md)
**Ports**: 80 (HTTP), 443 (HTTPS), 81 (Admin UI)
**Purpose**: SSL termination, reverse proxy, Let's Encrypt certificates

### Netbird VPN
Self-hosted WireGuard-based mesh VPN for secure remote access.

**Location**: `services/netbird/`
**Documentation**: [Netbird README](services/netbird/README.md)
**Ports**: 3478/udp (STUN), 49152-65535/udp (TURN)
**Purpose**: Secure remote access, peer-to-peer VPN

### Media Server
Automated media streaming and management stack with Jellyfin, Radarr, Sonarr, and AllDebrid integration.

**Location**: `services/media/`
**Documentation**: [Media Server README](services/media/readme.md)
**Ports**: 8096 (Jellyfin), 7878 (Radarr), 8989 (Sonarr), 6500 (RDTClient), 9696 (Prowlarr)

### Planned Services
- **Immich**: Photo management and backup
- **Nextcloud**: File sync and collaboration

## Quick Start

### Start All Services
```bash
./scripts/start-all.sh
```

### Start Individual Service
```bash
cd services/media
docker compose up -d
```

### Update All Services
```bash
./scripts/update-all.sh
```

### Backup Configuration
```bash
./scripts/backup.sh
```

## Structure

```
home_server/
├── services/
│   ├── nginx-proxy-manager/  # Reverse proxy + SSL
│   ├── netbird/              # VPN mesh network
│   └── media/                # Media streaming stack
├── scripts/                  # Utility scripts
├── DEPLOYMENT.md             # Full deployment guide
├── DUCKDNS_SETUP.md          # DuckDNS configuration
├── MIGRATION.md              # Migration from old setup
├── .env                      # Shared environment variables
└── README.md                 # This file
```

## Requirements

- Docker Desktop
- At least 8GB RAM
- 100GB+ storage space
- Stable internet connection

## Environment Variables

Shared environment variables are in `.env` at the root level. Each service can also have its own `.env` file for service-specific configuration.

## Management

Each service is independent and can be managed separately:
- Start: `cd services/<service> && docker compose up -d`
- Stop: `cd services/<service> && docker compose down`
- Logs: `cd services/<service> && docker compose logs -f`
- Update: `cd services/<service> && docker compose pull && docker compose up -d`

## Security

- Change default passwords in environment files
- Use firewall rules to restrict external access
- Keep services updated regularly
- Backup configurations frequently
