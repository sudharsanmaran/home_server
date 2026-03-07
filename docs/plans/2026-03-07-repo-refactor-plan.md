# Home Server Repo Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up the home_server repo for public sharing — remove secrets/data from git, update all docs, fix hardcoded paths — without affecting the running setup.

**Architecture:** Incremental commits on main branch. Each task is one commit. All changes are safe (git rm --cached, doc edits, one script path fix, one compose path fix). No containers are restarted or reconfigured.

**Tech Stack:** Git, Bash, Docker Compose (read-only), Markdown

**Design doc:** `docs/plans/2026-03-07-repo-refactor-design.md`

---

### Task 1: Update .gitignore and untrack data files

**Files:**
- Modify: `.gitignore`
- Untrack: `services/media/audiobookshelf/*`, `services/media/shelfmark/*`, `services/dns/adguard/conf/AdGuardHome.yaml`

**Step 1: Read current .gitignore**

Read `.gitignore` to understand existing structure.

**Step 2: Add new ignore rules**

Append these sections to `.gitignore` (after the existing "Tailscale state" section at the end):

```gitignore
# Audiobookshelf runtime data (DB, migrations - app-managed)
services/media/audiobookshelf/

# Shelfmark runtime data (covers, plugin configs with API keys)
services/media/shelfmark/

# AdGuard Home config (contains DNS settings, users)
services/dns/adguard/
```

**Step 3: Untrack data files**

Run:
```bash
cd /data/code/home_server
git rm --cached -r services/media/audiobookshelf/
git rm --cached -r services/media/shelfmark/
git rm --cached services/dns/adguard/conf/AdGuardHome.yaml
```

Expected: Files removed from index, still exist on disk. `git status` shows deletions + modified .gitignore.

**Step 4: Verify files still exist on disk**

Run:
```bash
ls services/media/audiobookshelf/absdatabase.sqlite && echo "OK: files still on disk"
ls services/media/shelfmark/covers/ | head -3 && echo "OK: covers still on disk"
```

Expected: Files present, containers unaffected.

**Step 5: Commit**

```bash
git add .gitignore
git commit -m "fix: update .gitignore and untrack data files

Remove audiobookshelf data (sqlite, migrations), shelfmark runtime
data (covers, plugin configs with Prowlarr API key), and AdGuard
config from git tracking. Files remain on disk.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Make restart-all.sh path dynamic

**Files:**
- Modify: `restart-all.sh:14`

**Step 1: Read the file**

Read `restart-all.sh` to confirm line 14 is `SERVICES_DIR="/data/code/home_server/services"`.

**Step 2: Replace hardcoded path**

Change line 14 from:
```bash
SERVICES_DIR="/data/code/home_server/services"
```
To:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICES_DIR="$SCRIPT_DIR/services"
```

Note: `restart-all.sh` lives in the repo root, so `$SCRIPT_DIR/services` resolves correctly. The existing `set -e` on line 12 stays.

**Step 3: Verify syntax**

Run:
```bash
bash -n /data/code/home_server/restart-all.sh && echo "Syntax OK"
```

Expected: "Syntax OK"

**Step 4: Commit**

```bash
cd /data/code/home_server
git add restart-all.sh
git commit -m "fix: make restart-all.sh path dynamic

Replace hardcoded /data/code/home_server/services with SCRIPT_DIR-relative
path so the repo works from any location.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Use relative path in tailscale compose

**Files:**
- Modify: `services/tailscale/compose.yml:14`

**Step 1: Read the file**

Read `services/tailscale/compose.yml` to confirm line 14 has the hardcoded volume path.

**Step 2: Replace hardcoded path**

Change the volume line from:
```yaml
      - /data/code/home_server/services/tailscale/state:/var/lib/tailscale
```
To:
```yaml
      - ./state:/var/lib/tailscale
```

**Step 3: Verify YAML syntax**

Run:
```bash
cd /data/code/home_server/services/tailscale
docker compose config --quiet 2>&1 && echo "YAML OK" || echo "YAML ERROR"
```

Expected: "YAML OK" (or possibly env var warnings — that's fine, no errors about syntax)

**Step 4: Commit**

```bash
cd /data/code/home_server
git add services/tailscale/compose.yml
git commit -m "fix: use relative path in tailscale compose volume

