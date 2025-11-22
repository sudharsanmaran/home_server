#!/usr/bin/env python3
"""
MKV to MP4 Converter for Jellyfin
Enhanced with corruption detection and safe file handling
"""

import os
import sys
import subprocess
import json
import logging
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

# Import corruption tracker
try:
    from corruption_tracker import CorruptionTracker
    CORRUPTION_TRACKING_ENABLED = True
except ImportError:
    CORRUPTION_TRACKING_ENABLED = False
    print("Warning: corruption_tracker.py not found - detailed analytics disabled")

# Configuration
LOG_DIR = "/var/log/conversions"
LOG_FILE = f"{LOG_DIR}/conversion_{datetime.now().strftime('%Y%m%d')}.log"
JELLYFIN_URL = "http://localhost:8096"
JELLYFIN_API_KEY = "32016b7447544f58bee948cc3d825e75"  # Add your API key here

# Safety settings
MIN_OUTPUT_SIZE_RATIO = 0.90  # Output must be at least 90% of input size
MAX_OUTPUT_SIZE_RATIO = 1.05  # Output shouldn't exceed 105% of input (for remux)
VERIFY_OUTPUT = True  # Verify output file integrity before deleting input

# Ensure log directory exists
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize corruption tracker
corruption_tracker = None
if CORRUPTION_TRACKING_ENABLED:
    try:
        corruption_tracker = CorruptionTracker()
        logger.info("Corruption tracking enabled - detailed analytics active")
    except Exception as e:
        logger.warning(f"Could not initialize corruption tracker: {e}")
        CORRUPTION_TRACKING_ENABLED = False


class Colors:
    """ANSI color codes for terminal output"""
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color


class ConversionError(Exception):
    """Custom exception for conversion errors"""
    pass


def verify_file_integrity(file_path, stage="unknown"):
    """
    Verify video file integrity using ffprobe (fast container check)

    Args:
        file_path (str): Path to video file
        stage (str): Stage of verification (input/output)

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        logger.info(f"Verifying file integrity: {os.path.basename(file_path)}")

        # Use ffprobe for fast container validation (no frame decoding)
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration,size',
            '-show_entries', 'stream=codec_name,codec_type',
            '-of', 'json',
            file_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout (much faster than full decode)
        )

        if result.returncode == 0 and result.stdout:
            # Try to parse JSON to ensure file is readable
            try:
                data = json.loads(result.stdout)
                if 'format' in data and 'streams' in data and len(data['streams']) > 0:
                    logger.info(f"{Colors.GREEN}✓ File integrity verified (fast check){Colors.NC}")
                    return True, None
                else:
                    error_msg = "File structure is invalid"
                    logger.error(f"{Colors.RED}✗ File integrity check failed{Colors.NC}")
                    logger.error(f"Error: {error_msg}")
                    return False, error_msg
            except json.JSONDecodeError:
                error_msg = "Could not parse file metadata"
                logger.error(f"{Colors.RED}✗ File integrity check failed{Colors.NC}")
                logger.error(f"Error: {error_msg}")
                return False, error_msg
        else:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            logger.error(f"{Colors.RED}✗ File integrity check failed{Colors.NC}")
            logger.error(f"Error: {error_msg}")

            # Log to corruption tracker
            if corruption_tracker:
                try:
                    corruption_tracker.log_corruption_event(
                        file_path=file_path,
                        corruption_type="integrity_check_failed",
                        corruption_stage=stage,
                        error_message=f"Integrity check failed at {stage}",
                        ffmpeg_errors=error_msg,
                        status="corrupted"
                    )
                except Exception as e:
                    logger.warning(f"Could not log to corruption tracker: {e}")

            return False, error_msg

    except subprocess.TimeoutExpired:
        logger.error("Integrity check timed out")
        return False, "Verification timeout"
    except Exception as e:
        logger.error(f"Integrity check error: {e}")
        return False, str(e)


def get_video_info(input_file):
    """
    Get video codec information using ffprobe
    
    Args:
        input_file (str): Path to video file
        
    Returns:
        dict: Video information including codec, duration, size
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            input_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Find video stream
        video_stream = None
        audio_streams = []
        subtitle_streams = []
        
        for stream in data.get('streams', []):
            stream_type = stream.get('codec_type')
            if stream_type == 'video' and not video_stream:
                video_stream = stream
            elif stream_type == 'audio':
                audio_streams.append(stream)
            elif stream_type == 'subtitle':
                subtitle_streams.append(stream)
        
        if not video_stream:
            logger.error("No video stream found")
            return None
        
        format_info = data.get('format', {})
        
        info = {
            'codec': video_stream.get('codec_name', 'unknown'),
            'duration': float(format_info.get('duration', 0)),
            'size': int(format_info.get('size', 0)),
            'bit_rate': int(format_info.get('bit_rate', 0)),
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'audio_count': len(audio_streams),
            'subtitle_count': len(subtitle_streams),
            'video_bitrate': int(video_stream.get('bit_rate', 0)) if video_stream.get('bit_rate') else 0
        }
        
        return info
        
    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe output: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting video info: {e}")
        return None


