# Netbird + Nginx Proxy Manager Setup Plan

## Overview

Self-host Netbird VPN mesh network with Nginx Proxy Manager for clean URLs and SSL certificates.

## Architecture

```
Internet
    ↓
Router (Port Forward 80, 443, 51820/udp)
    ↓
Nginx Proxy Manager (SSL Termination)
    ↓
    ├─→ netbird.yourdomain.com → Netbird Dashboard
    ├─→ api.netbird.yourdomain.com → Netbird Management API
    ├─→ signal.netbird.yourdomain.com → Netbird Signal Server
    ├─→ jellyfin.yourdomain.com → Jellyfin (optional)
    ├─→ radarr.yourdomain.com → Radarr (optional)
    └─→ etc...
```

## Requirements

### 1. Domain Name
- **Need**: A domain you own (e.g., `yourdomain.com`)
- **Options**:
  - Buy domain: Namecheap, Cloudflare, Google Domains (~$10-15/year)
  - Free subdomain: DuckDNS, FreeDNS (limited features)
- **Subdomains needed**:
  - `netbird.yourdomain.com` - Dashboard
  - `api.netbird.yourdomain.com` - Management API
  - `signal.netbird.yourdomain.com` - Signal server
  - Optional: `npm.yourdomain.com` - Nginx Proxy Manager UI

### 2. DNS Configuration
Point these to your **public IP**:
```
A Record: netbird.yourdomain.com → YOUR_PUBLIC_IP
A Record: api.netbird.yourdomain.com → YOUR_PUBLIC_IP
A Record: signal.netbird.yourdomain.com → YOUR_PUBLIC_IP
A Record: npm.yourdomain.com → YOUR_PUBLIC_IP
```

Or use wildcard:
```
A Record: *.yourdomain.com → YOUR_PUBLIC_IP
```

### 3. Port Forwarding (Router)
Forward these ports to your server:
- **80** (HTTP) → Nginx Proxy Manager (for Let's Encrypt)
- **443** (HTTPS) → Nginx Proxy Manager (SSL traffic)
- **51820/udp** (WireGuard) → Netbird (if using relay)
- **3478/udp** (STUN) → Netbird (optional, for NAT traversal)
- **49152-65535/udp** (TURN) → Netbird (optional, for relay)

### 4. Network Setup
Create shared Docker network for services:
```bash
docker network create home_server_network
```

## Service Structure

```
home_server/
├── services/
│   ├── nginx-proxy-manager/
│   │   ├── compose.yml
│   │   ├── data/
│   │   ├── letsencrypt/
│   │   └── README.md
│   ├── netbird/
│   │   ├── compose.yml
│   │   ├── management/
│   │   ├── signal/
│   │   ├── dashboard/
│   │   └── README.md
│   └── media/
│       └── ... (existing)
```

## Components

### Nginx Proxy Manager
- **Purpose**: Reverse proxy with SSL certificates
- **Web UI**: Port 81 (http://server-ip:81)
- **Default credentials**: admin@example.com / changeme
- **Features**:
  - Automatic SSL via Let's Encrypt
  - Easy subdomain management
  - Access control
  - Custom SSL certificates

### Netbird Components
1. **Management Server**
   - Central control plane
   - Stores peer configurations
   - API endpoint

2. **Signal Server**
   - WebRTC signaling
   - Peer discovery
   - Connection coordination

3. **Dashboard**
   - Web UI for management
   - User/peer management
   - Network visualization

4. **Relay (TURN/STUN)** - Optional
   - For peers behind strict NAT
   - Fallback when direct connection fails

## Security Considerations

### 1. SSL/TLS Certificates
- ✅ Use Let's Encrypt via Nginx Proxy Manager
- ✅ Auto-renewal handled by NPM
- ✅ Force HTTPS for all services

### 2. Authentication
- ✅ Netbird has built-in auth (OAuth or username/password)
- ✅ NPM access lists for additional security
- ✅ Change default passwords immediately

### 3. Firewall Rules
```bash
# Allow only necessary ports
sudo ufw allow 80/tcp    # HTTP (Let's Encrypt)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 51820/udp # WireGuard
sudo ufw enable
```

### 4. Secrets Management
- Store in `.env` files (gitignored)
- Use strong passwords
- Rotate credentials regularly

## DNS Options

### Option 1: Static IP + Domain Registrar DNS
- **Pro**: Full control, reliable
- **Con**: Requires static IP or manual updates

### Option 2: Dynamic DNS (DDNS)
- **Pro**: Works with dynamic IPs
- **Con**: Requires DDNS client
- **Services**: DuckDNS, No-IP, Cloudflare (API)

### Option 3: Cloudflare Tunnel (Zero Trust)
- **Pro**: No port forwarding needed, DDoS protection
- **Con**: All traffic through Cloudflare
- **Note**: Great alternative to traditional reverse proxy

## Docker Network Strategy

### Option A: Single Shared Network (Recommended)
```yaml
# All services join home_server_network
networks:
  default:
    name: home_server_network
    external: true
```
- ✅ Simple inter-service communication
- ✅ NPM can reach all services by container name

### Option B: Multiple Networks
```yaml
# NPM on frontend network, services on backend
networks:
  frontend:  # NPM and exposed services
  backend:   # Internal services only
```
- ✅ Better isolation
- ⚠️ More complex setup

## Deployment Steps (High Level)

1. **Setup Nginx Proxy Manager**
   - Deploy container
   - Configure admin credentials
   - Test access to web UI

2. **Configure DNS**
   - Add A records for subdomains
   - Wait for propagation (up to 24h)

3. **Setup Port Forwarding**
   - Forward 80, 443 on router
   - Test external access

4. **Deploy Netbird**
   - Configure environment variables
   - Start containers
   - Initialize setup

5. **Configure NPM Proxy Hosts**
   - Add proxy hosts for each subdomain
   - Request SSL certificates
   - Test HTTPS access

6. **Connect First Client**
   - Install Netbird client
   - Connect to your instance
   - Verify connectivity

## Optional: Expose Media Services

You can optionally expose media services through NPM:

### Public Access (Be Careful!)
- `jellyfin.yourdomain.com` → Jellyfin (for remote streaming)
- Secure with strong passwords + 2FA

### VPN-Only Access (Recommended)
- Keep media services on local network
- Access only via Netbird VPN
- More secure, no public exposure

## Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Domain | $10-15/year | Required |
| Server/VPS | $0 | Using your homeserver |
| SSL Certificates | $0 | Let's Encrypt free |
| Cloudflare (optional) | $0 | Free tier sufficient |
| **Total** | **$10-15/year** | Just domain cost |

## Troubleshooting Checklist

- [ ] Domain DNS propagated (use `nslookup netbird.yourdomain.com`)
- [ ] Ports forwarded correctly (test with canyouseeme.org)
- [ ] Firewall allows traffic
- [ ] Docker containers running (`docker ps`)
- [ ] NPM proxy hosts configured
- [ ] SSL certificates issued (check NPM UI)
- [ ] Netbird services healthy (`docker compose logs`)

## Next Steps

1. Decide on domain registrar
2. Choose authentication method for Netbird
3. Decide if using Cloudflare (DNS only or with tunnel)
4. Prepare environment variables
5. Create service configurations

## References

- [Netbird Self-Hosting Docs](https://docs.netbird.io/selfhosted/selfhosted-guide)
- [Nginx Proxy Manager Docs](https://nginxproxymanager.com/guide/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
