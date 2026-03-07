# Getting Started

A step-by-step guide to deploying the home server stack.

## Prerequisites

- **OS**: Ubuntu 22.04+ (or similar Linux distribution)
- **Docker**: Docker Engine 24+ and Docker Compose v2
- **RAM**: 8 GB minimum (16 GB recommended if running Immich ML)
- **Storage**: 100 GB minimum (500 GB+ recommended if using Immich)
- **CPU**: Intel CPU with integrated GPU recommended (for Jellyfin hardware transcoding)

## Clone and Configure

```bash
git clone https://github.com/sudharsanmaran/home_server.git
cd home_server
cp services/media/.env.example services/media/.env
cp services/immich/.env.example services/immich/.env
cp services/tailscale/.env.example services/tailscale/.env
cp services/media/rclone/rclone.conf.example services/media/rclone/rclone.conf
```

Edit each `.env` file and `rclone.conf` with your values before starting any services.

## Service Startup Order

Services must start in dependency order. Each step should be verified before moving to the next.

| Step | Service Group | Command | Verify |
|------|--------------|---------|--------|
| 1 | Tailscale (VPN/networking foundation) | `docker compose -f services/tailscale/compose.yml up -d` | `docker exec tailscale tailscale status` |
| 2 | DNS (AdGuard + Unbound) | `docker compose -f services/dns/compose.yml up -d` | http://\<server-ip\>:3001 |
| 3 | Management (Caddy, Portainer, Glances) | `docker compose -f services/management/compose.yml up -d` | http://\<server-ip\>:9000 |
| 4 | Media (full stack) | `docker compose -f services/media/compose.yml up -d` | http://\<server-ip\>:8096 |
| 5 | Immich (photo management) | `docker compose -f services/immich/compose.yml up -d` | http://\<server-ip\>:2283 |

Or start everything at once:

```bash
./scripts/start-all.sh
```

## Accessing Services via Caddy

Once the management stack is running, Caddy reverse-proxies all services at `http://<name>.home-server`:

- `jellyfin.home-server`
- `radarr.home-server`
- `sonarr.home-server`
- `prowlarr.home-server`
- `bazarr.home-server`
- `seerr.home-server`
- `rdtclient.home-server`
- `jellystat.home-server`
- `portainer.home-server`
- `glances.home-server`
- `immich.home-server`
- `adguard.home-server`
- `shelfmark.home-server`
- `audiobookshelf.home-server`

This requires DNS resolution of `*.home-server` to your server IP. Configure this in AdGuard Home (DNS rewrites) or your local DNS server.

## Boot Recovery

A systemd unit is provided to automatically restart all services on boot.

```bash
sudo cp homeserver-recovery.service /etc/systemd/system/
sudo systemctl enable homeserver-recovery
```

This runs `scripts/restart-all.sh` on startup, which brings up all compose stacks in the correct order.

## Maintenance

| Task | Command |
|------|---------|
| Update all containers | `./scripts/update-all.sh` |
| Backup | `./scripts/backup.sh` |
| Restart rclone mount | `./scripts/restart-rclone.sh` |
| Stop everything | `./scripts/stop-all.sh` |
| Restart everything | `./scripts/restart-all.sh` |

## Next Steps

1. **Configure each service** via its web UI (Radarr, Sonarr, Prowlarr, etc.)
2. **Set up Tailscale** on your other devices to access services remotely
3. **Configure AdGuard filtering** -- add blocklists and DNS rewrites for `*.home-server`
4. **Set up the Immich mobile app** and enable automatic photo backup
5. **Review per-service READMEs** in each `services/` subdirectory for detailed configuration
