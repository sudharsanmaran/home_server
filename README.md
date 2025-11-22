# Home Server

Self-hosted home server infrastructure running multiple services in Docker containers with secure remote access via Tailscale VPN.

## Services

### Media Server
Automated media streaming and management stack with Jellyfin, Radarr, Sonarr, and AllDebrid cloud integration.

**Location**: `services/media/`
**Documentation**: [Media Server README](services/media/README.md)
**Key Ports**: 8096 (Jellyfin), 7878 (Radarr), 8989 (Sonarr), 5055 (Jellyseerr), 9696 (Prowlarr)

Features:
- Jellyfin media server with hardware transcoding
- Radarr/Sonarr for automated movie/TV management
- AllDebrid integration via rclone mount
- Prowlarr indexer management (through VPN)
- Jellyseerr for media requests
- Jellystat for analytics
- Automated MKV to MP4 conversion

### Immich
Self-hosted Google Photos alternative with AI-powered features.

**Location**: `services/immich/`
**Documentation**: [Immich README](services/immich/README.md)
**Port**: 2283

Features:
- Photo and video backup
- Face recognition and object detection
- Semantic search
- Hardware-accelerated transcoding

### Tailscale VPN
Secure remote access to all services via mesh VPN.

**Location**: `services/tailscale/`
**Documentation**: [Tailscale README](services/tailscale/README.md)

## Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 8GB RAM (16GB recommended for Immich ML)
- 100GB+ storage space
- Intel GPU for hardware transcoding (optional)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/home_server.git
   cd home_server
   ```

2. **Configure environment variables**
   ```bash
   # Copy example env files
   cp services/media/.env.example services/media/.env
   cp services/immich/.env.example services/immich/.env

   # Edit with your values
   nano services/media/.env
   nano services/immich/.env
   ```

3. **Configure rclone (for AllDebrid)**
   ```bash
   cp services/media/rclone/rclone.conf.example services/media/rclone/rclone.conf
   # Edit with your AllDebrid credentials
   nano services/media/rclone/rclone.conf
   ```

4. **Start all services**
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

### Stop All Services
```bash
./scripts/stop-all.sh
```

## Structure

```
home_server/
├── services/
│   ├── media/                   # Media streaming stack
│   │   ├── compose.yml          # Docker compose configuration
│   │   ├── .env.example         # Environment template
│   │   └── rclone/              # Rclone configuration for AllDebrid
│   ├── immich/                  # Photo management
│   │   ├── compose.yml
│   │   └── .env.example
│   └── tailscale/               # VPN service
│       └── compose.yml
├── scripts/
│   ├── start-all.sh             # Start all services
│   ├── stop-all.sh              # Stop all services
│   ├── update-all.sh            # Update all services
│   ├── backup.sh                # Backup configurations
│   ├── restart-rclone.sh        # Restart rclone mount
│   ├── validate-jellyfin-gpu.sh # Validate GPU transcoding
│   └── media-conversion/        # MKV to MP4 conversion tools
└── README.md
```

## Configuration

### Environment Variables

Each service has its own `.env.example` file. Copy it to `.env` and configure:

| Service | Config File | Key Variables |
|---------|-------------|---------------|
| Media | `services/media/.env` | ALLDEBRID_API_KEY, SURFSHARK_PRIVATE_KEY, POSTGRES_PASSWORD |
| Immich | `services/immich/.env` | DB_PASSWORD, UPLOAD_LOCATION |
| Tailscale | `services/tailscale/.env` | TS_AUTHKEY |

### AllDebrid Setup

1. Get your API key from [AllDebrid](https://alldebrid.com/apikeys/)
2. Add to `services/media/.env`
3. Configure rclone with your credentials

### VPN for Prowlarr

Prowlarr runs through a Surfshark VPN container for privacy:
1. Get WireGuard credentials from [Surfshark](https://my.surfshark.com/vpn/manual-setup/main/wireguard)
2. Add to `services/media/.env`

## Security

- **Never commit `.env` files** - they contain secrets
- Change all default passwords before first use
- Use Tailscale for secure remote access
- Keep services updated regularly
- Backup configurations frequently

## Troubleshooting

### Rclone Mount Issues
```bash
# Restart rclone and dependent services
./scripts/restart-rclone.sh
```

### GPU Transcoding
```bash
# Validate Jellyfin GPU access
./scripts/validate-jellyfin-gpu.sh
```

### Container Issues
```bash
# Kill stuck containers
./scripts/kill-stuck-container.sh <container_name>
```

## License

MIT License - See individual service licenses for third-party components.
