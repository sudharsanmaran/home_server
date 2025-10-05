# Netbird Self-Hosted VPN

Netbird is a WireGuard-based VPN mesh network for secure remote access to your services.

## What It Does

- **Mesh VPN**: Direct peer-to-peer connections between devices
- **WireGuard**: Fast, modern VPN protocol
- **Zero Trust**: Granular access control
- **NAT Traversal**: Works behind routers without port forwarding
- **Cross-Platform**: Windows, Mac, Linux, iOS, Android

## Components

| Service | Purpose | Port |
|---------|---------|------|
| **Management** | API and control plane | Internal |
| **Signal** | WebRTC signaling for peer discovery | Internal |
| **Dashboard** | Web UI for management | Internal |
| **Coturn** | TURN/STUN for NAT traversal | 3478, 49152-65535 |

All services are exposed via Nginx Proxy Manager with SSL.

## Prerequisites

1. **DuckDNS account** (free at duckdns.org)
2. **Nginx Proxy Manager** running
3. **Docker network**: `home_server_network`
4. **Port forwarding**:
   - 80, 443 (for NPM/SSL)
   - 3478/udp (STUN/TURN)
   - 49152-65535/udp (TURN relay)

## Setup

### 1. Configure Environment

```bash
cd /data/code/home_server/services/netbird
cp .env.example .env
cp management.json.example management.json
cp turnserver.conf.example turnserver.conf
```

Edit `.env`:
```env
NETBIRD_DOMAIN=yourname.duckdns.org
NETBIRD_API_DOMAIN=api.yourname.duckdns.org
NETBIRD_SIGNAL_DOMAIN=signal.yourname.duckdns.org
NETBIRD_TURN_DOMAIN=yourname.duckdns.org
TURN_USERNAME=netbird
TURN_PASSWORD=your_strong_random_password
```

### 2. Update Configuration Files

**Edit `management.json`**:
- Replace all `yourname.duckdns.org` with your actual domain
- Update TURN username/password to match `.env`

**Edit `turnserver.conf`**:
- Replace `yourname.duckdns.org` with your domain
- Update credentials: `user=netbird:your_strong_random_password`

### 3. Start Services

```bash
docker compose up -d
```

Check logs:
```bash
docker compose logs -f
```

### 4. Configure Nginx Proxy Manager

Add these proxy hosts in NPM:

#### Netbird Dashboard
- **Domain**: `netbird.yourname.duckdns.org`
- **Forward**: `netbird-dashboard` → Port `80`
- **SSL**: Request new certificate, Force SSL ✅
- **Websockets**: ✅

#### Netbird Management API
- **Domain**: `api.yourname.duckdns.org`
- **Forward**: `netbird-management` → Port `443`
- **SSL**: Request new certificate, Force SSL ✅
- **Custom Config** (Advanced tab):
  ```nginx
  proxy_ssl_verify off;
  ```

#### Netbird Signal Server
- **Domain**: `signal.yourname.duckdns.org`
- **Forward**: `netbird-signal` → Port `443`
- **SSL**: Request new certificate, Force SSL ✅
- **Websockets**: ✅
- **Custom Config** (Advanced tab):
  ```nginx
  proxy_ssl_verify off;
  ```

### 5. DNS Configuration

In DuckDNS dashboard, create:
- Main domain: `yourname.duckdns.org` → Your Public IP

**Subdomains**: DuckDNS doesn't support traditional subdomains. Use one of these approaches:

**Option A: Multiple DuckDNS domains (Recommended)**
```
yourname.duckdns.org → Your IP (for dashboard)
yourname-api.duckdns.org → Your IP (for API)
yourname-signal.duckdns.org → Your IP (for signal)
```

**Option B: Use a single domain + NPM routing**
- Use `yourname.duckdns.org` for everything
- Configure NPM to route based on path:
  - `/` → Dashboard
  - `/api` → Management API
  - `/signal` → Signal server

**Option C: Use Cloudflare for free subdomain support**
- Transfer DNS to Cloudflare (free)
- Get proper subdomain support
- Better than DuckDNS for this use case

### 6. Access Dashboard

