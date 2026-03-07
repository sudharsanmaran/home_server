# DNS Filtering + Tailscale Exit Node Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up AdGuard Home + Unbound + Quad9 DoT for network-wide DNS filtering, replace dnsmasq, and enable Tailscale exit node so all traffic (home + remote) is ad-free, malware-protected, and encrypted.

**Architecture:** AdGuard Home (port 53) handles ad/tracker blocking and `*.home-server` DNS rewrites. Unbound (port 5335) provides a second cache layer and forwards to Quad9 over DoT for real-time malware protection. Tailscale exit node routes all remote traffic through the home server. A new `services/dns` directory holds AdGuard + Unbound configs.

**Tech Stack:** Docker Compose, AdGuard Home, Unbound, Quad9 DoT, Tailscale exit node, Caddy (unchanged)

---

## Current State

- **dnsmasq** on `100.126.155.105:53` resolves `*.home-server` → `100.126.155.105`
- **systemd-resolved** stub listener on `127.0.0.53:53` and `127.0.0.54:53`
- **Tailscale** running in Docker with `network_mode: host`, no exit node
- **IPv4 forwarding** enabled, **IPv6 forwarding** disabled
- **Router DNS** currently `192.168.0.1` (ISP default)
- Split DNS in Tailscale admin: `home-server → 100.126.155.105`

## Target State

- **AdGuard Home** on `0.0.0.0:53` (host network) — ad/tracker blocking + `*.home-server` rewrites
- **Unbound** on `127.0.0.1:5335` — caching recursive forwarder to Quad9 DoT
- **dnsmasq** removed
- **systemd-resolved** stub listener disabled (frees port 53)
- **Tailscale** exit node enabled
- **Router** DHCP DNS set to `192.168.0.112`
- **Tailscale admin** global DNS `100.126.155.105` with "Use with exit node"

---

### Task 1: Create DNS service directory and Unbound config

**Files:**
- Create: `services/dns/compose.yml`
- Create: `services/dns/unbound/unbound.conf`

**Step 1: Create directory structure**

```bash
mkdir -p /data/code/home_server/services/dns/unbound
mkdir -p /data/code/home_server/services/dns/adguard/conf
mkdir -p /data/code/home_server/services/dns/adguard/work
```

**Step 2: Write Unbound config**

Create `services/dns/unbound/unbound.conf`:

```yaml
server:
    verbosity: 1
    interface: 0.0.0.0
    port: 53
    do-ip4: yes
    do-ip6: no
    do-udp: yes
    do-tcp: yes

    # Access control - allow local and Docker networks
    access-control: 127.0.0.0/8 allow
    access-control: 172.16.0.0/12 allow
    access-control: 192.168.0.0/16 allow
    access-control: 10.0.0.0/8 allow
    access-control: 100.64.0.0/10 allow

    # Privacy and security
    hide-identity: yes
    hide-version: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    harden-referral-path: yes
    use-caps-for-id: yes
    qname-minimisation: yes

    # Performance
    num-threads: 2
    msg-cache-slabs: 4
    rrset-cache-slabs: 4
    infra-cache-slabs: 4
    key-cache-slabs: 4
    msg-cache-size: 64m
    rrset-cache-size: 128m
    cache-min-ttl: 300
    cache-max-ttl: 86400
    prefetch: yes
    prefetch-key: yes
    serve-expired: yes
    serve-expired-ttl: 86400

    # Logging
    logfile: ""
    log-queries: no
    log-replies: no

forward-zone:
    name: "."
    forward-tls-upstream: yes
    # Quad9 primary (DoT)
    forward-addr: 9.9.9.9@853#dns.quad9.net
    # Quad9 secondary (DoT)
    forward-addr: 149.112.112.112@853#dns.quad9.net
```

**Step 3: Verify config syntax**

```bash
docker run --rm -v /data/code/home_server/services/dns/unbound/unbound.conf:/opt/unbound/etc/unbound/unbound.conf mvance/unbound:latest unbound-checkconf
```

Expected: `no errors in /opt/unbound/etc/unbound/unbound.conf`

**Step 4: Commit**

```bash
cd /data/code/home_server
git add services/dns/
git commit -m "feat(dns): add Unbound config with Quad9 DoT forwarding"
```

---

### Task 2: Write DNS Docker Compose

**Files:**
- Create: `services/dns/compose.yml`

**Step 1: Write compose file**