Replace absolute /data/code/home_server/services/tailscale/state with
./state for portability.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**Note:** Do NOT restart the tailscale container. The change takes effect on next restart/reboot.

---

### Task 4: Add tailscale .env.example

**Files:**
- Create: `services/tailscale/.env.example`

**Step 1: Create the file**

Write `services/tailscale/.env.example`:

```env
# Tailscale auth key (get from https://login.tailscale.com/admin/settings/keys)
# Or leave empty and run: docker exec tailscale tailscale up
TS_AUTHKEY=
```

**Step 2: Verify it won't be gitignored**

Run:
```bash
cd /data/code/home_server
git check-ignore services/tailscale/.env.example && echo "IGNORED - FIX GITIGNORE" || echo "OK: not ignored"
```

Expected: "OK: not ignored" (the `!**/.env.example` rule in .gitignore allows it)

**Step 3: Commit**

```bash
git add services/tailscale/.env.example
git commit -m "docs: add tailscale .env.example

Provide template for TS_AUTHKEY configuration.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Update README.md

**Files:**
- Modify: `README.md`

**Step 1: Read current README**

Read `README.md` to understand current structure.

**Step 2: Rewrite README**

Replace the full contents of `README.md` with an updated version that includes:

1. **Header** — same description, keep it concise
2. **Services section** — add ALL services:
   - **DNS** (AdGuard Home + Unbound) — location `services/dns/`, ports 53 (DNS), 3001 (AdGuard UI), 5335 (Unbound)
   - **Media Server** — update to list ALL sub-services: Jellyfin, Radarr, Sonarr, Bazarr, Prowlarr (VPN), Jellyseerr, Seerr, RDTClient, Jellystat, Shelfmark (VPN), Audiobookshelf, Profilarr, Cleanuparr, Huntarr, FlareSolverr (VPN)
   - **Immich** — keep as-is
   - **Management** (Caddy + Portainer + Glances) — location `services/management/`, ports 9000/9443 (Portainer), 29999 (Glances)
   - **Tailscale VPN** — keep as-is
3. **Quick Start** — fix clone URL to `sudharsanmaran`, add link to `docs/GETTING_STARTED.md` for full guide
4. **Structure diagram** — updated to match reality:
   ```
   home_server/
   ├── services/
   │   ├── dns/                     # AdGuard Home + Unbound
   │   │   ├── compose.yml
   │   │   ├── adguard/             # AdGuard config (gitignored)
   │   │   └── unbound/             # Unbound config
   │   ├── immich/                  # Photo management
   │   │   ├── compose.yml
   │   │   └── .env.example
   │   ├── management/              # Caddy + Portainer + Glances
   │   │   ├── compose.yml
   │   │   └── caddy/Caddyfile
   │   ├── media/                   # Media streaming stack
   │   │   ├── compose.yml
   │   │   ├── .env.example
   │   │   └── rclone/             # Rclone config for AllDebrid
   │   └── tailscale/              # VPN service
   │       ├── compose.yml
   │       └── .env.example
   ├── scripts/
   │   ├── start-all.sh
   │   ├── stop-all.sh
   │   ├── update-all.sh
   │   ├── restart-rclone.sh
   │   ├── backup.sh
   │   ├── kill-stuck-container.sh
   │   ├── validate-jellyfin-gpu.sh
   │   └── common.sh
   ├── docs/
   │   └── GETTING_STARTED.md
   ├── restart-all.sh              # Boot recovery script
   ├── homeserver-recovery.service # Systemd service
   └── README.md
   ```
5. **Configuration table** — add all services:
   | Service | Config File | Key Variables |
   |---------|-------------|---------------|
   | Media | `services/media/.env` | ALLDEBRID_API_KEY, SURFSHARK_PRIVATE_KEY, POSTGRES_PASSWORD, JWT_SECRET |
   | Immich | `services/immich/.env` | DB_PASSWORD, UPLOAD_LOCATION |
   | Tailscale | `services/tailscale/.env` | TS_AUTHKEY |
   | DNS | No .env needed | TZ (default in compose) |
   | Management | No .env needed | TZ (default in compose) |
6. **Security, Troubleshooting, License** — keep existing content, minor cleanup

**Step 3: Verify no broken links**

Run:
```bash
cd /data/code/home_server
grep -oP '\[.*?\]\((.*?)\)' README.md | grep -oP '\((.*?)\)' | tr -d '()' | while read link; do
  if [[ "$link" != http* ]]; then
    [ -e "$link" ] || echo "BROKEN: $link"
  fi
