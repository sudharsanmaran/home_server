# Management Services

Reverse proxy, Docker management, and system monitoring.

## Services

### Caddy

Reverse proxy that routes `*.home-server` domains to the appropriate service. No HTTPS (local network only).

- **Image**: `caddy:latest`
- **HTTP**: port 80
- **Config**: `caddy/Caddyfile`

All routing rules are defined in the Caddyfile. To add a new service, append a block like:

```
http://myservice.home-server {
    reverse_proxy localhost:<port>
}
```

Then reload: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`

### Portainer

Web-based Docker management UI.

- **Image**: `portainer/portainer-ce:latest`
- **HTTP**: http://server-ip:9000
- **HTTPS**: https://server-ip:9443

### Glances

Real-time system monitoring (CPU, memory, disk, network, containers).

- **Image**: `nicolargo/glances:latest`
- **HTTP**: http://server-ip:29999

## Setup

1. Start the services:
   ```bash
   cd services/management
   docker compose up -d
   ```

2. Access Portainer at `http://<server-ip>:9000`

3. Create admin account on first visit

4. Access Glances at `http://<server-ip>:29999`

## Management Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f portainer
docker compose logs -f caddy
docker compose logs -f glances

# Update all
docker compose pull && docker compose up -d

# Reload Caddy config without restart
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```