Create `services/dns/compose.yml`:

```yaml
services:
  adguard:
    image: adguard/adguardhome:latest
    container_name: adguard
    restart: always
    network_mode: host
    volumes:
      - ./adguard/work:/opt/adguardhome/work
      - ./adguard/conf:/opt/adguardhome/conf
    environment:
      - TZ=${TZ:-Asia/Kolkata}
    depends_on:
      unbound:
        condition: service_started

  unbound:
    image: mvance/unbound:latest
    container_name: unbound
    restart: always
    ports:
      - "5335:53/tcp"
      - "5335:53/udp"
    volumes:
      - ./unbound/unbound.conf:/opt/unbound/etc/unbound/unbound.conf:ro
    environment:
      - TZ=${TZ:-Asia/Kolkata}
```

**Step 2: Commit**

```bash
cd /data/code/home_server
git add services/dns/compose.yml
git commit -m "feat(dns): add Docker Compose for AdGuard Home + Unbound"
```

---

### Task 3: Disable systemd-resolved stub listener (requires sudo)

**Files:**
- Modify: `/etc/systemd/resolved.conf`

**Step 1: Disable stub listener to free port 53**

```bash
sudo mkdir -p /etc/systemd/resolved.conf.d
sudo tee /etc/systemd/resolved.conf.d/no-stub.conf << 'EOF'
[Resolve]
DNSStubListener=no
DNS=127.0.0.1
FallbackDNS=
EOF
```

**Step 2: Update resolv.conf symlink**

```bash
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
```

**Step 3: Restart systemd-resolved**

```bash
sudo systemctl restart systemd-resolved
```

**Step 4: Verify port 53 is free**

```bash
ss -tulnp | grep ':53 '
```

Expected: Only dnsmasq on `100.126.155.105:53` remains (no `127.0.0.53` or `127.0.0.54`).

---

### Task 4: Stop dnsmasq and start DNS stack

**Step 1: Stop dnsmasq**

```bash
cd /data/code/home_server/services/management
docker compose stop dnsmasq
docker compose rm -f dnsmasq
```

**Step 2: Verify port 53 is fully free**

```bash
ss -tulnp | grep ':53 '
```

Expected: No output (port 53 completely free).

**Step 3: Start Unbound first**

```bash
cd /data/code/home_server/services/dns
docker compose up -d unbound
```

**Step 4: Test Unbound resolves via Quad9**

```bash
docker exec unbound drill @127.0.0.1 google.com
```

Expected: A records for google.com returned.

**Step 5: Start AdGuard Home**

```bash
cd /data/code/home_server/services/dns
docker compose up -d adguard
```

**Step 6: Verify AdGuard Home setup wizard is accessible**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Expected: `200` (setup wizard page).

---

### Task 5: Configure AdGuard Home

**This task is done via the AdGuard Home web UI at `http://192.168.0.112:3000`**

**Step 1: Complete setup wizard**

- Listen interface: `0.0.0.0:53` (DNS)
- Admin interface: `0.0.0.0:3000` (Web UI)
- Set admin username and password

**Step 2: Configure upstream DNS**

Go to Settings → DNS Settings → Upstream DNS servers:

```
127.0.0.1:5335
```

Click "Test upstreams" to verify. Expected: green checkmark.

**Step 3: Add DNS rewrites for *.home-server**

Go to Filters → DNS Rewrites → Add:

| Domain | Answer |
|---|---|
| `*.home-server` | `100.126.155.105` |

This replaces dnsmasq's `address=/home-server/100.126.155.105`.

**Step 4: Enable DNSSEC**

Go to Settings → DNS Settings → Enable DNSSEC.

**Step 5: Add blocklists**

Go to Filters → DNS Blocklists → Add:

- AdGuard DNS filter (pre-installed, enable it)
- OISD Big: `https://big.oisd.nl`
- Steven Black Unified: `https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts`
- Energized Ultimate: `https://energized.pro/unified/formats/hosts`

**Step 6: Test DNS resolution**

```bash
# Test ad blocking
nslookup ads.google.com 127.0.0.1
# Expected: 0.0.0.0 (blocked)

# Test normal resolution
nslookup google.com 127.0.0.1
# Expected: real IP

# Test *.home-server rewrite
nslookup jellyfin.home-server 127.0.0.1
# Expected: 100.126.155.105

nslookup immich.home-server 127.0.0.1
# Expected: 100.126.155.105

nslookup radarr.home-server 127.0.0.1
# Expected: 100.126.155.105
```