done
```

Expected: No broken links (or only `docs/GETTING_STARTED.md` which is created in next task).

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README with all services and fix structure

Add DNS, management, and expanded media services. Fix clone URL,
update structure diagram, and configuration table.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Create docs/GETTING_STARTED.md and update per-service READMEs

This is the largest task. It has three sub-parts.

**Files:**
- Create: `docs/GETTING_STARTED.md`
- Create: `services/dns/README.md`
- Modify: `services/media/README.md` (add missing services)
- Modify: `services/management/README.md` (add Caddy and Glances)
- Review (no change needed if accurate): `services/tailscale/README.md`, `services/immich/README.md`

#### Part A: Create docs/GETTING_STARTED.md

Write `docs/GETTING_STARTED.md` with these sections:

1. **Prerequisites**
   - Ubuntu 22.04+ (or similar Linux)
   - Docker Engine 24+ and Docker Compose v2
   - 8GB+ RAM (16GB recommended for Immich ML)
   - 100GB+ storage (500GB+ if using Immich)
   - Intel CPU with iGPU recommended (for hardware transcoding)

2. **Clone & Configure**
   ```bash
   git clone https://github.com/sudharsanmaran/home_server.git
   cd home_server
   cp services/media/.env.example services/media/.env
   cp services/immich/.env.example services/immich/.env
   cp services/tailscale/.env.example services/tailscale/.env
   cp services/media/rclone/rclone.conf.example services/media/rclone/rclone.conf
   ```
   Then edit each `.env` file with your values.

3. **Service Startup Order**
   Services must start in this order (dependency chain):
   - **Step 1: Tailscale** — VPN/networking foundation
     ```bash
     cd services/tailscale && docker compose up -d
     docker exec tailscale tailscale up  # if not using auth key
     ```
   - **Step 2: DNS** — AdGuard + Unbound
     ```bash
     cd services/dns && docker compose up -d
     ```
     Verify: `http://<server-ip>:3001` → AdGuard UI
   - **Step 3: Management** — Caddy, Portainer, Glances
     ```bash
     cd services/management && docker compose up -d
     ```
     Verify: `http://<server-ip>:9000` → Portainer
   - **Step 4: Media** — full media stack
     ```bash
     cd services/media && docker compose up -d
     ```
     Verify: `http://<server-ip>:8096` → Jellyfin
   - **Step 5: Immich** — photo management
     ```bash
     cd services/immich && docker compose up -d
     ```
     Verify: `http://<server-ip>:2283` → Immich

   Or start everything at once: `./scripts/start-all.sh`

4. **Accessing Services via Caddy**
   Once Caddy is running, services are available at `http://<name>.home-server`:
   - `jellyfin.home-server`, `radarr.home-server`, `sonarr.home-server`, etc.
   - Requires DNS resolution of `*.home-server` to your server IP (configure in AdGuard or local DNS)

5. **Boot Recovery**
   The `restart-all.sh` script and `homeserver-recovery.service` systemd unit handle automatic startup on reboot:
   ```bash
   sudo cp homeserver-recovery.service /etc/systemd/system/
   sudo systemctl enable homeserver-recovery
   ```

6. **Maintenance**
   - Update all: `./scripts/update-all.sh`
   - Backup configs: `./scripts/backup.sh`
   - Restart rclone mount: `./scripts/restart-rclone.sh`

7. **Next Steps**
   - Configure each service via its web UI (see per-service READMEs)
   - Set up Tailscale on your devices for remote access
   - Configure AdGuard DNS filtering rules
   - Set up Immich mobile app for photo backup

#### Part B: Create services/dns/README.md

Write `services/dns/README.md`:

- **Overview**: AdGuard Home for DNS filtering/ad-blocking, forwarding to Unbound for recursive DNS resolution via Quad9 DoT.
- **Architecture**: Client → AdGuard (port 53) → Unbound (port 5335) → Quad9 DoT (upstream)
- **Ports**: 53 (DNS), 3001 (AdGuard UI), 5335 (Unbound)
- **Setup**: `docker compose up -d`, access AdGuard at `http://<ip>:3001`
- **Configuration**: AdGuard UI for filtering rules, `unbound/unbound.conf` for upstream DNS settings
- **Reference**: Link to Unbound config file `unbound/unbound.conf`