def estimate_conversion_time(info):
    """
    Estimate conversion time based on codec and file size
    
    Args:
        info (dict): Video information from get_video_info
        
    Returns:
        tuple: (estimated_minutes, should_convert, reason)
    """
    codec = info['codec']
    duration_hours = info['duration'] / 3600
    
    if codec in ['hevc', 'h264', 'h265']:
        # Fast remux - just copying streams
        estimated_minutes = duration_hours * 3  # ~3 min per hour of video
        should_convert = True
        reason = "Fast remux (no re-encoding)"
    elif codec == 'av1':
        # Very slow re-encode
        estimated_minutes = duration_hours * 1800  # ~30 hours per hour of video
        should_convert = False
        reason = "AV1 re-encoding too slow (48+ hours)"
    elif codec == 'mpeg4':
        # Moderate re-encode
        estimated_minutes = duration_hours * 120  # ~2 hours per hour of video
        should_convert = True
        reason = "MPEG-4 re-encoding acceptable"
    elif codec == 'mpeg2video':
        # Moderate re-encode
        estimated_minutes = duration_hours * 90
        should_convert = True
        reason = "MPEG-2 re-encoding acceptable"
    else:
        # Unknown codec - be cautious
        estimated_minutes = 0
        should_convert = False
        reason = f"Unknown codec: {codec} (manual review recommended)"
    
    return estimated_minutes, should_convert, reason


