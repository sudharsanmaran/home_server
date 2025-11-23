# Management Services

Docker management and monitoring tools.

## Services

### Portainer

Web-based Docker management UI.

- **Image**: `portainer/portainer-ce:latest`
- **HTTP**: http://server-ip:9000
- **HTTPS**: https://server-ip:9443

## Setup

1. Start the services:
   ```bash
   cd /data/code/home_server/services/management
   docker compose up -d
   ```

2. Access Portainer at `http://<server-ip>:9000`

3. Create admin account on first visit

## Management Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f portainer

# Update Portainer
docker compose pull && docker compose up -d
```
