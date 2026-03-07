# Home Server

Self-hosted home server infrastructure running multiple services in Docker containers with secure remote access via Tailscale VPN.

## Services

### DNS (AdGuard Home + Unbound)

Network-wide ad blocking and recursive DNS resolution.

**Location**: `services/dns/`
**Ports**: 53 (DNS), 3001 (AdGuard UI), 5335 (Unbound)

- AdGuard Home for DNS filtering and ad blocking
- Unbound as a recursive DNS resolver for privacy

### Media Server

Automated media streaming and management stack with AllDebrid cloud integration.

**Location**: `services/media/`
**Documentation**: [Media Server README](services/media/README.md)

| Sub-service | Port | Notes |
|-------------|------|-------|
| Jellyfin | 8096 | Media server with hardware transcoding |
| Radarr | 7878 | Movie management |
| Sonarr | 8989 | TV show management |
| Bazarr | 6767 | Subtitle management |
| Prowlarr | 9696 | Indexer management (via VPN) |
| Jellyseerr | 5055 | Media requests |
| Seerr | 5056 | Media requests (alternative) |
| RDTClient | 6500 | Real-Debrid torrent client |
| Jellystat | 3000 | Jellyfin analytics |
| Shelfmark | 8084 | Bookmarking (via VPN) |
| Audiobookshelf | 13378 | Audiobook/podcast server |
| Profilarr | 6868 | Profile management |
| Cleanuparr | 11011 | Automated cleanup |
| Huntarr | 9705 | Hunt for missing media |
| FlareSolverr | 8191 | CAPTCHA solver (via VPN) |
| Rclone | -- | Cloud mount for AllDebrid |
| VPN/Gluetun | -- | Surfshark WireGuard tunnel |

### Immich

Self-hosted photo management with AI-powered features.

**Location**: `services/immich/`
**Documentation**: [Immich README](services/immich/README.md)
**Port**: 2283

- Photo and video backup
- Face recognition and object detection
- Hardware-accelerated transcoding

### Management (Caddy + Portainer + Glances)

Reverse proxy, container management, and system monitoring.

**Location**: `services/management/`
**Ports**: 9000/9443 (Portainer), 29999 (Glances)

- Caddy as a reverse proxy
- Portainer for container management UI
- Glances for system monitoring

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
   git clone https://github.com/sudharsanmaran/home_server.git
   cd home_server
   ```

2. **Configure environment variables**
   ```bash
   cp services/media/.env.example services/media/.env
   cp services/immich/.env.example services/immich/.env
   cp services/tailscale/.env.example services/tailscale/.env

   # Edit each .env with your values
   ```

3. **Start all services**
   ```bash
   ./scripts/start-all.sh
   ```

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for the full setup guide.

## Structure

```
home_server/
├── services/
│   ├── dns/                     # AdGuard Home + Unbound
│   │   ├── compose.yml
│   │   ├── adguard/             # AdGuard config (gitignored)
│   │   └── unbound/             # Unbound config
│   ├── immich/                  # Photo management
│   │   ├── compose.yml
│   │   └── .env.example
│   ├── management/              # Caddy + Portainer + Glances
│   │   ├── compose.yml
│   │   └── caddy/Caddyfile
│   ├── media/                   # Media streaming stack
│   │   ├── compose.yml
│   │   ├── .env.example
│   │   └── rclone/             # Rclone config for AllDebrid
│   └── tailscale/              # VPN service
│       ├── compose.yml
│       └── .env.example
├── scripts/
│   ├── start-all.sh
│   ├── stop-all.sh
│   ├── update-all.sh
│   ├── restart-rclone.sh
│   ├── backup.sh
│   ├── kill-stuck-container.sh
│   ├── validate-jellyfin-gpu.sh
│   └── common.sh
├── docs/
│   └── GETTING_STARTED.md
├── restart-all.sh              # Boot recovery script
├── homeserver-recovery.service # Systemd service
└── README.md
```

## Configuration

### Environment Variables

Each service that requires configuration has a `.env.example` file. Copy it to `.env` and fill in your values.

| Service | Config File | Key Variables |
|---------|-------------|---------------|
| Media | `services/media/.env` | ALLDEBRID_API_KEY, SURFSHARK_PRIVATE_KEY, POSTGRES_PASSWORD, JWT_SECRET |
| Immich | `services/immich/.env` | DB_PASSWORD, UPLOAD_LOCATION |
| Tailscale | `services/tailscale/.env` | TS_AUTHKEY |
| DNS | No .env needed | TZ (default in compose) |
| Management | No .env needed | TZ (default in compose) |

### AllDebrid Setup

1. Get your API key from [AllDebrid](https://alldebrid.com/apikeys/)
2. Add to `services/media/.env`
3. Configure rclone with your credentials

### VPN for Prowlarr

Prowlarr runs through a Surfshark VPN container (Gluetun) for privacy:
1. Get WireGuard credentials from [Surfshark](https://my.surfshark.com/vpn/manual-setup/main/wireguard)
2. Add to `services/media/.env`

## Security

- **Never commit `.env` files** -- they contain secrets
- Change all default passwords before first use
- Use Tailscale for secure remote access
- Keep services updated regularly
- Backup configurations frequently

## Troubleshooting

### Rclone Mount Issues
```bash
./scripts/restart-rclone.sh
```

### GPU Transcoding
```bash
./scripts/validate-jellyfin-gpu.sh
```

### Container Issues
```bash
./scripts/kill-stuck-container.sh <container_name>
```

## License

MIT License -- See individual service licenses for third-party components.
