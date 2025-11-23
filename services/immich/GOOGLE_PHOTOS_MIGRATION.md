# Google Photos to Immich Migration Guide

## Overview

This guide covers migrating photos from Google Photos to Immich using Google Takeout.

## Step 1: Export from Google Photos

1. Go to [takeout.google.com](https://takeout.google.com)
2. Click **"Deselect all"**
3. Check only **"Google Photos"**
4. Click **"All photo albums included"** → select albums or keep all
5. Click **"Next step"**
6. Configure export:
   - **Delivery method:** Send download link via email
   - **Frequency:** Export once
   - **File type:** .zip
   - **File size:** 50GB (larger = fewer files to download)
7. Click **"Create export"**
8. Wait for email (can take hours to days depending on library size)
9. Download all zip files to server

**Repeat for each Google account.**

## Step 2: Download Zips to Server

```bash
# Create a folder for takeout files
mkdir -p /data/google-takeout
cd /data/google-takeout

# Download using wget or browser
# Example if you have direct links:
wget "https://..." -O takeout-account1-001.zip
wget "https://..." -O takeout-account1-002.zip
```

## Step 3: Install immich-go

`immich-go` is the best tool for Google Takeout imports - it properly handles metadata from JSON files.

```bash
cd /data/google-takeout

# Download latest immich-go
wget https://github.com/simulot/immich-go/releases/latest/download/immich-go_linux_amd64.tar.gz

# Extract
tar -xzf immich-go_linux_amd64.tar.gz

# Verify
./immich-go --help
```

## Step 4: Get Immich API Key

1. Open Immich web UI: `http://<server-ip>:2283`
2. Click your profile icon (top right)
3. Go to **Account Settings**
4. Click **API Keys** in the sidebar
5. Click **New API Key**
6. Give it a name (e.g., "migration")
7. Copy the key

## Step 5: Upload to Immich

### Option A: Upload zip files directly (recommended)

```bash
cd /data/google-takeout

# Upload all zips at once - immich-go handles extraction
./immich-go -server=http://localhost:2283 -key=YOUR_API_KEY upload from-google-photos *.zip
```

### Option B: Extract first, then upload

```bash
# Extract all zips
mkdir extracted
for f in *.zip; do unzip -o "$f" -d extracted/; done

# Upload extracted folder
./immich-go -server=http://localhost:2283 -key=YOUR_API_KEY upload from-google-photos extracted/
```

### Useful flags

```bash
# Dry run (see what would be uploaded without actually uploading)
./immich-go -server=http://localhost:2283 -key=YOUR_API_KEY upload from-google-photos --dry-run *.zip

# Create albums based on Google Photos album structure
./immich-go -server=http://localhost:2283 -key=YOUR_API_KEY upload from-google-photos --create-albums *.zip

# Skip duplicates already in Immich
./immich-go -server=http://localhost:2283 -key=YOUR_API_KEY upload from-google-photos --skip-duplicates *.zip

# Full recommended command
./immich-go -server=http://localhost:2283 -key=YOUR_API_KEY upload from-google-photos \
  --create-albums \
  --skip-duplicates \
  *.zip
```

## Step 6: Verify Import

1. Open Immich web UI
2. Check **Timeline** for imported photos
3. Go to **Administration** → **Jobs** to monitor processing:
   - Thumbnail generation
   - Face detection
   - Smart search indexing
   - Video transcoding

## Troubleshooting

### "API key invalid"
- Make sure you copied the full API key
- Check server URL is correct (http vs https)

### "Connection refused"
- Verify Immich is running: `docker ps | grep immich`
- Check port 2283 is accessible

### Duplicate photos
- Use `--skip-duplicates` flag
- Immich also has built-in duplicate detection

### Missing metadata/dates
- `immich-go` reads Google's JSON sidecar files automatically
- Make sure you're using `from-google-photos` command, not regular `upload`

### Out of disk space
- Check available space: `df -h`
- Clean up zips after successful import
- Consider importing one account at a time

## Cleanup After Migration

```bash
# After successful import, remove takeout files
rm -rf /data/google-takeout

# Delete the API key if no longer needed (from Immich UI)
```

## Multiple Google Accounts

Repeat the entire process for each Google account:

1. Export Account 1 → Upload → Verify
2. Export Account 2 → Upload → Verify
3. etc.

All photos will be merged into your single Immich library.

## Resources

- [immich-go GitHub](https://github.com/simulot/immich-go)
- [Immich Documentation](https://immich.app/docs)
- [Google Takeout](https://takeout.google.com)
