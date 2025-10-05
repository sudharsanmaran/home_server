# Home Server

Self-hosted home server infrastructure running multiple services in Docker containers.

## Services

### Media Server
Automated media streaming and management stack with Jellyfin, Radarr, Sonarr, and AllDebrid integration.

**Location**: `services/media/`
**Documentation**: [Media Server README](services/media/readme.md)
**Ports**: 8096 (Jellyfin), 7878 (Radarr), 8989 (Sonarr), 6500 (RDTClient), 9696 (Prowlarr)

### Planned Services
- **Netbird**: VPN mesh network
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
│   └── media/              # Media streaming stack
├── scripts/                # Utility scripts
├── .env                    # Shared environment variables
└── README.md              # This file
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