1. Open https://netbird.yourname.duckdns.org (or your chosen domain)
2. First time setup:
   - Create admin account
   - Set up authentication (can use simple username/password)
3. Add your first peer (see below)

## Adding Clients

### Desktop/Laptop

1. Download client from [netbird.io](https://netbird.io/downloads)
2. Install and run
3. Click "Connect"
4. Enter your management URL: `https://api.yourname.duckdns.org`
5. Login and approve

### Mobile

1. Install Netbird app from App Store/Play Store
2. Add network
3. Enter management URL
4. Login and connect

## Network Configuration

In the dashboard:

1. **Setup Key** (for easy device enrollment):
   - Go to Setup Keys
   - Create new key
   - Use this to quickly add devices

2. **Access Control**:
   - Create groups (e.g., "servers", "laptops", "phones")
   - Define policies (who can access what)

3. **Routing** (optional):
   - Configure network routes
   - Access entire LAN through VPN

## Port Forwarding

Forward on your router:

```
External Port → Internal Port (Server IP)
80/tcp → 80/tcp (for NPM/Let's Encrypt)
443/tcp → 443/tcp (for NPM SSL)
3478/udp → 3478/udp (STUN/TURN)
49152-65535/udp → 49152-65535/udp (TURN relay range)
```

**Note**: The UDP port range is large but only used for active relay connections.

## Volumes

Data stored in:
- `/data/code/home_server/services/netbird/management` - Management database
- `/data/code/home_server/services/netbird/signal` - Signal data
- Config files: `management.json`, `turnserver.conf`

## Backup

```bash
# Backup Netbird configuration
sudo tar -czf netbird-backup-$(date +%Y%m%d).tar.gz \
  /data/code/home_server/services/netbird/
```

## Troubleshooting

### Can't Access Dashboard
- Check NPM proxy host is configured
- Verify SSL certificate is valid
- Check DNS points to your IP: `nslookup netbird.yourname.duckdns.org`
- Check container logs: `docker compose logs dashboard`

### Peers Can't Connect
- Verify management API is accessible from internet
- Check signal server is running: `docker compose logs signal`
- Test TURN server: Use [Trickle ICE](https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/)
- Check firewall allows UDP ports

### TURN Server Issues
- Verify ports 3478 and 49152-65535 UDP are forwarded
- Check turnserver.conf credentials match .env
- Test with: `turnutils_uclient -v turn.yourname.duckdns.org`

### Slow Connections
- Peers might be using relay instead of direct connection
- Check NAT traversal is working
- Verify STUN is accessible
- Check local firewall rules

## DuckDNS IP Update

Keep DuckDNS updated with your public IP (if dynamic):

### Option 1: Manual Update
Visit: `https://www.duckdns.org/update?domains=yourname&token=YOUR_TOKEN&ip=`

### Option 2: Cron Job
```bash
# Add to crontab: crontab -e
*/5 * * * * curl "https://www.duckdns.org/update?domains=yourname&token=YOUR_TOKEN&ip=" >/dev/null 2>&1
```

### Option 3: Docker Container
Use `linuxserver/duckdns` container to auto-update.

## Security

1. **Strong passwords**: Use random passwords for TURN
2. **Firewall**: Only open required ports
3. **Access control**: Configure Netbird policies properly
4. **Monitor**: Check dashboard for unknown peers
5. **Updates**: Keep containers updated

## Alternative: Cloudflare for Subdomains

If you have a domain (even free from Freenom), use Cloudflare DNS:

1. Add domain to Cloudflare (free)
2. Change nameservers at registrar
3. Add A records:
   ```
   netbird.yourdomain.com → Your IP
   api.yourdomain.com → Your IP
   signal.yourdomain.com → Your IP
   ```
4. Disable Cloudflare proxy (orange cloud → gray cloud)
5. Let's Encrypt will work perfectly

## Documentation

- [Netbird Self-Hosting Guide](https://docs.netbird.io/selfhosted/selfhosted-guide)
- [DuckDNS Documentation](https://www.duckdns.org/spec.jsp)
- [Coturn Wiki](https://github.com/coturn/coturn/wiki)