def convert_to_mp4(input_file, output_file, input_info):
    """
    Convert MKV to MP4 using ffmpeg with corruption protection
    
    Args:
        input_file (str): Input MKV file path
        output_file (str): Output MP4 file path
        input_info (dict): Input file information
        
    Returns:
        bool: True if successful, False otherwise
    """
    temp_output = f"{output_file}.tmp.mp4"
    
    # Ensure temp file doesn't already exist
    if os.path.exists(temp_output):
        logger.warning(f"Removing existing temp file: {temp_output}")
        os.remove(temp_output)
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-c:v', 'copy',          # Copy video stream
        '-c:a', 'copy',          # Copy audio streams
        '-c:s', 'mov_text',      # Convert subtitles to MP4 format
        '-map', '0:v:0',         # Map first video stream
        '-map', '0:a',           # Map all audio streams
        '-map', '0:s?',          # Map subtitles if present (optional)
        '-tag:v', 'hvc1',        # HEVC tag for compatibility
        '-movflags', '+faststart', # Enable fast start for streaming
        '-max_muxing_queue_size', '1024',  # Increase muxing queue
        '-f', 'mp4',
        '-hide_banner',
        '-loglevel', 'warning',
        '-stats',
        '-y',                    # Overwrite output
        temp_output
    ]
    
    try:
        logger.info(f"Starting conversion: {os.path.basename(input_file)}")
        logger.info(f"Command: {' '.join(cmd[:8])}... (truncated)")
        
        # Run conversion with real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Monitor progress
        last_log_time = datetime.now()
        for line in process.stdout:
            # Log progress every 30 seconds
            if (datetime.now() - last_log_time).seconds >= 30:
                if 'time=' in line:
                    logger.info(f"Progress: {line.strip()}")
                    last_log_time = datetime.now()
        
        process.wait()
        
        if process.returncode != 0:
            logger.error(f"{Colors.RED}✗ FFmpeg failed with return code {process.returncode}{Colors.NC}")
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
        
        # Verify temp file was created
        if not os.path.exists(temp_output):
            logger.error(f"{Colors.RED}✗ Output file not created{Colors.NC}")
            return False
        
        # Check output file size
        output_size = os.path.getsize(temp_output)
        input_size = input_info['size']
        size_ratio = output_size / input_size
        
        logger.info(f"Input size: {input_size / (1024**3):.2f} GB")
        logger.info(f"Output size: {output_size / (1024**3):.2f} GB")
        logger.info(f"Size ratio: {size_ratio:.2%}")
        
        # Validate output size
        if size_ratio < MIN_OUTPUT_SIZE_RATIO:
            logger.error(f"{Colors.RED}✗ Output file too small ({size_ratio:.1%} of input){Colors.NC}")
            logger.error(f"{Colors.RED}  Possible corruption or incomplete conversion{Colors.NC}")
            os.remove(temp_output)
            return False
        
        if size_ratio > MAX_OUTPUT_SIZE_RATIO:
            logger.warning(f"{Colors.YELLOW}⚠ Output file larger than expected ({size_ratio:.1%}){Colors.NC}")
            logger.warning(f"{Colors.YELLOW}  This is unusual for remux but continuing...{Colors.NC}")
        
        # Verify output file integrity if enabled
        if VERIFY_OUTPUT:
            is_valid, error_msg = verify_file_integrity(temp_output, stage="output")
            if not is_valid:
                logger.error(f"{Colors.RED}✗ Output file failed integrity check{Colors.NC}")
                logger.error(f"{Colors.RED}  Error: {error_msg}{Colors.NC}")
                logger.error(f"{Colors.RED}  Keeping original file for safety{Colors.NC}")
                os.remove(temp_output)
                return False
        
        # All checks passed - move temp to final location
        logger.info(f"{Colors.GREEN}✓ All validation checks passed{Colors.NC}")
        logger.info(f"Moving temp file to: {os.path.basename(output_file)}")
        
        # Use shutil.move for safer file operation
        shutil.move(temp_output, output_file)
        
        # Final verification that output exists
        if not os.path.exists(output_file):
            logger.error(f"{Colors.RED}✗ Failed to create final output file{Colors.NC}")
            return False
        
        logger.info(f"{Colors.GREEN}✓ Conversion successful{Colors.NC}")
        return True
        
    except Exception as e:
        logger.error(f"{Colors.RED}✗ Conversion error: {e}{Colors.NC}")
        if os.path.exists(temp_output):
            logger.info("Cleaning up temp file...")
            os.remove(temp_output)
        return False


def safe_delete_original(input_file, output_file):
    """
    Safely delete original file after verifying output
    
    Args:
        input_file (str): Original file to delete
        output_file (str): New file that should exist
        
    Returns:
        bool: True if deleted successfully
    """
    try:
        # Final safety check
        if not os.path.exists(output_file):
            logger.error(f"{Colors.RED}✗ Output file doesn't exist, NOT deleting original{Colors.NC}")
            return False
        
        # Get output file info
        output_info = get_video_info(output_file)
        if not output_info:
            logger.error(f"{Colors.RED}✗ Cannot verify output file, NOT deleting original{Colors.NC}")
            return False
        
        # Verify output is playable one more time
        is_valid, error = verify_file_integrity(output_file, stage="final_verification")
        if not is_valid:
            logger.error(f"{Colors.RED}✗ Final integrity check failed, NOT deleting original{Colors.NC}")
            return False
        
        # Everything checks out - safe to delete
        logger.info(f"Deleting original file: {os.path.basename(input_file)}")
        os.remove(input_file)
        logger.info(f"{Colors.GREEN}✓ Original file deleted successfully{Colors.NC}")
        
        return True
        
    except Exception as e:
        logger.error(f"{Colors.RED}✗ Error deleting original: {e}{Colors.NC}")
        logger.error(f"{Colors.RED}  Original file preserved for safety{Colors.NC}")
        return False


