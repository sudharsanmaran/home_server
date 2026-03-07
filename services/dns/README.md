# DNS Services (AdGuard Home + Unbound)

## Overview

This stack provides network-wide DNS filtering and ad-blocking using AdGuard Home, with Unbound as a recursive DNS resolver forwarding to Quad9 over DNS-over-TLS (DoT).

## Architecture

```
Client --> AdGuard Home (port 53) --> Unbound (port 5335) --> Quad9 DoT (upstream)
```

- **AdGuard Home**: DNS filtering, ad-blocking, and query logging. Acts as the primary DNS server for the network.
- **Unbound**: Recursive DNS resolver. Receives queries from AdGuard and forwards them to Quad9 (`9.9.9.9`) over DoT for privacy.

## Ports

| Port | Protocol | Service |
|------|----------|---------|
| 53 | TCP/UDP | AdGuard Home DNS (host network) |
| 3001 | TCP | AdGuard Home web UI |
| 5335 | TCP/UDP | Unbound DNS |

## Setup

```bash
cd services/dns
docker compose up -d
```

Access the AdGuard Home dashboard at `http://<server-ip>:3001` and complete the initial setup wizard.

Set your server IP as the DNS server on your router or individual devices.

## Configuration

### AdGuard Home

All filtering rules, blocklists, and DNS rewrites are managed through the AdGuard web UI at port 3001. Configuration is persisted in `adguard/conf/`.

To route `*.home-server` domains to your server, add a DNS rewrite in AdGuard:
- Domain: `*.home-server`
- Answer: your server's LAN IP

### Unbound

Upstream DNS and resolver settings are in `unbound/unbound.conf`. The default configuration:

- Forwards all queries to Quad9 (`9.9.9.9`, `149.112.112.112`) over DoT
- Enables DNSSEC validation
- Restricts access to private network ranges
- Caches responses for performance

Edit `unbound/unbound.conf` to change upstream DNS providers or tuning parameters.

## Management

```bash
# View logs
docker compose logs -f adguard
docker compose logs -f unbound

# Restart
docker compose restart

# Update
docker compose pull && docker compose up -d
```