#### Part C: Update services/management/README.md

Read and update `services/management/README.md` to add:
- **Caddy** — reverse proxy, auto-routes `*.home-server` domains, config in `caddy/Caddyfile`
- **Glances** — system monitoring at port 29999
- Update the setup section to remove hardcoded path

#### Part D: Update services/media/README.md

Read and update `services/media/README.md` to add a services list section covering ALL containers:
- **Jellyfin** (8096) — media server with hardware transcoding
- **Radarr** (7878) — movie management
- **Sonarr** (8989) — TV management
- **Bazarr** (6767) — subtitle management
- **Prowlarr** (9696, via VPN) — indexer management
- **Jellyseerr** (5055) — media requests (legacy)
- **Seerr** (5056) — media requests (new)
- **RDTClient** (6500) — AllDebrid download client
- **Jellystat** (3000) — Jellyfin analytics
- **Shelfmark** (8084, via VPN) — ebook/audiobook downloads
- **Audiobookshelf** (13378) — audiobook/podcast server
- **Profilarr** (6868) — quality profile sync
- **Cleanuparr** (11011) — media cleanup
- **Huntarr** (9705) — missing media hunter
- **FlareSolverr** (8191, via VPN) — Cloudflare bypass
- **Rclone** — AllDebrid cloud mount
- **VPN (Gluetun)** — Surfshark WireGuard for Prowlarr/FlareSolverr/Shelfmark

Keep the existing RDTClient, Radarr, and media-converter setup sections. Add the new services as a reference table at the top.

#### Part E: Review tailscale and immich READMEs

Read `services/tailscale/README.md` — note it has a hardcoded path in the "Create state directory" step. Update that line to use a relative path (`mkdir -p state`). Also the exit node note says "uncomment TS_EXTRA_ARGS" but it's already set in compose.yml — fix this.

Read `services/immich/README.md` — comprehensive and accurate. No changes needed.

**Step: Commit all docs**

```bash
cd /data/code/home_server
git add docs/GETTING_STARTED.md services/dns/README.md services/management/README.md services/media/README.md services/tailscale/README.md
git commit -m "docs: add getting started guide and update per-service READMEs

Add comprehensive docs/GETTING_STARTED.md with prerequisites, setup order,
and maintenance. Add DNS README, update management/media/tailscale READMEs
with complete service listings.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Final verification

**Step 1: Check git status is clean**

Run:
```bash
cd /data/code/home_server
git status
```

Expected: Clean working tree (no untracked important files).

**Step 2: Verify tracked files are clean**

Run:
```bash
git ls-files | grep -E '\.sqlite|covers/|plugins/prowlarr_config' | head -5
```

Expected: No output (all data files untracked).

**Step 3: Verify no secrets in tracked files**

Run:
```bash
git ls-files | xargs grep -l 'api_key\|API_KEY\|password\|secret' 2>/dev/null | grep -v '.env.example' | grep -v '.md' | grep -v '.gitignore'
```

Expected: No output (or only compose files referencing `${VAR}` env var syntax, not actual values).

**Step 4: Review commit log**

Run:
```bash
git log --oneline -8
```

Expected: 6 new commits on top of the design doc commit.

**Step 5: Remind user of manual step**

Print: "All commits done. Manual step remaining: **Rotate Prowlarr API key** in Prowlarr UI (Settings > General > API Key > regenerate). The old key was exposed in git history."

---

### Notes for implementer

- **Do NOT restart any Docker containers.** All changes are git/file-only.
- **Do NOT rewrite git history.** The Prowlarr API key stays in history; the user will rotate it.
- **Immich compose.yml** also has hardcoded paths (`/data/code/home_server/services/immich/...`) but the design explicitly excludes changing those. Don't touch them.
- **AdGuard config** (`services/dns/adguard/conf/AdGuardHome.yaml`) may fail `git rm --cached` due to file permissions. If so, use `sudo git rm --cached` or skip it (it's already getting gitignored by the directory rule).