**Step 7: Commit**

```bash
cd /data/code/home_server
git add services/dns/adguard/
git commit -m "feat(dns): configure AdGuard Home with blocklists and home-server rewrites"
```

---

### Task 6: Remove dnsmasq from management compose

**Files:**
- Modify: `services/management/compose.yml` (remove dnsmasq service)
- Delete: `services/management/dnsmasq/` directory

**Step 1: Edit management compose**

Remove lines 41-49 from `services/management/compose.yml` (the entire dnsmasq service block):

```yaml
  # REMOVE THIS ENTIRE BLOCK:
  dnsmasq:
    image: andyshinn/dnsmasq:latest
    container_name: dnsmasq
    restart: always
    network_mode: host
    volumes:
      - ./dnsmasq/dnsmasq.conf:/etc/dnsmasq.conf:ro
    cap_add:
      - NET_ADMIN
```

**Step 2: Remove dnsmasq config directory**

```bash
rm -rf /data/code/home_server/services/management/dnsmasq
```

**Step 3: Commit**

```bash
cd /data/code/home_server
git add -A services/management/
git commit -m "feat(dns): remove dnsmasq, replaced by AdGuard Home"
```

---

### Task 7: Enable Tailscale exit node

**Files:**
- Modify: `services/tailscale/compose.yml`

**Step 1: Update Tailscale compose to advertise exit node**

Edit `services/tailscale/compose.yml`, change the environment section:

```yaml
    environment:
      - TS_AUTHKEY=${TS_AUTHKEY:-}
      - TS_ACCEPT_ROUTES=true
      - TS_EXTRA_ARGS=--advertise-exit-node --accept-dns=false
      - TS_SSH=true
```

**Step 2: Enable IPv6 forwarding (exit node requires both)**

```bash
sudo tee /etc/sysctl.d/99-tailscale-exit.conf << 'EOF'
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF
sudo sysctl -p /etc/sysctl.d/99-tailscale-exit.conf
```

**Step 3: Restart Tailscale container**

```bash
cd /data/code/home_server/services/tailscale
docker compose down
docker compose up -d
```

**Step 4: Verify exit node is advertised**

```bash
docker exec tailscale tailscale status --json | python3 -c "import sys,json; d=json.load(sys.stdin); print('ExitNodeOption:', d['Self']['ExitNodeOption'])"
```

Expected: `ExitNodeOption: True`

**Step 5: Commit**

```bash
cd /data/code/home_server
git add services/tailscale/compose.yml
git commit -m "feat(tailscale): enable exit node with accept-dns=false"
```

---

### Task 8: Configure Tailscale admin console (manual)

**This task is done in the Tailscale admin console at https://login.tailscale.com/admin**

**Step 1: Approve exit node**

- Go to Machines tab
- Find `home-server`
- Click the three-dot menu → Edit route settings
- Enable "Use as exit node"

**Step 2: Configure DNS**

- Go to DNS tab
- Add nameserver: `100.126.155.105`
- Enable "Override local DNS"
- Click three-dot menu on the nameserver → Enable **"Use with exit node"**

**Step 3: Keep existing split DNS**

- Verify split DNS for `home-server` → `100.126.155.105` still exists
- This ensures `*.home-server` queries always route to AdGuard even without exit node

**Step 4: Test from a client device**

On your phone/laptop with Tailscale:
- Set exit node to `home-server`
- Visit `http://jellyfin.home-server` — should work
- Visit a known ad domain — should be blocked
- Check AdGuard dashboard — should see queries from 127.0.0.1 (exit node client)

---

### Task 9: Configure router DNS

**This task is done on the TP-Link AX3000 router admin at http://192.168.0.1**

**Step 1: Change DHCP DNS server**

- Go to Advanced → Network → DHCP Server (or similar)
- Set Primary DNS: `192.168.0.112`
- Set Secondary DNS: leave empty (or `192.168.0.112` again)
- Save and apply

**Step 2: Verify from a LAN device**

Disconnect and reconnect WiFi on a device, then:

```bash
nslookup google.com
# Expected: Server is 192.168.0.112

nslookup jellyfin.home-server
# Expected: 100.126.155.105
```

**Step 3: Check AdGuard dashboard**

Visit `http://adguard.home-server:3000` — you should see queries from LAN devices appearing.

---

