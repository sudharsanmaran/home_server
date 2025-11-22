#!/usr/bin/env python3
"""
Smart Download Script for Jellyfin + AllDebrid
Automatically downloads movies based on watch patterns and rarity
"""

import os
import sys
import json
import requests
from datetime import datetime
import logging

# Configuration
JELLYFIN_URL = os.getenv('JELLYFIN_URL', 'http://jellyfin-test:8096')
JELLYFIN_API_KEY = os.getenv('JELLYFIN_API_KEY', '')
JELLYSTAT_URL = os.getenv('JELLYSTAT_URL', 'http://jellystat:3000')
RADARR_URL = os.getenv('RADARR_URL', 'http://radarr:7878')
RADARR_API_KEY = os.getenv('RADARR_API_KEY', '')  # Set via environment variable

# User settings
TRACKED_USER_NAME = os.getenv('TRACKED_USER_NAME', 'admin')  # Your username
LOCAL_NETWORK = os.getenv('LOCAL_NETWORK', '192.168.')  # Your local network prefix
TAILSCALE_NETWORK = os.getenv('TAILSCALE_NETWORK', '100.64.')  # Tailscale network
WATCH_COUNT_THRESHOLD = int(os.getenv('WATCH_COUNT_THRESHOLD', '2'))  # Download after 2 watches
MIN_SEEDERS_RARE = int(os.getenv('MIN_SEEDERS_RARE', '10'))  # <10 seeders = rare

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/conversions/smart_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def is_local_user(ip_address):
    """Check if user is on local network or Tailscale"""
    if ip_address.startswith(LOCAL_NETWORK) or ip_address.startswith(TAILSCALE_NETWORK):
        return True
    return False