def trigger_jellyfin_scan():
    """Trigger Jellyfin library scan via API"""
    if not JELLYFIN_API_KEY:
        logger.warning("Jellyfin API key not configured, skipping scan")
        return

    try:
        import requests

        headers = {
            'X-MediaBrowser-Token': JELLYFIN_API_KEY
        }

        response = requests.post(
            f"{JELLYFIN_URL}/Library/Refresh",
            headers=headers,
            timeout=10
        )

        if response.status_code == 204:
            logger.info(f"{Colors.GREEN}✓ Jellyfin library scan triggered{Colors.NC}")
        else:
            logger.warning(f"Jellyfin scan returned status {response.status_code}")

    except ImportError:
        logger.warning("requests library not installed, skipping Jellyfin scan")
    except Exception as e:
        logger.error(f"Failed to trigger Jellyfin scan: {e}")


def get_radarr_config():
    """
    Get Radarr configuration from environment or config file

    Returns:
        dict: Radarr configuration
    """
    config = {
        'url': os.environ.get('RADARR_URL', 'http://localhost:7878'),
        'api_key': os.environ.get('RADARR_API_KEY', ''),
        'enabled': False
    }

    # Try to read from config file if not in environment (located next to this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'radarr_config.json')

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.warning(f"Could not read Radarr config file: {e}")

    config['enabled'] = bool(config['api_key'])
    return config


def get_movie_info_from_path(file_path):
    """
    Extract movie information from file path

    Args:
        file_path (str): Full path to movie file

    Returns:
        dict: Movie info including title and year
    """
    try:
        # Try to extract from parent folder name
        # Format: "Movie Name (Year)"
        parent_dir = os.path.basename(os.path.dirname(file_path))

        import re
        match = re.search(r'^(.+?)\s*\((\d{4})\)', parent_dir)

        if match:
            return {
                'title': match.group(1).strip(),
                'year': int(match.group(2))
            }

        # Fallback: just use parent dir name
        return {
            'title': parent_dir,
            'year': None
        }

    except Exception as e:
        logger.warning(f"Could not extract movie info from path: {e}")
        return None


