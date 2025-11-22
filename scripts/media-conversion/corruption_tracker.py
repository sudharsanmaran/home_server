#!/usr/bin/env python3
"""
Media Corruption Tracker with Analytics
Tracks DV/HDR corruption patterns, publishers, formats for analysis
"""

import os
import sqlite3
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import re


class CorruptionTracker:
    """Tracks and analyzes media file corruption patterns"""

    def __init__(self, db_path: str = "/var/log/conversions/corruption_tracker.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main corruption events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corruption_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT NOT NULL,
                movie_title TEXT,
                movie_year INTEGER,
                file_size_bytes INTEGER,
                duration_seconds REAL,

                -- Video metadata
                video_codec TEXT,
                video_profile TEXT,
                resolution TEXT,
                width INTEGER,
                height INTEGER,
                bit_depth INTEGER,
                color_space TEXT,
                color_transfer TEXT,
                color_primaries TEXT,

                -- HDR/DV metadata
                is_hdr BOOLEAN,
                is_dolby_vision BOOLEAN,
                hdr_format TEXT,
                master_display TEXT,
                max_luminance INTEGER,

                -- Audio/subtitle info
                audio_codecs TEXT,
                audio_count INTEGER,
                subtitle_count INTEGER,

                -- Release info
                release_group TEXT,
                source_type TEXT,
                release_name TEXT,

                -- Corruption details
                corruption_type TEXT,
                corruption_stage TEXT,
                error_message TEXT,
                ffmpeg_errors TEXT,

                -- Processing result
                status TEXT,
                blocklisted BOOLEAN DEFAULT 0,
                redownload_triggered BOOLEAN DEFAULT 0
            )
        """)

        # Publisher/release group statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publisher_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                release_group TEXT UNIQUE,
                total_files INTEGER DEFAULT 0,
                corrupted_files INTEGER DEFAULT 0,
                success_files INTEGER DEFAULT 0,
                corruption_rate REAL,
                last_seen DATETIME,
                first_seen DATETIME
            )
        """)

        # Format statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS format_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_codec TEXT,
                hdr_format TEXT,
                source_type TEXT,
                total_files INTEGER DEFAULT 0,
                corrupted_files INTEGER DEFAULT 0,
                corruption_rate REAL,
                last_seen DATETIME,
                UNIQUE(video_codec, hdr_format, source_type)
            )
        """)

        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_release_group
            ON corruption_events(release_group)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_codec
            ON corruption_events(video_codec)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hdr_format
            ON corruption_events(hdr_format)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status
            ON corruption_events(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON corruption_events(timestamp)
        """)

        conn.commit()
        conn.close()

    def extract_metadata(self, file_path: str) -> Dict:
        """Extract comprehensive metadata from video file using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-show_entries',
                'stream=codec_name,codec_type,profile,width,height,pix_fmt,'
                'color_space,color_transfer,color_primaries,bit_depth,'
                'bits_per_raw_sample,duration,bit_rate:stream_tags:format_tags',
                file_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return {}

            data = json.loads(result.stdout)

            # Parse streams
            video_stream = None
            audio_streams = []
            subtitle_streams = []

            for stream in data.get('streams', []):
                codec_type = stream.get('codec_type')
                if codec_type == 'video' and not video_stream:
                    video_stream = stream
                elif codec_type == 'audio':
                    audio_streams.append(stream)
                elif codec_type == 'subtitle':
                    subtitle_streams.append(stream)

            if not video_stream:
                return {}

            format_info = data.get('format', {})

            # Extract HDR/DV information
            hdr_info = self._detect_hdr_dv(video_stream, format_info)

            # Extract release info from filename/path
            release_info = self._parse_release_info(file_path)

            metadata = {
                # File info
                'file_path': file_path,
                'file_size_bytes': int(format_info.get('size', 0)),
                'duration_seconds': float(format_info.get('duration', 0)),

                # Video metadata
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'video_profile': video_stream.get('profile', ''),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'resolution': f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                'bit_depth': int(video_stream.get('bits_per_raw_sample',
                                video_stream.get('bit_depth', 8))),
                'color_space': video_stream.get('color_space', ''),
                'color_transfer': video_stream.get('color_transfer', ''),
                'color_primaries': video_stream.get('color_primaries', ''),

                # HDR/DV info
                'is_hdr': hdr_info['is_hdr'],
                'is_dolby_vision': hdr_info['is_dv'],
                'hdr_format': hdr_info['format'],
                'master_display': hdr_info.get('master_display', ''),
                'max_luminance': hdr_info.get('max_luminance', 0),

                # Audio/subtitle info
                'audio_codecs': ','.join([a.get('codec_name', '') for a in audio_streams]),
                'audio_count': len(audio_streams),
                'subtitle_count': len(subtitle_streams),

                # Release info
                'release_group': release_info['group'],
                'source_type': release_info['source'],
                'release_name': release_info['release_name'],
                'movie_title': release_info['title'],
                'movie_year': release_info['year'],
            }

            return metadata

        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return {}

    def _detect_hdr_dv(self, video_stream: Dict, format_info: Dict) -> Dict:
        """Detect HDR and Dolby Vision from stream metadata"""
        hdr_info = {
            'is_hdr': False,
            'is_dv': False,
            'format': 'SDR'
        }

        # Check color transfer for HDR
        color_transfer = video_stream.get('color_transfer', '').lower()
        if any(x in color_transfer for x in ['smpte2084', 'arib-std-b67', 'bt2020-10']):
            hdr_info['is_hdr'] = True
            hdr_info['format'] = 'HDR10'

        # Check for HLG
        if 'arib-std-b67' in color_transfer:
            hdr_info['format'] = 'HLG'

        # Check color primaries
        color_primaries = video_stream.get('color_primaries', '').lower()
        if 'bt2020' in color_primaries:
            hdr_info['is_hdr'] = True
            if hdr_info['format'] == 'SDR':
                hdr_info['format'] = 'HDR10'

        # Check for Dolby Vision
        codec_name = video_stream.get('codec_name', '').lower()
        profile = video_stream.get('profile', '').lower()

        if 'dovi' in codec_name or 'dolby' in profile:
            hdr_info['is_dv'] = True
            hdr_info['is_hdr'] = True
            hdr_info['format'] = 'Dolby Vision'

        # Check side data for HDR metadata
        side_data = video_stream.get('side_data_list', [])
        for data in side_data:
            side_type = data.get('side_data_type', '').lower()

            if 'mastering display' in side_type:
                hdr_info['is_hdr'] = True
                if hdr_info['format'] == 'SDR':
                    hdr_info['format'] = 'HDR10'
                hdr_info['master_display'] = str(data)

                # Extract max luminance if available
                if 'max_luminance' in data:
                    hdr_info['max_luminance'] = int(data['max_luminance'])

            if 'content light level' in side_type:
                hdr_info['is_hdr'] = True

            if 'dovi' in side_type or 'dolby' in side_type:
                hdr_info['is_dv'] = True
                hdr_info['is_hdr'] = True
                hdr_info['format'] = 'Dolby Vision'

        # Check format tags
        format_tags = format_info.get('tags', {})
        for key, value in format_tags.items():
            value_lower = str(value).lower()
            if 'dolby' in value_lower or 'dovi' in value_lower:
                hdr_info['is_dv'] = True
                hdr_info['is_hdr'] = True
                hdr_info['format'] = 'Dolby Vision'
            elif 'hdr' in value_lower:
                hdr_info['is_hdr'] = True
                if hdr_info['format'] == 'SDR':
                    hdr_info['format'] = 'HDR10'

        return hdr_info

    def _parse_release_info(self, file_path: str) -> Dict:
        """Parse release group, source, and title from filename"""
        filename = os.path.basename(file_path)
        parent_dir = os.path.basename(os.path.dirname(file_path))

        release_info = {
            'group': 'Unknown',
            'source': 'Unknown',
            'release_name': filename,
            'title': None,
            'year': None
        }

        # Extract movie title and year from parent directory
        # Format: "Movie Name (Year)"
        match = re.search(r'^(.+?)\s*\((\d{4})\)', parent_dir)
        if match:
            release_info['title'] = match.group(1).strip()
            release_info['year'] = int(match.group(2))
        else:
            release_info['title'] = parent_dir

        # Extract release group (usually after last dash or in brackets)
        # Examples: Movie.2024.1080p-GROUP, Movie.2024.1080p.GROUP
        group_patterns = [
            r'-([A-Za-z0-9]+)(?:\.\w+)?$',  # -GROUP.mkv
            r'\.([A-Z][A-Za-z0-9]+)(?:\.\w+)?$',  # .GROUP.mkv
            r'\[([A-Za-z0-9]+)\]',  # [GROUP]
        ]

        for pattern in group_patterns:
            match = re.search(pattern, filename)
            if match:
                release_info['group'] = match.group(1)
                break

        # Detect source type
        filename_upper = filename.upper()
        if 'REMUX' in filename_upper:
            release_info['source'] = 'REMUX'
        elif 'BLURAY' in filename_upper or 'BLU-RAY' in filename_upper:
            release_info['source'] = 'BluRay'
        elif 'WEB-DL' in filename_upper or 'WEBDL' in filename_upper:
            release_info['source'] = 'WEB-DL'
        elif 'WEBRIP' in filename_upper or 'WEB-RIP' in filename_upper:
            release_info['source'] = 'WEBRip'
        elif 'HDTV' in filename_upper:
            release_info['source'] = 'HDTV'
        elif 'DVDRIP' in filename_upper or 'DVD-RIP' in filename_upper:
            release_info['source'] = 'DVDRip'

        return release_info

    def log_corruption_event(
        self,
        file_path: str,
        corruption_type: str,
        corruption_stage: str,
        error_message: str = "",
        ffmpeg_errors: str = "",
        status: str = "corrupted",
        blocklisted: bool = False,
        redownload_triggered: bool = False
    ) -> int:
        """
        Log a corruption event to the database

        Args:
            file_path: Path to the corrupted file
            corruption_type: Type of corruption (integrity_check_failed, conversion_failed, etc.)
            corruption_stage: Stage where corruption was detected (input, output, verification)
            error_message: Human-readable error message
            ffmpeg_errors: Raw ffmpeg error output
            status: Processing status (corrupted, skipped, failed)
            blocklisted: Whether the release was blocklisted
            redownload_triggered: Whether re-download was triggered

        Returns:
            Event ID
        """
        metadata = self.extract_metadata(file_path)

        if not metadata:
            # Minimal logging if metadata extraction fails
            metadata = {
                'file_path': file_path,
                'release_name': os.path.basename(file_path),
                'release_group': 'Unknown',
                'source_type': 'Unknown',
            }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO corruption_events (
                file_path, movie_title, movie_year, file_size_bytes, duration_seconds,
                video_codec, video_profile, resolution, width, height, bit_depth,
                color_space, color_transfer, color_primaries,
                is_hdr, is_dolby_vision, hdr_format, master_display, max_luminance,
                audio_codecs, audio_count, subtitle_count,
                release_group, source_type, release_name,
                corruption_type, corruption_stage, error_message, ffmpeg_errors,
                status, blocklisted, redownload_triggered
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get('file_path', file_path),
            metadata.get('movie_title'),
            metadata.get('movie_year'),
            metadata.get('file_size_bytes', 0),
            metadata.get('duration_seconds', 0),
            metadata.get('video_codec', 'unknown'),
            metadata.get('video_profile', ''),
            metadata.get('resolution', ''),
            metadata.get('width', 0),
            metadata.get('height', 0),
            metadata.get('bit_depth', 8),
            metadata.get('color_space', ''),
            metadata.get('color_transfer', ''),
            metadata.get('color_primaries', ''),
            metadata.get('is_hdr', False),
            metadata.get('is_dolby_vision', False),
            metadata.get('hdr_format', 'SDR'),
            metadata.get('master_display', ''),
            metadata.get('max_luminance', 0),
            metadata.get('audio_codecs', ''),
            metadata.get('audio_count', 0),
            metadata.get('subtitle_count', 0),
            metadata.get('release_group', 'Unknown'),
            metadata.get('source_type', 'Unknown'),
            metadata.get('release_name', os.path.basename(file_path)),
            corruption_type,
            corruption_stage,
            error_message,
            ffmpeg_errors,
            status,
            blocklisted,
            redownload_triggered
        ))

        event_id = cursor.lastrowid

        # Update statistics
        self._update_publisher_stats(cursor, metadata.get('release_group', 'Unknown'), True)
        self._update_format_stats(
            cursor,
            metadata.get('video_codec', 'unknown'),
            metadata.get('hdr_format', 'SDR'),
            metadata.get('source_type', 'Unknown'),
            True
        )

        conn.commit()
        conn.close()

        return event_id

    def log_success_event(self, file_path: str) -> int:
        """Log a successful conversion event"""
        metadata = self.extract_metadata(file_path)

        if not metadata:
            return -1

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO corruption_events (
                file_path, movie_title, movie_year, file_size_bytes, duration_seconds,
                video_codec, video_profile, resolution, width, height, bit_depth,
                color_space, color_transfer, color_primaries,
                is_hdr, is_dolby_vision, hdr_format, master_display, max_luminance,
                audio_codecs, audio_count, subtitle_count,
                release_group, source_type, release_name,
                corruption_type, corruption_stage, error_message,
                status, blocklisted, redownload_triggered
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.get('file_path'),
            metadata.get('movie_title'),
            metadata.get('movie_year'),
            metadata.get('file_size_bytes', 0),
            metadata.get('duration_seconds', 0),
            metadata.get('video_codec'),
            metadata.get('video_profile', ''),
            metadata.get('resolution'),
            metadata.get('width'),
            metadata.get('height'),
            metadata.get('bit_depth', 8),
            metadata.get('color_space', ''),
            metadata.get('color_transfer', ''),
            metadata.get('color_primaries', ''),
            metadata.get('is_hdr', False),
            metadata.get('is_dolby_vision', False),
            metadata.get('hdr_format', 'SDR'),
            metadata.get('master_display', ''),
            metadata.get('max_luminance', 0),
            metadata.get('audio_codecs'),
            metadata.get('audio_count'),
            metadata.get('subtitle_count'),
            metadata.get('release_group'),
            metadata.get('source_type'),
            metadata.get('release_name'),
            'none',
            'completed',
            '',
            'success',
            False,
            False
        ))

        event_id = cursor.lastrowid

        # Update statistics
        self._update_publisher_stats(cursor, metadata.get('release_group'), False)
        self._update_format_stats(
            cursor,
            metadata.get('video_codec'),
            metadata.get('hdr_format'),
            metadata.get('source_type'),
            False
        )

        conn.commit()
        conn.close()

        return event_id

    def _update_publisher_stats(self, cursor, release_group: str, is_corrupted: bool):
        """Update publisher statistics"""
        corrupted_val = 1 if is_corrupted else 0
        success_val = 0 if is_corrupted else 1
        cursor.execute("""
            INSERT INTO publisher_stats (release_group, total_files, corrupted_files, success_files, first_seen, last_seen)
            VALUES (?, 1, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(release_group) DO UPDATE SET
                total_files = total_files + 1,
                corrupted_files = corrupted_files + ?,
                success_files = success_files + ?,
                corruption_rate = CAST(corrupted_files AS REAL) / total_files * 100,
                last_seen = datetime('now')
        """, (release_group, corrupted_val, success_val, corrupted_val, success_val))

    def _update_format_stats(self, cursor, codec: str, hdr_format: str, source: str, is_corrupted: bool):
        """Update format statistics"""
        cursor.execute("""
            INSERT INTO format_stats (video_codec, hdr_format, source_type, total_files, corrupted_files, last_seen)
            VALUES (?, ?, ?, 1, ?, datetime('now'))
            ON CONFLICT(video_codec, hdr_format, source_type) DO UPDATE SET
                total_files = total_files + 1,
                corrupted_files = corrupted_files + ?,
                corruption_rate = CAST(corrupted_files AS REAL) / total_files * 100,
                last_seen = datetime('now')
        """, (codec, hdr_format, source, 1 if is_corrupted else 0, 1 if is_corrupted else 0))


def main():
    """Test the corruption tracker"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 corruption_tracker.py <video_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    tracker = CorruptionTracker()

    print("Extracting metadata...")
    metadata = tracker.extract_metadata(file_path)

    print("\n" + "="*70)
    print("METADATA EXTRACTION RESULTS")
    print("="*70)

    for key, value in metadata.items():
        print(f"{key:25s}: {value}")

    print("\nTest logging corruption event...")
    event_id = tracker.log_corruption_event(
        file_path,
        corruption_type="test_corruption",
        corruption_stage="test",
        error_message="This is a test",
        status="test"
    )

    print(f"✓ Logged event ID: {event_id}")


if __name__ == "__main__":
    main()
