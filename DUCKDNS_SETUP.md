# DuckDNS Setup Guide

Free dynamic DNS service for your home server with SSL support.

## What is DuckDNS?

- **Free**: Completely free dynamic DNS service
- **SSL Compatible**: Works with Let's Encrypt
- **Simple**: Easy to set up and maintain
- **Reliable**: Been around since 2014
- **Limitation**: No native subdomain support (workarounds available)

## Step 1: Create DuckDNS Account

1. Go to [duckdns.org](https://www.duckdns.org)
2. Sign in with:
   - Google
   - GitHub
   - Reddit
   - Twitter
   - Or email

3. You'll get a **token** - save this securely!

## Step 2: Create Domain(s)

### Option A: Multiple Domains (Recommended for Netbird)

Create separate DuckDNS domains for each service:

```
yourname.duckdns.org        → Dashboard
yourname-api.duckdns.org    → Netbird API
yourname-signal.duckdns.org → Netbird Signal
yourname-media.duckdns.org  → Jellyfin (optional)
```

**Steps:**
1. In DuckDNS dashboard, enter domain name (e.g., `yourname`)
2. Click "add domain"
3. Repeat for each subdomain variant:
   - `yourname`
   - `yourname-api`
   - `yourname-signal`
   - etc.

### Option B: Single Domain + Path Routing

Create just one domain and use NPM path-based routing:

```
yourname.duckdns.org → All services
```

Less recommended for Netbird (needs separate endpoints).

## Step 3: Set Your IP Address

### Find Your Public IP

```bash
curl ifconfig.me
# or
curl https://api.ipify.org
```

### Update DuckDNS

**Manual Update:**
1. Go to DuckDNS dashboard
2. Enter your public IP in the "current ip" field
3. Click "update ip"

**Automatic Update (Recommended):**

See "Keeping IP Updated" section below.

## Step 4: Verify DNS Propagation

Test your domains:

```bash
nslookup yourname.duckdns.org
nslookup yourname-api.duckdns.org
nslookup yourname-signal.duckdns.org
```

Should all return your public IP address.

**Note**: DNS propagation is usually instant with DuckDNS, but can take up to 5 minutes.

## Step 5: Configure Services

### Nginx Proxy Manager

Add proxy hosts for each domain:

| Domain | Forward To | Port | SSL |
|--------|------------|------|-----|
| yourname.duckdns.org | netbird-dashboard | 80 | ✅ |
| yourname-api.duckdns.org | netbird-management | 443 | ✅ |
| yourname-signal.duckdns.org | netbird-signal | 443 | ✅ |

### Netbird .env

```env
NETBIRD_DOMAIN=yourname.duckdns.org
NETBIRD_API_DOMAIN=yourname-api.duckdns.org
NETBIRD_SIGNAL_DOMAIN=yourname-signal.duckdns.org
NETBIRD_TURN_DOMAIN=yourname.duckdns.org
```

## Keeping IP Updated

If you have a dynamic IP (most home internet), you need to keep DuckDNS updated.

### Option 1: Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add this line (updates every 5 minutes)
*/5 * * * * curl "https://www.duckdns.org/update?domains=yourname,yourname-api,yourname-signal&token=YOUR_TOKEN&ip=" >/dev/null 2>&1
```

Replace:
- `yourname,yourname-api,yourname-signal` with your domains (comma-separated)
- `YOUR_TOKEN` with your DuckDNS token

### Option 2: Docker Container

Add this to a new service:

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
docker compose up -d
```

### Option 3: Router (DD-WRT/OpenWRT)

Many routers support DDNS updates directly:

1. Go to router admin panel
2. Find DDNS settings
3. Select "Custom" or "DuckDNS"
4. Enter URL: `https://www.duckdns.org/update?domains=yourname&token=YOUR_TOKEN&ip=`

### Option 4: Windows Task Scheduler

Create a batch file (`update-duckdns.bat`):

```batch
@echo off
curl "https://www.duckdns.org/update?domains=yourname,yourname-api&token=YOUR_TOKEN&ip="
```

Schedule it to run every 5 minutes via Task Scheduler.

## Testing DuckDNS

### Test Update Endpoint

```bash
curl "https://www.duckdns.org/update?domains=yourname&token=YOUR_TOKEN&ip="
```

Response should be: `OK`

If you get `KO`, check:
- Token is correct
- Domain exists in your account
- URL is properly formatted

### Test from External Network

Use a different network (mobile data) to test:

1. Visit: `https://yourname.duckdns.org`
2. Should reach your NPM or services

Or use online tools:
- [DNS Checker](https://dnschecker.org)
- [What's My DNS](https://www.whatsmydns.net)

## Troubleshooting

### Domain Not Resolving

```bash
# Check if DuckDNS has your IP
nslookup yourname.duckdns.org

# Compare with your public IP
curl ifconfig.me
```

If they don't match, update DuckDNS.

### SSL Certificate Fails

**Let's Encrypt requirements:**
- Port 80 must be forwarded (for verification)
- Domain must resolve to your public IP
- No Cloudflare proxy (orange cloud) enabled

**Check:**
```bash
# Test from external
curl -I http://yourname.duckdns.org

# Should reach your NPM
```

### IP Not Updating Automatically

Check your update method:

**For cron:**
```bash
# Check cron is running
crontab -l

# Test manually
curl "https://www.duckdns.org/update?domains=yourname&token=YOUR_TOKEN&ip="
```

**For Docker:**
```bash
docker logs duckdns
```

### Rate Limiting

DuckDNS allows updates every 5 minutes. Don't update more frequently.

## Alternative: Cloudflare for Subdomains

If you need proper subdomains, consider Cloudflare:

### Get a Free Domain

1. Register free domain at [Freenom](https://www.freenom.com) (.tk, .ml, .ga, etc.)
2. Or buy cheap domain (~$1/year) at Namecheap, Porkbun

### Use Cloudflare DNS (Free)

1. Sign up at [cloudflare.com](https://www.cloudflare.com)
2. Add your domain
3. Change nameservers at your registrar to Cloudflare's
4. Add A records:
   ```
   netbird.yourdomain.tk → YOUR_IP
   api.yourdomain.tk → YOUR_IP
   signal.yourdomain.tk → YOUR_IP
   ```
5. **Disable proxy** (click orange cloud → gray)
6. Done! Proper subdomains with free SSL

**Advantages:**
- Real subdomains
- Better for Netbird
- DDoS protection (if you enable proxy)
- Better DNS management
- Still free!

## DuckDNS vs Cloudflare

| Feature | DuckDNS | Cloudflare |
|---------|---------|------------|
| **Cost** | Free | Free |
| **Subdomains** | No (workaround needed) | Yes ✅ |
| **Dynamic IP** | Yes ✅ | Via API |
| **Setup** | Very easy | Requires domain |
| **SSL** | Via Let's Encrypt ✅ | Via Let's Encrypt or Cloudflare ✅ |
| **Best for** | Quick testing, single service | Production, multiple services |

## Recommendation

**For testing/simple setup:**
- Use DuckDNS with multiple domain approach
- Example: `yourname.duckdns.org`, `yourname-api.duckdns.org`

**For production/better setup:**
- Get a cheap/free domain
- Use Cloudflare DNS
- Get proper subdomains
- More professional

## Example: Complete Netbird + DuckDNS

### 1. Create DuckDNS Domains
- `myserver.duckdns.org`
- `myserver-api.duckdns.org`
- `myserver-signal.duckdns.org`

### 2. Set All to Your Public IP

### 3. Setup Auto-Update (Cron)
```bash
*/5 * * * * curl "https://www.duckdns.org/update?domains=myserver,myserver-api,myserver-signal&token=abc123&ip=" >/dev/null 2>&1
```

### 4. Configure Netbird .env
```env
NETBIRD_DOMAIN=myserver.duckdns.org
NETBIRD_API_DOMAIN=myserver-api.duckdns.org
NETBIRD_SIGNAL_DOMAIN=myserver-signal.duckdns.org
```

### 5. Add NPM Proxy Hosts
- `myserver.duckdns.org` → `netbird-dashboard:80`
- `myserver-api.duckdns.org` → `netbird-management:443`
- `myserver-signal.duckdns.org` → `netbird-signal:443`

All with Let's Encrypt SSL!

## Resources

- [DuckDNS](https://www.duckdns.org)
- [DuckDNS API Spec](https://www.duckdns.org/spec.jsp)
- [Cloudflare](https://www.cloudflare.com)
- [Freenom](https://www.freenom.com) (free domains)
- [Let's Encrypt](https://letsencrypt.org)