def find_radarr_movie(movie_title, movie_year, radarr_config):
    """
    Find movie in Radarr by title and year

    Args:
        movie_title (str): Movie title
        movie_year (int): Movie year
        radarr_config (dict): Radarr configuration

    Returns:
        dict: Movie information from Radarr, or None
    """
    try:
        import requests

        headers = {
            'X-Api-Key': radarr_config['api_key']
        }

        # Search for movie
        response = requests.get(
            f"{radarr_config['url']}/api/v3/movie",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Radarr API returned status {response.status_code}")
            return None

        movies = response.json()

        # Find matching movie
        for movie in movies:
            if movie.get('title', '').lower() == movie_title.lower():
                if movie_year is None or movie.get('year') == movie_year:
                    return movie

        logger.warning(f"Movie not found in Radarr: {movie_title} ({movie_year})")
        return None

    except ImportError:
        logger.error("requests library not installed")
        return None
    except Exception as e:
        logger.error(f"Error finding movie in Radarr: {e}")
        return None


def blocklist_release_in_radarr(file_path, reason="Conversion failed - corrupted or incomplete file"):
    """
    Add failed release to Radarr blocklist and trigger re-search

    Args:
        file_path (str): Path to the failed file
        reason (str): Reason for blocklisting

    Returns:
        bool: True if successfully blocklisted
    """
    radarr_config = get_radarr_config()

    if not radarr_config['enabled']:
        logger.warning("Radarr integration not configured, skipping blocklist")
        return False

    try:
        import requests

        logger.info(f"{Colors.MAGENTA}Attempting to blocklist release in Radarr...{Colors.NC}")

        # Extract movie info from path
        movie_info = get_movie_info_from_path(file_path)
        if not movie_info:
            logger.error("Could not extract movie info from path")
            return False

        logger.info(f"Movie: {movie_info['title']} ({movie_info['year']})")

        # Find movie in Radarr
        movie = find_radarr_movie(movie_info['title'], movie_info['year'], radarr_config)
        if not movie:
            logger.error("Movie not found in Radarr")
            return False

        movie_id = movie['id']
        logger.info(f"Found movie in Radarr (ID: {movie_id})")

        headers = {
            'X-Api-Key': radarr_config['api_key'],
            'Content-Type': 'application/json'
        }

        # Get movie file details to find download ID
        response = requests.get(
            f"{radarr_config['url']}/api/v3/moviefile?movieId={movie_id}",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Could not get movie files: {response.status_code}")
            return False

        movie_files = response.json()

        # Find the specific file
        target_filename = os.path.basename(file_path)
        movie_file = None

        for mf in movie_files:
            if os.path.basename(mf.get('path', '')) == target_filename:
                movie_file = mf
                break

        if not movie_file:
            logger.warning("Could not find specific movie file in Radarr")
            # Still try to trigger re-search for the movie
            trigger_movie_search(movie_id, radarr_config)
            return True

        # Get the download ID from history
        response = requests.get(
            f"{radarr_config['url']}/api/v3/history/movie?movieId={movie_id}",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            history = response.json()

            # Find most recent download
            for entry in history:
                if entry.get('eventType') == 'grabbed':
                    download_id = entry.get('downloadId')

                    if download_id:
                        # Blocklist the release
                        blocklist_data = {
                            'movieId': movie_id,
                            'sourceTitle': entry.get('sourceTitle', 'Unknown'),
                            'quality': entry.get('quality', {}),
                            'date': entry.get('date'),
                            'reason': reason
                        }

                        response = requests.post(
                            f"{radarr_config['url']}/api/v3/blocklist",
                            headers=headers,
                            json=blocklist_data,
                            timeout=10
                        )

                        if response.status_code in [200, 201]:
                            logger.info(f"{Colors.GREEN}✓ Release added to blocklist{Colors.NC}")
                            logger.info(f"  Source: {entry.get('sourceTitle', 'Unknown')}")
                        else:
                            logger.warning(f"Could not blocklist release: {response.status_code}")

                        break

        # Trigger automatic search for a better release
        trigger_movie_search(movie_id, radarr_config)

        # Delete the bad file from Radarr
        if movie_file:
            delete_movie_file(movie_file['id'], radarr_config)

        return True

    except ImportError:
        logger.error("requests library not installed")
        return False
    except Exception as e:
        logger.error(f"Error blocklisting release: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def trigger_movie_search(movie_id, radarr_config):
    """
    Trigger automatic search for movie in Radarr

    Args:
        movie_id (int): Radarr movie ID
        radarr_config (dict): Radarr configuration

    Returns:
        bool: True if search triggered successfully
    """
    try:
        import requests

        logger.info(f"{Colors.BLUE}Triggering automatic search for better release...{Colors.NC}")

        headers = {
            'X-Api-Key': radarr_config['api_key'],
            'Content-Type': 'application/json'
        }

        command_data = {
            'name': 'MoviesSearch',
            'movieIds': [movie_id]
        }

        response = requests.post(
            f"{radarr_config['url']}/api/v3/command",
            headers=headers,
            json=command_data,
            timeout=10
        )

        if response.status_code in [200, 201]:
            logger.info(f"{Colors.GREEN}✓ Automatic search triggered{Colors.NC}")
            logger.info(f"{Colors.GREEN}  Radarr will search for a better release{Colors.NC}")
            return True
        else:
            logger.warning(f"Could not trigger search: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error triggering search: {e}")
        return False


def delete_movie_file(movie_file_id, radarr_config):
    """
    Delete movie file from Radarr

    Args:
        movie_file_id (int): Radarr movie file ID
        radarr_config (dict): Radarr configuration

    Returns:
        bool: True if deleted successfully
    """
    try:
        import requests

        logger.info(f"Removing bad file from Radarr database...")

        headers = {
            'X-Api-Key': radarr_config['api_key']
        }

        response = requests.delete(
            f"{radarr_config['url']}/api/v3/moviefile/{movie_file_id}",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"{Colors.GREEN}✓ File removed from Radarr{Colors.NC}")
            return True
        else:
            logger.warning(f"Could not remove file: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return False


def process_file(input_file):
    """
    Main processing logic for a single file with comprehensive error handling

    Args:
        input_file (str): Path to input file

    Returns:
        bool: True if processed successfully
    """
    input_path = Path(input_file)

    # Validate input
    if not input_path.exists():
        logger.error(f"{Colors.RED}File not found: {input_file}{Colors.NC}")
        return False

    if input_path.suffix.lower() != '.mkv':
        logger.info(f"{Colors.YELLOW}Not an MKV file, skipping{Colors.NC}")
        return True

    output_file = str(input_path.with_suffix('.mp4'))

    # Check if output already exists
    if os.path.exists(output_file):
        logger.info(f"{Colors.YELLOW}MP4 already exists, skipping{Colors.NC}")
        return True

    # Track if we should blocklist on failure
    should_blocklist = False
    failure_reason = ""

    try:
        # Verify input file integrity first
        logger.info(f"{Colors.BLUE}Step 1: Verifying input file{Colors.NC}")
        is_valid, error = verify_file_integrity(str(input_path), stage="input")
        if not is_valid:
            logger.error(f"{Colors.RED}✗ Input file is corrupted or unreadable{Colors.NC}")
            logger.error(f"{Colors.RED}  Cannot safely convert this file{Colors.NC}")
            should_blocklist = True
            failure_reason = f"Input file corrupted: {error}"
            return False

        # Get video info
        logger.info(f"{Colors.BLUE}Step 2: Analyzing file properties{Colors.NC}")
        logger.info(f"File: {input_path.name}")
        info = get_video_info(str(input_path))

        if not info:
            logger.error(f"{Colors.RED}Failed to get video information{Colors.NC}")
            should_blocklist = True
            failure_reason = "Cannot read video streams"
            return False

        # Log file details
        size_gb = info['size'] / (1024**3)
        duration_min = info['duration'] / 60
        logger.info(f"Codec: {info['codec']}")
        logger.info(f"Resolution: {info['width']}x{info['height']}")
        logger.info(f"Size: {size_gb:.2f} GB")
        logger.info(f"Duration: {duration_min:.1f} minutes")
        logger.info(f"Audio tracks: {info['audio_count']}")
        logger.info(f"Subtitle tracks: {info['subtitle_count']}")

        # Estimate conversion time
        logger.info(f"{Colors.BLUE}Step 3: Evaluating conversion feasibility{Colors.NC}")
        est_minutes, should_convert, reason = estimate_conversion_time(info)

        logger.info(f"Estimated time: {est_minutes:.1f} minutes")
        logger.info(f"Decision: {reason}")

        if not should_convert:
            logger.warning(f"{Colors.RED}⚠️  SKIPPING CONVERSION{Colors.NC}")
            logger.warning(f"{Colors.YELLOW}📥 Recommendation: Delete and re-download HEVC version{Colors.NC}")
            logger.warning(f"{Colors.YELLOW}   File: {input_file}{Colors.NC}")
            # Don't blocklist AV1 - just needs HEVC version
            return False

        # Perform conversion
        logger.info(f"{Colors.BLUE}Step 4: Converting to MP4{Colors.NC}")
        success = convert_to_mp4(str(input_path), output_file, info)

        if not success:
            logger.error(f"{Colors.RED}✗ Conversion failed{Colors.NC}")
            should_blocklist = True
            failure_reason = "Conversion process failed"

            # Log conversion failure
            if corruption_tracker:
                try:
                    corruption_tracker.log_corruption_event(
                        file_path=str(input_path),
                        corruption_type="conversion_failed",
                        corruption_stage="conversion",
                        error_message="Conversion process failed",
                        status="failed"
                    )
                except Exception as e:
                    logger.warning(f"Could not log to corruption tracker: {e}")

            return False

        # Safely delete original
        logger.info(f"{Colors.BLUE}Step 5: Removing original file{Colors.NC}")
        deleted = safe_delete_original(str(input_path), output_file)

        if not deleted:
            logger.warning(f"{Colors.YELLOW}⚠ Original file not deleted (safety precaution){Colors.NC}")
            logger.warning(f"{Colors.YELLOW}  Manual review recommended{Colors.NC}")
            logger.warning(f"{Colors.YELLOW}  Original: {input_file}{Colors.NC}")
            logger.warning(f"{Colors.YELLOW}  Converted: {output_file}{Colors.NC}")
            # Still return True since conversion succeeded

        # Log successful conversion
        if corruption_tracker:
            try:
                corruption_tracker.log_success_event(output_file)
                logger.info(f"{Colors.GREEN}✓ Logged successful conversion to analytics{Colors.NC}")
            except Exception as e:
                logger.warning(f"Could not log success to corruption tracker: {e}")

        return True

    except Exception as e:
        logger.error(f"{Colors.RED}Unexpected error during processing: {e}{Colors.NC}")
        should_blocklist = True
        failure_reason = f"Unexpected error: {str(e)}"
        return False

    finally:
        # If conversion failed and we should blocklist, do it now
        if should_blocklist:
            logger.info("")
            logger.info(f"{Colors.MAGENTA}{'=' * 70}{Colors.NC}")
            logger.info(f"{Colors.MAGENTA}INITIATING RADARR RECOVERY PROCESS{Colors.NC}")
            logger.info(f"{Colors.MAGENTA}{'=' * 70}{Colors.NC}")

            blocklist_success = blocklist_release_in_radarr(input_file, failure_reason)

            # Update corruption tracker with blocklist info
            if corruption_tracker:
                try:
                    # Update the last event to mark as blocklisted
                    import sqlite3
                    conn = sqlite3.connect(corruption_tracker.db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE corruption_events
                        SET blocklisted = ?, redownload_triggered = ?
                        WHERE file_path = ?
                        ORDER BY timestamp DESC LIMIT 1
                    """, (blocklist_success, blocklist_success, input_file))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.warning(f"Could not update blocklist status in tracker: {e}")

            if blocklist_success:
                logger.info(f"{Colors.GREEN}✓ Recovery process completed{Colors.NC}")
                logger.info(f"{Colors.GREEN}  - Bad release blocklisted{Colors.NC}")
                logger.info(f"{Colors.GREEN}  - Automatic search triggered{Colors.NC}")
                logger.info(f"{Colors.GREEN}  - Radarr will download better version{Colors.NC}")
            else:
                logger.warning(f"{Colors.YELLOW}⚠ Automatic recovery not available{Colors.NC}")
                logger.warning(f"{Colors.YELLOW}  Please manually delete and re-search in Radarr{Colors.NC}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_file.mkv>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    logger.info("=" * 70)
    logger.info("MKV TO MP4 CONVERSION - ENHANCED VERSION")
    logger.info(f"Safety Features: Integrity checks, size validation, smart deletion")
    logger.info("=" * 70)
    
    try:
        success = process_file(input_file)
        
        if success:
            # Trigger Jellyfin scan
            trigger_jellyfin_scan()
            logger.info("=" * 70)
            logger.info(f"{Colors.GREEN}✓ PROCESSING COMPLETED SUCCESSFULLY{Colors.NC}")
            logger.info("=" * 70)
            sys.exit(0)
        else:
            logger.info("=" * 70)
            logger.error(f"{Colors.RED}✗ PROCESSING FAILED OR SKIPPED{Colors.NC}")
            logger.info("=" * 70)
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning(f"\n{Colors.YELLOW}Conversion interrupted by user{Colors.NC}")
        logger.warning(f"{Colors.YELLOW}Cleaning up...{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        logger.error(f"{Colors.RED}Unexpected error: {e}{Colors.NC}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()