### Task 10: Add AdGuard to Caddy reverse proxy

**Files:**
- Modify: `services/management/caddy/Caddyfile`

**Step 1: Add AdGuard Home entry to Caddyfile**

Add to the Caddyfile:

```
# AdGuard Home
http://adguard.home-server {
    reverse_proxy localhost:3000
}
```

**Step 2: Restart Caddy**

```bash
cd /data/code/home_server/services/management
docker compose restart caddy
```

**Step 3: Verify**

```bash
curl -s -o /dev/null -w "%{http_code}" http://adguard.home-server
```

Expected: `200` or `302` (redirect to login).

**Step 4: Commit**

```bash
cd /data/code/home_server
git add services/management/caddy/Caddyfile
git commit -m "feat(dns): add AdGuard Home to Caddy reverse proxy"
```

---

### Task 11: Update restart scripts

**Files:**
- Modify: `/data/code/home_server/restart-all.sh`
- Modify: `/data/code/home_server/scripts/start-all.sh`

**Step 1: Update restart-all.sh**

Update the STACKS array to include dns (before management, since Caddy needs DNS):

```bash
STACKS=(tailscale dns management media immich)
```

**Step 2: Update start-all.sh if it has similar logic**

Check and update `scripts/start-all.sh` to include the `dns` stack.

**Step 3: Commit**

```bash
cd /data/code/home_server
git add restart-all.sh scripts/
git commit -m "feat(dns): add dns stack to startup scripts"
```

---

### Task 12: End-to-end verification

**Step 1: Test DNS filtering (from server)**

```bash
# Ad domain — should be blocked
nslookup ads.google.com 127.0.0.1
# Expected: 0.0.0.0

# Normal domain — should resolve
nslookup github.com 127.0.0.1
# Expected: real IP

# Home service — should rewrite
nslookup jellyfin.home-server 127.0.0.1
# Expected: 100.126.155.105

# All home services
for svc in jellyfin radarr sonarr immich portainer glances adguard; do
    echo -n "$svc.home-server: "
    nslookup $svc.home-server 127.0.0.1 | grep Address | tail -1
done
# Expected: all resolve to 100.126.155.105
```

**Step 2: Test from LAN device (phone/laptop on home WiFi)**

- Open browser → `http://jellyfin.home-server` — should load
- Open browser → visit any website — should load (no DNS issues)
- Check AdGuard dashboard — device queries should appear

**Step 3: Test exit node (from phone on mobile data)**

- Disconnect from home WiFi, use mobile data
- Enable Tailscale exit node → `home-server`
- Open browser → `http://jellyfin.home-server` — should load
- Open browser → visit any website — should load with ads blocked
- Check what-is-my-ip → should show your home IP
- Check AdGuard dashboard — exit node queries should appear

**Step 4: Test DNS leak**

- With exit node active, visit `https://dnsleaktest.com`
- Run extended test
- Expected: only Quad9 servers shown (no ISP DNS)

**Step 5: Final commit**

```bash
cd /data/code/home_server
git add -A
git commit -m "feat(dns): complete DNS filtering + Tailscale exit node setup"
```

---

## Rollback Plan

If anything breaks:

1. Stop DNS stack: `cd /data/code/home_server/services/dns && docker compose down`
2. Re-enable dnsmasq: `cd /data/code/home_server/services/management && docker compose up -d dnsmasq`
3. Re-enable systemd-resolved stub: `sudo rm /etc/systemd/resolved.conf.d/no-stub.conf && sudo systemctl restart systemd-resolved`
4. Router DNS back to automatic (192.168.0.1)
5. Disable exit node in Tailscale admin

## Task Dependency Graph

```
Task 1 (Unbound config) ──┐
                           ├─► Task 4 (Start DNS stack)
Task 2 (Compose file)  ───┤
                           │
Task 3 (systemd-resolved) ─┘
                               ├─► Task 5 (Configure AdGuard) ─► Task 6 (Remove dnsmasq)
                               │
Task 7 (Tailscale exit node) ──┴─► Task 8 (Tailscale admin) ─► Task 9 (Router DNS)
                                                                        │
Task 10 (Caddy) ─────────────────────────────────────────────────────────┤
Task 11 (Scripts) ───────────────────────────────────────────────────────┤
                                                                        ▼
                                                              Task 12 (Verification)
```

Tasks 1-3 can run in parallel. Task 7 can run in parallel with Tasks 4-6.