def get_watch_count(item_id, user_id):
    """Get watch count for specific item and user from Jellystat"""
    try:
        # Try Jellystat API first
        response = requests.get(
            f"{JELLYSTAT_URL}/api/getItemHistory",
            params={'itemId': item_id, 'userId': user_id},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return len(data) if isinstance(data, list) else 0
    except Exception as e:
        logger.warning(f"Jellystat API error: {e}, falling back to Jellyfin")

    # Fallback to Jellyfin API
    try:
        response = requests.get(
            f"{JELLYFIN_URL}/Users/{user_id}/Items/{item_id}",
            headers={'X-MediaBrowser-Token': JELLYFIN_API_KEY},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            user_data = data.get('UserData', {})
            return user_data.get('PlayCount', 0)
    except Exception as e:
        logger.error(f"Failed to get watch count: {e}")

    return 0


def is_rare_content(movie_title, year=None):
    """Check if content is rare/might disappear"""
    # Criteria for "rare":
    # 1. Old foreign films (pre-2000, non-English)
    # 2. Criterion Collection
    # 3. Director's Cut/Special editions
    # 4. Low IMDb popularity (could query IMDb API)

    rare_keywords = [
        'criterion', 'director\'s cut', 'special edition',
        'restored', 'remastered', 'limited edition',
        'collectors edition', 'uncut', 'extended'
    ]

    title_lower = movie_title.lower()

    # Check for rare keywords
    if any(keyword in title_lower for keyword in rare_keywords):
        logger.info(f"Rare content detected: {movie_title} (special edition/restoration)")
        return True

    # Check if old film (pre-1990)
    if year and int(year) < 1990:
        logger.info(f"Rare content detected: {movie_title} (old film from {year})")
        return True

    return False


def get_movie_details_from_radarr(tmdb_id=None, title=None):
    """Get movie details from Radarr"""
    try:
        response = requests.get(
            f"{RADARR_URL}/api/v3/movie",
            headers={'X-Api-Key': RADARR_API_KEY},
            timeout=10
        )

        if response.status_code == 200:
            movies = response.json()
            for movie in movies:
                if tmdb_id and movie.get('tmdbId') == tmdb_id:
                    return movie
                if title and movie.get('title', '').lower() == title.lower():
                    return movie
    except Exception as e:
        logger.error(f"Failed to get Radarr movie details: {e}")

    return None


def trigger_download(radarr_movie_id):
    """Trigger download in Radarr"""
    try:
        # Get movie file info
        response = requests.get(
            f"{RADARR_URL}/api/v3/movie/{radarr_movie_id}",
            headers={'X-Api-Key': RADARR_API_KEY},
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Failed to get movie info from Radarr")
            return False

        movie = response.json()

        # Check if already downloaded to HDD
        if movie.get('hasFile') and '/storage/media' in movie.get('path', ''):
            logger.info(f"Movie already on HDD: {movie.get('title')}")
            return True

        # Search for movie to trigger download
        response = requests.post(
            f"{RADARR_URL}/api/v3/command",
            headers={'X-Api-Key': RADARR_API_KEY},
            json={
                'name': 'MoviesSearch',
                'movieIds': [radarr_movie_id]
            },
            timeout=10
        )

        if response.status_code in [200, 201]:
            logger.info(f"Download triggered for: {movie.get('title')}")
            return True
        else:
            logger.error(f"Failed to trigger download: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Failed to trigger download: {e}")
        return False


def process_playback_event(event_data):
    """Process Jellyfin playback event"""
    try:
        # Extract event information
        user_name = event_data.get('User', {}).get('Name', '')
        user_id = event_data.get('UserId', '')
        item_id = event_data.get('ItemId', '')
        item_name = event_data.get('Item', {}).get('Name', '')
        item_type = event_data.get('Item', {}).get('Type', '')
        item_year = event_data.get('Item', {}).get('ProductionYear')
        client_ip = event_data.get('Session', {}).get('RemoteEndPoint', '')

        logger.info(f"Playback event: {user_name} watched {item_name} from {client_ip}")

        # Only process movies for the tracked user
        if item_type != 'Movie':
            logger.info(f"Skipping non-movie content: {item_type}")
            return

        if user_name != TRACKED_USER_NAME:
            logger.info(f"Skipping non-tracked user: {user_name}")
            return

        # Check if user is on local network
        is_local = is_local_user(client_ip)
        logger.info(f"User location: {'Local' if is_local else 'Remote'} ({client_ip})")

        # Get watch count
        watch_count = get_watch_count(item_id, user_id)
        logger.info(f"Watch count for {item_name}: {watch_count}")

        # Check if rare content
        is_rare = is_rare_content(item_name, item_year)

        # Decision logic
        should_download = False
        reason = ""

        if watch_count >= WATCH_COUNT_THRESHOLD:
            should_download = True
            reason = f"watched {watch_count} times"
        elif is_rare:
            should_download = True
            reason = "rare/special content"
        elif is_local and watch_count >= 1:
            # Download after first watch if local user
            should_download = True
            reason = "local user rewatch"

        if should_download:
            logger.info(f"DOWNLOAD TRIGGERED: {item_name} - Reason: {reason}")

            # Get Radarr movie ID
            movie = get_movie_details_from_radarr(title=item_name)
            if movie:
                trigger_download(movie['id'])
            else:
                logger.warning(f"Movie not found in Radarr: {item_name}")
        else:
            logger.info(f"No download needed for {item_name}")

    except Exception as e:
        logger.error(f"Error processing playback event: {e}", exc_info=True)


if __name__ == "__main__":
    # Test mode: read event from stdin or test with sample data
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Test with sample data
        test_event = {
            'User': {'Name': 'admin'},
            'UserId': 'test-user-id',
            'ItemId': 'test-item-id',
            'Item': {
                'Name': 'The Long Walk',
                'Type': 'Movie',
                'ProductionYear': 2025
            },
            'Session': {'RemoteEndPoint': '192.168.1.100'}
        }
        process_playback_event(test_event)
    else:
        # Read JSON event from stdin (webhook)
        try:
            event_data = json.load(sys.stdin)
            process_playback_event(event_data)
        except Exception as e:
            logger.error(f"Failed to read event data: {e}")
            sys.exit(1)
