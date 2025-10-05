# Tailscale VPN Service

Tailscale provides secure remote access to your home server from anywhere.

## Setup

1. **Create state directory:**
   ```bash
   mkdir -p /data/code/home_server/services/tailscale/state
   ```

2. **(Optional) Get auth key:**
   - Visit https://login.tailscale.com/admin/settings/keys
   - Generate a new auth key
   - Add it to your `.env` file: `TS_AUTHKEY=tskey-auth-xxxxx`

3. **Start the service:**
   ```bash
   docker compose -f services/tailscale/compose.yml up -d
   ```

4. **Authenticate (if not using auth key):**
   ```bash
   docker exec tailscale tailscale up
   ```
   Then follow the link to authenticate.

## Usage

### Check status:
```bash
docker exec tailscale tailscale status
```

### Get Tailscale IP:
```bash
docker exec tailscale tailscale ip -4
```

### Access your services:
Once connected to Tailscale, you can access:
- Nginx Proxy Manager: `http://<tailscale-ip>:81`
- Other services on your home server using the Tailscale IP

### Enable exit node (optional):
To use your home server as an exit node:
1. Uncomment the `TS_EXTRA_ARGS` line in `compose.yml`
2. Restart: `docker compose -f services/tailscale/compose.yml restart`
3. Enable in Tailscale admin: https://login.tailscale.com/admin/machines

## Environment Variables

- `TS_AUTHKEY`: Tailscale auth key for automatic authentication
- `TS_ACCEPT_ROUTES`: Accept subnet routes from other nodes (default: true)
- `TS_SSH`: Enable SSH access through Tailscale (default: true)
- `TS_EXTRA_ARGS`: Additional Tailscale arguments (e.g., `--advertise-exit-node`)
