# Home Server Repo Refactor Design

**Date**: 2026-03-07
**Goal**: Clean up the repo for public sharing — remove secrets/data from git, update docs, fix hardcoded paths — without affecting the running setup.
**Audience**: Primarily personal, but presentable publicly.
**Approach**: Incremental commits on main branch.

## 1. Secrets & Data Cleanup

### Problem
- Prowlarr API key committed in `services/media/shelfmark/plugins/prowlarr_config.json`
- 70+ data files tracked that shouldn't be (audiobookshelf DB/migrations, shelfmark covers/plugins, AdGuard config)

### Solution
Add to `.gitignore`:
```
services/media/audiobookshelf/
services/media/shelfmark/
services/dns/adguard/
```

Run `git rm --cached` on all matching tracked files. Files stay on disk — running containers unaffected.

### Post-commit manual step
Rotate Prowlarr API key in Prowlarr UI (Settings > General).

## 2. Missing .env.example

### Tailscale (`services/tailscale/.env.example`)
```env
# Tailscale auth key (get from https://login.tailscale.com/admin/settings/keys)
# Or leave empty and run: docker exec tailscale tailscale up
TS_AUTHKEY=
```

DNS service skipped — only uses `TZ` with a default value in compose.yml.

## 3. Script & Path Fixes

### restart-all.sh (line 14)
Replace hardcoded `SERVICES_DIR="/data/code/home_server/services"` with:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICES_DIR="$(cd "$SCRIPT_DIR/services" 2>/dev/null && pwd || cd "$SCRIPT_DIR/../services" && pwd)"
```
Note: restart-all.sh is in the repo root (not scripts/), so SERVICES_DIR is `$SCRIPT_DIR/services`.

### services/tailscale/compose.yml (line 14)
Replace `/data/code/home_server/services/tailscale/state:/var/lib/tailscale` with `./state:/var/lib/tailscale`.

## 4. Documentation Overhaul

### README.md
- Fix clone URL (`yourusername` -> `sudharsanmaran`)
- Add all services: DNS (AdGuard + Unbound), Management (Caddy + Portainer + Glances), expanded media stack (bazarr, shelfmark, audiobookshelf, seerr, profilarr, cleanuparr, huntarr)
- Update structure diagram to match actual repo layout
- Update configuration table with all services

### Per-service READMEs
- `services/dns/README.md` — new file documenting AdGuard + Unbound chain
- `services/media/README.md` — update to include bazarr, shelfmark, audiobookshelf, seerr, profilarr, cleanuparr, huntarr
- Review existing: `services/tailscale/README.md`, `services/immich/README.md`, `services/management/README.md`

### New: docs/GETTING_STARTED.md
Step-by-step guide:
1. Prerequisites (hardware, OS, Docker)
2. Clone & initial config (copy all .env.examples)
3. Service-by-service setup order: tailscale -> dns -> management -> media -> immich
4. Verification steps per service
5. Accessing services via Caddy reverse proxy (*.home-server domains)
6. Post-setup: backups, updates, monitoring

## Commit Plan

| # | Message | Scope |
|---|---------|-------|
| 1 | `fix: update .gitignore and untrack data files` | .gitignore + git rm --cached |
| 2 | `fix: make restart-all.sh path dynamic` | restart-all.sh |
| 3 | `fix: use relative path in tailscale compose` | services/tailscale/compose.yml |
| 4 | `docs: add tailscale .env.example` | services/tailscale/.env.example |
| 5 | `docs: update README with all services and fix structure` | README.md |
| 6 | `docs: add GETTING_STARTED.md and update per-service READMEs` | docs/ + services/*/README.md |

## Constraints
- No changes to running Docker containers
- Only `git rm --cached` (files stay on disk)
- No git history rewriting
- No changes to compose service definitions (only the tailscale volume path)
