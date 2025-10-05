# Home Server Deployment Guide

Complete step-by-step guide to deploy Nginx Proxy Manager + Netbird + Media services with DuckDNS and SSL.

## Prerequisites Checklist

- [ ] Server running (local or VPS)
- [ ] Docker and Docker Compose installed
- [ ] Git installed
- [ ] Router access for port forwarding
- [ ] DuckDNS account created
- [ ] Public IP address known

## Architecture Overview

```
Internet
  ↓
Router (Ports: 80, 443, 3478, 49152-65535)
  ↓
Nginx Proxy Manager (SSL Termination)
  ↓
  ├─→ yourname.duckdns.org → Netbird Dashboard
  ├─→ yourname-api.duckdns.org → Netbird API
  ├─→ yourname-signal.duckdns.org → Netbird Signal
  └─→ media.yourname.duckdns.org → Jellyfin (optional)
```

## Part 1: DuckDNS Setup

### 1.1 Create Account

1. Go to [duckdns.org](https://www.duckdns.org)
2. Sign in (Google/GitHub/email)
3. Save your token securely

### 1.2 Create Domains

Create these domains (all pointing to your public IP):

```
yourname.duckdns.org        → Netbird Dashboard
yourname-api.duckdns.org    → Netbird API
yourname-signal.duckdns.org → Netbird Signal
```

Replace `yourname` with your chosen subdomain.

### 1.3 Set Your Public IP

```bash
# Find public IP
curl ifconfig.me

# Update DuckDNS (test)
curl "https://www.duckdns.org/update?domains=yourname,yourname-api,yourname-signal&token=YOUR_TOKEN&ip="
# Should return: OK
```

### 1.4 Verify DNS

```bash
nslookup yourname.duckdns.org
nslookup yourname-api.duckdns.org
nslookup yourname-signal.duckdns.org
```

All should return your public IP.

## Part 2: Router Configuration

### 2.1 Port Forwarding

Forward these ports to your server's local IP:

| External Port | Internal Port | Protocol | Service |
|---------------|---------------|----------|---------|
| 80 | 80 | TCP | HTTP (Let's Encrypt) |
| 443 | 443 | TCP | HTTPS (All services) |
| 3478 | 3478 | UDP | STUN/TURN |
| 49152-65535 | 49152-65535 | UDP | TURN Relay |

**Find your server's local IP:**
```bash
ip addr show  # Linux
ifconfig      # Mac
ipconfig      # Windows
```

Usually something like `192.168.1.100`

### 2.2 Firewall (if using ufw)

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3478/udp
sudo ufw allow 49152:65535/udp
sudo ufw enable
sudo ufw status
```

## Part 3: Server Setup

### 3.1 Clone Repository

```bash
cd /data/code
git clone <your-repo-url> home_server
cd home_server
```

### 3.2 Create Docker Network

```bash
docker network create home_server_network
```

### 3.3 Verify Structure

```bash
ls -la services/
# Should show: media, netbird, nginx-proxy-manager
```

## Part 4: Deploy Nginx Proxy Manager

### 4.1 Start NPM

```bash
cd /data/code/home_server/services/nginx-proxy-manager
docker compose up -d
```

### 4.2 Wait for Startup

```bash
# Watch logs
docker compose logs -f

# Wait until you see "Server listening on port 81"
# Press Ctrl+C to exit logs
```

### 4.3 Access Web UI

1. Open browser: `http://YOUR_SERVER_IP:81`
2. **Default login**:
   - Email: `admin@example.com`
   - Password: `changeme`

### 4.4 First Login

1. You'll be prompted to change email and password
2. Set new credentials (save them!)
3. Complete setup

## Part 5: Deploy Netbird

### 5.1 Configure Environment

```bash
cd /data/code/home_server/services/netbird

# Copy example files
cp .env.example .env
cp management.json.example management.json
cp turnserver.conf.example turnserver.conf
```

### 5.2 Edit .env

```bash
nano .env
```

Update:
```env
NETBIRD_DOMAIN=yourname.duckdns.org
NETBIRD_API_DOMAIN=yourname-api.duckdns.org
NETBIRD_SIGNAL_DOMAIN=yourname-signal.duckdns.org
NETBIRD_TURN_DOMAIN=yourname.duckdns.org

# Generate strong password
TURN_USERNAME=netbird
TURN_PASSWORD=<random-strong-password>
```

**Generate strong password:**
```bash
openssl rand -base64 32
```

### 5.3 Edit management.json

```bash
nano management.json
```

Replace all instances of:
- `yourname.duckdns.org` → your actual domain
- `change_this_strong_password` → your TURN password from .env

### 5.4 Edit turnserver.conf

```bash
nano turnserver.conf
```

Update:
- `realm=yourname.duckdns.org` → your domain
- `user=netbird:change_this_strong_password` → your TURN credentials

### 5.5 Start Netbird

```bash
docker compose up -d
```

### 5.6 Check Logs

```bash
docker compose logs -f

# Look for errors
# Ctrl+C to exit
```

### 5.7 Verify Containers

```bash
docker ps | grep netbird

# Should see:
# netbird-management
# netbird-signal
# netbird-dashboard
# netbird-coturn
```

## Part 6: Configure Nginx Proxy Manager

Now connect NPM to Netbird services.

### 6.1 Add Netbird Dashboard

1. In NPM UI: **Hosts** → **Proxy Hosts** → **Add Proxy Host**

**Details tab:**
- Domain Names: `yourname.duckdns.org`
- Scheme: `http`
- Forward Hostname / IP: `netbird-dashboard`
- Forward Port: `80`
- Cache Assets: ✅
- Block Common Exploits: ✅
- Websockets Support: ✅

**SSL tab:**
- SSL Certificate: `Request a new SSL Certificate`
- Force SSL: ✅
- HTTP/2 Support: ✅
- HSTS Enabled: ✅
- Email Address for Let's Encrypt: `your@email.com`
- I Agree to Let's Encrypt TOS: ✅

Click **Save**

### 6.2 Add Netbird Management API

**Details tab:**
- Domain Names: `yourname-api.duckdns.org`
- Scheme: `https`
- Forward Hostname / IP: `netbird-management`
- Forward Port: `443`
- Block Common Exploits: ✅
- Websockets Support: ✅

**SSL tab:**
- Request new SSL certificate (same as above)

**Advanced tab:**
```nginx
proxy_ssl_verify off;
```

Click **Save**

### 6.3 Add Netbird Signal Server

**Details tab:**
- Domain Names: `yourname-signal.duckdns.org`
- Scheme: `https`
- Forward Hostname / IP: `netbird-signal`
- Forward Port: `443`
- Block Common Exploits: ✅
- Websockets Support: ✅

**SSL tab:**
- Request new SSL certificate

**Advanced tab:**
```nginx
proxy_ssl_verify off;
```

Click **Save**

### 6.4 Wait for SSL Certificates

- NPM will request certificates from Let's Encrypt
- Takes 30-60 seconds per domain
- Check **SSL Certificates** tab to see status

## Part 7: Test Netbird Access

### 7.1 Access Dashboard

1. Open browser: `https://yourname.duckdns.org`
2. Should load Netbird dashboard
3. If SSL error: wait a bit longer for certificate
4. If timeout: check DNS, port forwarding, firewall

### 7.2 Create Admin Account

1. On first access, create admin user
2. Set username and password
3. Login

### 7.3 Configure Authentication

Choose authentication method:
- **None**: Simple username/password (OK for personal use)
- **Auth0**: OAuth integration (more complex)
- **Hosted IDP**: Other OAuth providers

For simplicity, start with **None** (username/password).

## Part 8: Add Your First Device

### 8.1 Create Setup Key

In Netbird dashboard:
1. Go to **Setup Keys**
2. Click **Create Setup Key**
3. Name: `my-devices`
4. Expires: 30 days (or longer)
5. Usage limit: 10 (or unlimited)
6. Auto-assign groups: (optional)
7. Click **Create**
8. **Copy the key**

### 8.2 Install Netbird Client

**On your laptop/desktop:**

Download from [netbird.io/downloads](https://netbird.io/downloads)

**Linux:**
```bash
curl -fsSL https://pkgs.netbird.io/install.sh | sh
```

**Mac:**
```bash
brew install netbirdio/tap/netbird
```

**Windows:**
Download installer from website

### 8.3 Connect Device

```bash
# Using setup key (easiest)
netbird up --setup-key <YOUR_SETUP_KEY>

# Or using login
netbird up --management-url https://yourname-api.duckdns.org
```

**Desktop clients:** Use GUI to connect with setup key or login.

### 8.4 Verify Connection

In Netbird dashboard:
1. Go to **Peers**
2. Should see your device connected
3. Note the assigned IP (e.g., `100.64.0.1`)

**Test connectivity:**
```bash
# Ping another peer
ping 100.64.0.2

# Or ping your server if it's a peer
ping 100.64.0.1
```

## Part 9: Setup DuckDNS Auto-Update

Keep your IP updated automatically.

### Option A: Cron Job

```bash
# Edit crontab
crontab -e

# Add this line
*/5 * * * * curl "https://www.duckdns.org/update?domains=yourname,yourname-api,yourname-signal&token=YOUR_DUCKDNS_TOKEN&ip=" >/dev/null 2>&1
```

### Option B: Docker Container

Create `services/duckdns/compose.yml`:

```yaml
services:
  duckdns:
    image: lscr.io/linuxserver/duckdns:latest
    container_name: duckdns
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
      - SUBDOMAINS=yourname,yourname-api,yourname-signal
      - TOKEN=YOUR_DUCKDNS_TOKEN
      - UPDATE_IP=ipv4
    volumes:
      - /data/code/home_server/services/duckdns/config:/config
```

Then:
```bash
cd /data/code/home_server/services/duckdns
docker compose up -d
```

## Part 10: Optional - Expose Media Services

### 10.1 Add Jellyfin Proxy (If Desired)

**Create domain:**
- `media-yourname.duckdns.org` in DuckDNS

**Add to NPM:**
- Domain: `media-yourname.duckdns.org`
- Forward to: `jellyfin:8096`
- Request SSL certificate

**Security consideration:**
- Publicly exposing media requires strong passwords
- Consider keeping it VPN-only (access via Netbird)

### 10.2 Access Media via VPN (Recommended)

Instead of public exposure:
1. Connect to Netbird VPN
2. Access by local IP: `http://192.168.1.100:8096`
3. Or setup route in Netbird for entire LAN

## Troubleshooting

### NPM Can't Get SSL Certificate

**Check:**
```bash
# DNS resolves correctly
nslookup yourname.duckdns.org

# Port 80 is accessible from internet
curl -I http://yourname.duckdns.org

# Check NPM logs
cd /data/code/home_server/services/nginx-proxy-manager
docker compose logs -f
```

**Common fixes:**
- Verify port 80/443 are forwarded
- Check firewall allows traffic
- Ensure DNS points to your IP
- Wait 5 minutes for DNS propagation

### Netbird Dashboard Won't Load

**Check:**
```bash
# Container running
docker ps | grep netbird-dashboard

# Logs
docker compose logs dashboard

# NPM proxy configured
# Check in NPM UI under Proxy Hosts
```

### Clients Can't Connect to Netbird

**Check:**
```bash
# Management API accessible
curl -k https://yourname-api.duckdns.org

# Signal accessible
curl -k https://yourname-signal.duckdns.org

# TURN server
# Verify UDP ports 3478 and 49152-65535 forwarded
```

### Netbird Peers Can't Communicate

**Check:**
- Both peers connected (dashboard shows online)
- No restrictive access policies
- Test direct ping: `ping <peer-ip>`
- Check TURN is working for NAT traversal

## Post-Deployment

### Security Checklist

- [ ] Changed NPM admin password
- [ ] Used strong TURN password
- [ ] Enabled firewall (ufw)
- [ ] Only exposed necessary ports
- [ ] SSL certificates working
- [ ] DuckDNS auto-update configured
- [ ] Netbird access policies configured
- [ ] Regular backups scheduled

### Monitoring

```bash
# Check all services
docker ps

# Check resource usage
docker stats

# View logs
cd /data/code/home_server
./scripts/logs.sh  # If you create this helper
```

### Backup

```bash
# Backup configurations
cd /data/code/home_server
./scripts/backup.sh

# Or manual
sudo tar -czf home-server-backup-$(date +%Y%m%d).tar.gz \
  services/nginx-proxy-manager/data \
  services/nginx-proxy-manager/letsencrypt \
  services/netbird/ \
  services/media/.env
```

### Updates

```bash
# Update all services
cd /data/code/home_server
./scripts/update-all.sh

# Or manually
cd services/nginx-proxy-manager && docker compose pull && docker compose up -d
cd ../netbird && docker compose pull && docker compose up -d
cd ../media && docker compose pull && docker compose up -d
```

## Next Steps

1. **Add more devices** to Netbird
2. **Configure access policies** in Netbird dashboard
3. **Setup network routes** (optional) to access entire LAN via VPN
4. **Add more services** (Immich, Nextcloud, etc.)
5. **Setup monitoring** (Uptime Kuma, Grafana)
6. **Configure backups** (automated)

## Resources

- [Nginx Proxy Manager Docs](https://nginxproxymanager.com/guide/)
- [Netbird Self-Hosting](https://docs.netbird.io/selfhosted/selfhosted-guide)
- [DuckDNS](https://www.duckdns.org)
- [Let's Encrypt](https://letsencrypt.org)
- Home Server Repo: [Your GitHub URL]

## Support

If you encounter issues:
1. Check service logs: `docker compose logs -f`
2. Verify DNS: `nslookup domain.duckdns.org`
3. Test ports: Use [canyouseeme.org](https://canyouseeme.org)
4. Review this guide carefully
5. Check Netbird/NPM documentation

Good luck with your home server! 🚀
