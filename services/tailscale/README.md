# Tailscale VPN Service

Tailscale provides secure remote access to your home server from anywhere.

## Setup

1. **Create state directory:**
   ```bash
   mkdir -p state
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
Once connected to Tailscale, you can access all services using the Tailscale IP:
- Jellyfin: `http://<tailscale-ip>:8096`
- Immich: `http://<tailscale-ip>:2283`
- Radarr: `http://<tailscale-ip>:7878`
- Other services on your home server

### Exit node (enabled by default):
The compose configuration advertises this node as an exit node (`--advertise-exit-node` in `TS_EXTRA_ARGS`). To use it:
1. Approve the exit node in the Tailscale admin console: https://login.tailscale.com/admin/machines
2. On your client device, select the home server as your exit node

To disable exit node functionality, remove `--advertise-exit-node` from the `TS_EXTRA_ARGS` environment variable in `compose.yml` and restart the container.

## Environment Variables

- `TS_AUTHKEY`: Tailscale auth key for automatic authentication
- `TS_ACCEPT_ROUTES`: Accept subnet routes from other nodes (default: true)
- `TS_SSH`: Enable SSH access through Tailscale (default: true)
- `TS_EXTRA_ARGS`: Additional Tailscale arguments (e.g., `--advertise-exit-node`)
