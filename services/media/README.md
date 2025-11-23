# Media Stack Setup

## TODO

- [ ] **Jellyseerr search filtering** - No language/region filtering available. Tamil movies get buried under irrelevant results. Searching by year or IMDB ID doesn't help.
- [ ] **Radarr language profiles** - Configure profiles for:
  - Tamil dubbed Hollywood movies
  - English dubbed foreign movies
- [ ] **Google Photos migration** - Migrate photos to self-hosted solution (Immich)
- [ ] **Immich backup to HDD** - Set up backup of Immich data to external HDD for safety

---

## Services

**aria2** - Reliable downloads with auto-resume (solves 12GB+ timeout issues)
**rdtclient** - Real-Debrid integration
**radarr** - Movie management
**media-converter** - Auto-converts MKV → MP4 for TV compatibility

## Configuration

### 1. RDTClient + aria2
```
http://localhost:6500
Settings → Download Client → Aria2c
URL: http://aria2:6800/jsonrpc
Secret: <your ARIA2_RPC_SECRET from .env>
Test → Save
```

### 2. Radarr Custom Script (Auto-Convert)
```
http://localhost:7878
Settings → Connect → + Custom Script
Name: Auto Convert MKV to MP4
On Import: ✅
Path: /scripts/radarr_hook.sh
Test → Save
```

## What It Does

1. **Download**: aria2 handles large files with auto-resume
2. **Import**: Radarr moves file to `/data/media/movies/`
3. **Convert**: Automatically converts MKV → MP4 (HEVC remux, lossless)
4. **Verify**: Checks integrity before/after conversion
5. **Delete**: Removes MKV only if MP4 is verified
6. **Play**: Your TV can now play MP4 files

## Conversion Details

**Fast (3-8 minutes per hour of video):**
- HEVC/H.264/H.265 → MP4 (remux only, no re-encoding)

**Skipped:**
- AV1 (too slow - recommends redownloading HEVC)
- Already MP4

**Safety:**
- Original MKV kept if any check fails
- Output verified before deletion
- Size validation (90-105%)

## Files

### Essential Scripts
- `convert_mkv_to_mp4.py` - Main converter
- `corruption_tracker.py` - Quality tracking
- `corruption_analytics.py` - Analytics
- `radarr_hook.sh` - Radarr integration
- `analyze.sh` - Quick analytics commands
- `scan_library.sh` - One-time library scan (optional)

### Configuration
- `radarr_config.json` - Radarr API settings
- `Dockerfile` - Container build
- `README.md` - Original conversion docs

## Analytics

After conversions run:
```bash
cd /data/code/home_server/scripts/media-conversion
./analyze.sh summary      # Overview
./analyze.sh recommended  # Best publishers
./analyze.sh quality      # Quality scores
```

## Monitoring

```bash
docker logs media-converter -f       # Watch conversions
docker logs aria2 -f                 # Watch downloads
docker ps | grep -E "aria2|radarr"   # Check services
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for comprehensive solutions to common issues including:
- RDTClient mount path and download issues
- Rclone FUSE mount problems
- Jellyfin/Infuse compatibility
- Broken symlinks after mount changes

**Downloads timing out?**
- Check RDTClient is using aria2

**MKV not converting?**
- Check Radarr custom script is configured
- Check logs: `docker logs media-converter`

**MKV not deleted?**
- Safety feature - check logs for validation errors
- Output must pass all integrity checks

## Success Indicators

✅ Downloads complete without timeout
✅ MP4 files appear automatically
✅ MKV files deleted (if conversion succeeded)
✅ TV can play files

## Performance

**Typical conversion times:**
- 2 hour HEVC movie (20GB): ~6-8 minutes
- 2.5 hour 4K movie (50GB): ~10-15 minutes
- Integrity check: ~5 seconds (fast container validation)

## File Safety

Original MKV is deleted ONLY if:
1. Conversion succeeds
2. Output MP4 exists
3. Output passes integrity check
4. Output size is valid (90-105%)

Otherwise, original is preserved.
