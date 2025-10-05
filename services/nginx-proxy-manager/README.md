# Nginx Proxy Manager

Nginx Proxy Manager is a reverse proxy with a web UI for managing SSL certificates and proxy hosts.

## What It Does

- **Reverse Proxy**: Routes external traffic to internal services
- **SSL Certificates**: Automatic Let's Encrypt SSL certificates
- **Access Control**: Password protection and IP whitelisting
- **Custom Domains**: Clean URLs for your services

## Quick Start

### 1. Create Docker Network

```bash
# From repo root
docker network create home_server_network
```

### 2. Start Nginx Proxy Manager

```bash
cd /data/code/home_server/services/nginx-proxy-manager
docker compose up -d
```

### 3. Access Web UI

- **URL**: http://YOUR_SERVER_IP:81
- **Default Login**:
  - Email: `admin@example.com`
  - Password: `changeme`

**IMPORTANT**: Change the default credentials immediately after first login!

### 4. First Login Steps

1. Login with default credentials
2. You'll be prompted to:
   - Change email address
   - Set new password
3. Complete the setup

## Configuration

### Add Proxy Host

1. Go to **Hosts** → **Proxy Hosts**
2. Click **Add Proxy Host**
3. Fill in details:
   - **Domain Names**: `service.yourname.duckdns.org`
   - **Scheme**: `http`
   - **Forward Hostname/IP**: Container name (e.g., `netbird-dashboard`)
   - **Forward Port**: Service port (e.g., `80`)
   - **Block Common Exploits**: ✅
   - **Websockets Support**: ✅ (if needed)

4. Go to **SSL** tab:
   - **SSL Certificate**: Request a new SSL certificate
   - **Force SSL**: ✅
   - **Email**: Your email for Let's Encrypt
   - **Agree to ToS**: ✅

5. Click **Save**

### Example Proxy Hosts

| Service | Domain | Forward To | Port |
|---------|--------|------------|------|
| Netbird Dashboard | netbird.yourname.duckdns.org | netbird-dashboard | 80 |
| Netbird API | api.yourname.duckdns.org | netbird-management | 443 |
| Netbird Signal | signal.yourname.duckdns.org | netbird-signal | 443 |
| Jellyfin | jellyfin.yourname.duckdns.org | jellyfin | 8096 |

## Port Forwarding Required

Forward these ports on your router to your server:

- **Port 80** (HTTP) → For Let's Encrypt certificate verification
- **Port 443** (HTTPS) → For all SSL traffic

## Volumes

Data is stored in:
- `/data/code/home_server/services/nginx-proxy-manager/data` - Configuration
- `/data/code/home_server/services/nginx-proxy-manager/letsencrypt` - SSL certificates

## Backup

```bash
# Backup NPM configuration
sudo tar -czf npm-backup-$(date +%Y%m%d).tar.gz \
  /data/code/home_server/services/nginx-proxy-manager/data \
  /data/code/home_server/services/nginx-proxy-manager/letsencrypt
```

## Troubleshooting

### Can't Access Web UI
- Check container is running: `docker ps | grep nginx-proxy`
- Check firewall allows port 81
- Try: `docker compose logs -f`

### SSL Certificate Fails
- Ensure ports 80 and 443 are forwarded
- Check DNS is pointing to your public IP
- Verify email is valid
- Check Let's Encrypt rate limits

### Service Not Accessible
- Verify proxy host configuration
- Check forward hostname matches container name
- Ensure service is on same Docker network
- Check service logs: `docker logs <container-name>`

## Security

1. **Change default credentials** immediately
2. **Restrict admin UI access**:
   - Change port 81 to something else
   - Use access lists to whitelist IPs
   - Or only expose via VPN (Netbird)
3. **Keep updated**: `docker compose pull && docker compose up -d`

## Documentation

- [Official Docs](https://nginxproxymanager.com/guide/)
- [GitHub](https://github.com/NginxProxyManager/nginx-proxy-manager)
