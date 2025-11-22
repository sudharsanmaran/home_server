#!/usr/bin/env python3
"""
Corruption Analytics Dashboard
Query and analyze media corruption patterns
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import json


class CorruptionAnalytics:
    """Analytics tool for querying corruption patterns"""

    def __init__(self, db_path: str = "/var/log/conversions/corruption_tracker.db"):
        self.db_path = db_path
        if not Path(db_path).exists():
            print(f"Error: Database not found at {db_path}")
            print("Run some conversions first to generate data.")
            exit(1)

    def _execute_query(self, query: str, params: tuple = ()):
        """Execute a query and return results"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    def _print_table(self, headers: list, rows: list, title: str = None):
        """Print results as a formatted table"""
        if title:
            print("\n" + "=" * 80)
            print(title.center(80))
            print("=" * 80)

        if not rows:
            print("\n  No data found.")
            return

        # Calculate column widths
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Print header
        print()
        header_line = "  ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
        print("  " + header_line)
        print("  " + "-" * len(header_line))

        # Print rows
        for row in rows:
            row_line = "  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
            print("  " + row_line)

        print()

    def summary(self):
        """Show overall corruption summary"""
        # Total files processed
        result = self._execute_query("""
            SELECT
                COUNT(*) as total_files,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted_files,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_files,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate
            FROM corruption_events
        """)

        if result:
            row = result[0]
            print("\n" + "=" * 80)
            print("OVERALL SUMMARY".center(80))
            print("=" * 80)
            print(f"  Total Files Processed:    {row['total_files']}")
            print(f"  Successful Conversions:   {row['success_files']}")
            print(f"  Corrupted/Failed Files:   {row['corrupted_files']}")
            print(f"  Overall Corruption Rate:  {row['corruption_rate']}%")
            print()

        # HDR/DV statistics
        result = self._execute_query("""
            SELECT
                hdr_format,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate
            FROM corruption_events
            WHERE hdr_format IS NOT NULL AND hdr_format != ''
            GROUP BY hdr_format
            ORDER BY corruption_rate DESC
        """)

        if result:
            headers = ["HDR Format", "Total", "Corrupted", "Corruption Rate"]
            rows = [[r['hdr_format'], r['total'], r['corrupted'], f"{r['corruption_rate']}%"] for r in result]
            self._print_table(headers, rows, "HDR/DV CORRUPTION RATES")

        # Recent activity
        result = self._execute_query("""
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM corruption_events
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """)

        if result:
            headers = ["Date", "Total", "Success", "Failed"]
            rows = [[r['date'], r['total'], r['success'], r['failed']] for r in result]
            self._print_table(headers, rows, "LAST 7 DAYS ACTIVITY")

    def worst_publishers(self, limit: int = 20):
        """Show publishers with highest corruption rates"""
        result = self._execute_query("""
            SELECT
                release_group,
                COUNT(*) as total_files,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted_files,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_files,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate
            FROM corruption_events
            WHERE release_group IS NOT NULL AND release_group != 'Unknown'
            GROUP BY release_group
            HAVING COUNT(*) >= 2
            ORDER BY corruption_rate DESC, total_files DESC
            LIMIT ?
        """, (limit,))

        headers = ["Publisher/Group", "Total", "Corrupted", "Success", "Corruption Rate"]
        rows = [[r['release_group'], r['total_files'], r['corrupted_files'],
                 r['success_files'], f"{r['corruption_rate']}%"] for r in result]
        self._print_table(headers, rows, f"TOP {limit} WORST PUBLISHERS (min 2 files)")

    def best_publishers(self, limit: int = 20):
        """Show publishers with best success rates"""
        result = self._execute_query("""
            SELECT
                release_group,
                COUNT(*) as total_files,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted_files,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_files,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate
            FROM corruption_events
            WHERE release_group IS NOT NULL AND release_group != 'Unknown'
            GROUP BY release_group
            HAVING COUNT(*) >= 5
            ORDER BY corruption_rate ASC, total_files DESC
            LIMIT ?
        """, (limit,))

        headers = ["Publisher/Group", "Total", "Corrupted", "Success", "Corruption Rate"]
        rows = [[r['release_group'], r['total_files'], r['corrupted_files'],
                 r['success_files'], f"{r['corruption_rate']}%"] for r in result]
        self._print_table(headers, rows, f"TOP {limit} BEST PUBLISHERS (min 5 files)")

    def format_analysis(self):
        """Analyze corruption by video format"""
        result = self._execute_query("""
            SELECT
                video_codec,
                hdr_format,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate,
                ROUND(AVG(file_size_bytes) / 1024.0 / 1024.0 / 1024.0, 2) as avg_size_gb
            FROM corruption_events
            WHERE video_codec IS NOT NULL AND video_codec != 'unknown'
            GROUP BY video_codec, hdr_format
            ORDER BY corruption_rate DESC, total DESC
        """)

        headers = ["Codec", "HDR Format", "Total", "Corrupted", "Rate", "Avg Size (GB)"]
        rows = [[r['video_codec'], r['hdr_format'] or 'SDR', r['total'], r['corrupted'],
                 f"{r['corruption_rate']}%", r['avg_size_gb']] for r in result]
        self._print_table(headers, rows, "CORRUPTION BY VIDEO FORMAT")

    def source_analysis(self):
        """Analyze corruption by source type"""
        result = self._execute_query("""
            SELECT
                source_type,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate
            FROM corruption_events
            WHERE source_type IS NOT NULL AND source_type != 'Unknown'
            GROUP BY source_type
            ORDER BY corruption_rate DESC
        """)

        headers = ["Source Type", "Total", "Corrupted", "Success", "Corruption Rate"]
        rows = [[r['source_type'], r['total'], r['corrupted'], r['success'],
                 f"{r['corruption_rate']}%"] for r in result]
        self._print_table(headers, rows, "CORRUPTION BY SOURCE TYPE")

    def hdr_dv_analysis(self):
        """Detailed HDR and Dolby Vision analysis"""
        result = self._execute_query("""
            SELECT
                is_hdr,
                is_dolby_vision,
                hdr_format,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate
            FROM corruption_events
            GROUP BY is_hdr, is_dolby_vision, hdr_format
            ORDER BY corruption_rate DESC
        """)

        headers = ["HDR", "Dolby Vision", "Format", "Total", "Corrupted", "Rate"]
        rows = [[
            "Yes" if r['is_hdr'] else "No",
            "Yes" if r['is_dolby_vision'] else "No",
            r['hdr_format'] or 'SDR',
            r['total'],
            r['corrupted'],
            f"{r['corruption_rate']}%"
        ] for r in result]
        self._print_table(headers, rows, "HDR/DOLBY VISION DETAILED ANALYSIS")

    def corruption_types(self):
        """Show breakdown of corruption types"""
        result = self._execute_query("""
            SELECT
                corruption_type,
                corruption_stage,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM corruption_events WHERE status != 'success'), 2) as percentage
            FROM corruption_events
            WHERE status != 'success'
            GROUP BY corruption_type, corruption_stage
            ORDER BY count DESC
        """)

        headers = ["Corruption Type", "Stage", "Count", "Percentage"]
        rows = [[r['corruption_type'], r['corruption_stage'], r['count'],
                 f"{r['percentage']}%"] for r in result]
        self._print_table(headers, rows, "CORRUPTION TYPES BREAKDOWN")

    def recent_corruptions(self, limit: int = 20):
        """Show recent corruption events"""
        result = self._execute_query("""
            SELECT
                datetime(timestamp, 'localtime') as time,
                movie_title,
                release_group,
                video_codec,
                hdr_format,
                source_type,
                corruption_type,
                blocklisted
            FROM corruption_events
            WHERE status != 'success'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        headers = ["Time", "Movie", "Publisher", "Codec", "HDR", "Source", "Type", "Blocklisted"]
        rows = [[
            r['time'],
            (r['movie_title'] or 'Unknown')[:30],
            r['release_group'][:15],
            r['video_codec'],
            r['hdr_format'] or 'SDR',
            r['source_type'],
            r['corruption_type'],
            "Yes" if r['blocklisted'] else "No"
        ] for r in result]
        self._print_table(headers, rows, f"LAST {limit} CORRUPTED FILES")

    def search_publisher(self, publisher: str):
        """Search for a specific publisher's history"""
        result = self._execute_query("""
            SELECT
                datetime(timestamp, 'localtime') as time,
                movie_title,
                video_codec,
                hdr_format,
                source_type,
                resolution,
                status,
                corruption_type,
                ROUND(file_size_bytes / 1024.0 / 1024.0 / 1024.0, 2) as size_gb
            FROM corruption_events
            WHERE release_group LIKE ?
            ORDER BY timestamp DESC
        """, (f"%{publisher}%",))

        if not result:
            print(f"\nNo files found for publisher: {publisher}")
            return

        # Summary for this publisher
        total = len(result)
        corrupted = sum(1 for r in result if r['status'] in ['corrupted', 'failed'])
        success = sum(1 for r in result if r['status'] == 'success')
        rate = (corrupted / total * 100) if total > 0 else 0

        print("\n" + "=" * 80)
        print(f"PUBLISHER: {publisher}".center(80))
        print("=" * 80)
        print(f"  Total Files:        {total}")
        print(f"  Successful:         {success}")
        print(f"  Corrupted/Failed:   {corrupted}")
        print(f"  Corruption Rate:    {rate:.2f}%")
        print()

        headers = ["Time", "Movie", "Codec", "HDR", "Source", "Resolution", "Size (GB)", "Status", "Issue"]
        rows = [[
            r['time'],
            (r['movie_title'] or 'Unknown')[:25],
            r['video_codec'],
            r['hdr_format'] or 'SDR',
            r['source_type'],
            r['resolution'],
            r['size_gb'],
            r['status'],
            r['corruption_type'] or '-'
        ] for r in result]
        self._print_table(headers, rows, "DETAILED HISTORY")

    def success_summary(self):
        """Show successful conversion statistics"""
        result = self._execute_query("""
            SELECT
                COUNT(*) as total_success,
                COUNT(DISTINCT release_group) as unique_publishers,
                SUM(CASE WHEN is_hdr = 1 THEN 1 ELSE 0 END) as hdr_success,
                SUM(CASE WHEN is_dolby_vision = 1 THEN 1 ELSE 0 END) as dv_success,
                ROUND(AVG(file_size_bytes) / 1024.0 / 1024.0 / 1024.0, 2) as avg_size_gb,
                ROUND(AVG(duration_seconds) / 60.0, 2) as avg_duration_min
            FROM corruption_events
            WHERE status = 'success'
        """)

        if result:
            row = result[0]
            print("\n" + "=" * 80)
            print("SUCCESS SUMMARY".center(80))
            print("=" * 80)
            print(f"  Total Successful Conversions:  {row['total_success']}")
            print(f"  Unique Publishers:             {row['unique_publishers']}")
            print(f"  HDR Successes:                 {row['hdr_success']}")
            print(f"  Dolby Vision Successes:        {row['dv_success']}")
            print(f"  Average File Size:             {row['avg_size_gb']} GB")
            print(f"  Average Duration:              {row['avg_duration_min']} minutes")
            print()

    def recommended_publishers(self, min_files: int = 5, max_corruption_rate: float = 5.0):
        """
        Show recommended publishers for Radarr preferred words

        Args:
            min_files: Minimum number of files required for recommendation
            max_corruption_rate: Maximum acceptable corruption rate (%)
        """
        result = self._execute_query("""
            SELECT
                release_group,
                COUNT(*) as total_files,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_files,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as corrupted_files,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate,
                ROUND(AVG(file_size_bytes) / 1024.0 / 1024.0 / 1024.0, 2) as avg_size_gb
            FROM corruption_events
            WHERE release_group IS NOT NULL AND release_group != 'Unknown'
            GROUP BY release_group
            HAVING COUNT(*) >= ? AND corruption_rate <= ?
            ORDER BY success_files DESC, corruption_rate ASC
        """, (min_files, max_corruption_rate))

        headers = ["Publisher/Group", "Total", "Success", "Failed", "Rate", "Avg Size (GB)"]
        rows = [[r['release_group'], r['total_files'], r['success_files'],
                 r['corrupted_files'], f"{r['corruption_rate']}%", r['avg_size_gb']] for r in result]

        title = f"RECOMMENDED PUBLISHERS (min {min_files} files, max {max_corruption_rate}% failure)"
        self._print_table(headers, rows, title)

        if result:
            print("\n" + "=" * 80)
            print("RADARR CONFIGURATION SUGGESTIONS")
            print("=" * 80)
            print("\nAdd these publishers to Radarr Preferred Words:")
            print("(Settings → Profiles → Release Profiles → Preferred)")
            print()
            for r in result[:10]:  # Top 10
                print(f"  {r['release_group']:30s} +10")
            print("\nOr use must-contain restriction to only download from these groups.")
            print()

    def publisher_quality_score(self, limit: int = 50):
        """
        Show publisher quality scores based on success rate and file quality
        """
        result = self._execute_query("""
            SELECT
                release_group,
                COUNT(*) as total_files,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_files,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as success_rate,
                ROUND(AVG(CASE WHEN status = 'success' THEN file_size_bytes ELSE NULL END) / 1024.0 / 1024.0 / 1024.0, 2) as avg_size_gb,
                SUM(CASE WHEN status = 'success' AND is_hdr = 1 THEN 1 ELSE 0 END) as hdr_count,
                SUM(CASE WHEN status = 'success' AND is_dolby_vision = 1 THEN 1 ELSE 0 END) as dv_count,
                -- Quality score: success_rate * (1 + hdr_bonus)
                ROUND(
                    (CAST(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100) *
                    (1.0 + (CAST(SUM(CASE WHEN status = 'success' AND is_hdr = 1 THEN 1 ELSE 0 END) AS REAL) /
                            NULLIF(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), 0) * 0.2))
                , 2) as quality_score
            FROM corruption_events
            WHERE release_group IS NOT NULL AND release_group != 'Unknown'
            GROUP BY release_group
            HAVING COUNT(*) >= 3
            ORDER BY quality_score DESC, total_files DESC
            LIMIT ?
        """, (limit,))

        headers = ["Publisher/Group", "Total", "Success", "Success Rate", "Quality Score", "HDR", "DV", "Avg Size"]
        rows = [[
            r['release_group'],
            r['total_files'],
            r['success_files'],
            f"{r['success_rate']}%",
            r['quality_score'],
            r['hdr_count'],
            r['dv_count'],
            f"{r['avg_size_gb']} GB"
        ] for r in result]

        self._print_table(headers, rows, f"TOP {limit} PUBLISHERS BY QUALITY SCORE (min 3 files)")

    def hdr_dv_reliable_publishers(self, min_files: int = 3):
        """Show publishers most reliable for HDR/DV content"""
        result = self._execute_query("""
            SELECT
                release_group,
                COUNT(*) as total_hdr_files,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_files,
                SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) as failed_files,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as success_rate,
                hdr_format
            FROM corruption_events
            WHERE (is_hdr = 1 OR is_dolby_vision = 1)
                  AND release_group IS NOT NULL
                  AND release_group != 'Unknown'
            GROUP BY release_group, hdr_format
            HAVING COUNT(*) >= ?
            ORDER BY success_rate DESC, total_hdr_files DESC
        """, (min_files,))

        headers = ["Publisher/Group", "HDR Format", "Total", "Success", "Failed", "Success Rate"]
        rows = [[
            r['release_group'],
            r['hdr_format'],
            r['total_hdr_files'],
            r['success_files'],
            r['failed_files'],
            f"{r['success_rate']}%"
        ] for r in result]

        self._print_table(headers, rows, f"MOST RELIABLE HDR/DV PUBLISHERS (min {min_files} files)")

    def export_radarr_config(self, output_file: str, min_files: int = 5, max_corruption_rate: float = 5.0):
        """
        Export Radarr-compatible preferred publishers list

        Args:
            output_file: Output filename (.txt or .json)
            min_files: Minimum files required
            max_corruption_rate: Maximum acceptable corruption rate
        """
        result = self._execute_query("""
            SELECT
                release_group,
                COUNT(*) as total_files,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_files,
                ROUND(
                    CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                    COUNT(*) * 100, 2
                ) as corruption_rate
            FROM corruption_events
            WHERE release_group IS NOT NULL AND release_group != 'Unknown'
            GROUP BY release_group
            HAVING COUNT(*) >= ? AND corruption_rate <= ?
            ORDER BY success_files DESC, corruption_rate ASC
        """, (min_files, max_corruption_rate))

        publishers = [dict(row) for row in result]

        if output_file.endswith('.json'):
            # JSON format for API import
            config = {
                "preferred_publishers": [
                    {
                        "name": p['release_group'],
                        "score": 10,
                        "total_files": p['total_files'],
                        "success_files": p['success_files'],
                        "corruption_rate": p['corruption_rate']
                    } for p in publishers
                ],
                "generated": datetime.now().isoformat(),
                "criteria": {
                    "min_files": min_files,
                    "max_corruption_rate": max_corruption_rate
                }
            }
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2)
        else:
            # Plain text format for manual copy-paste
            with open(output_file, 'w') as f:
                f.write("# Recommended Publishers for Radarr\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Criteria: min {min_files} files, max {max_corruption_rate}% corruption\n")
                f.write(f"# Total publishers: {len(publishers)}\n")
                f.write("#\n")
                f.write("# Add to Radarr → Settings → Profiles → Release Profiles → Preferred\n")
                f.write("#\n\n")

                for p in publishers:
                    f.write(f"{p['release_group']:30s} +10  # {p['success_files']}/{p['total_files']} success, {p['corruption_rate']}% fail\n")

                f.write("\n# Avoid these (high corruption rate):\n")

                # Also include worst publishers to avoid
                bad_result = self._execute_query("""
                    SELECT
                        release_group,
                        COUNT(*) as total_files,
                        ROUND(
                            CAST(SUM(CASE WHEN status = 'corrupted' OR status = 'failed' THEN 1 ELSE 0 END) AS REAL) /
                            COUNT(*) * 100, 2
                        ) as corruption_rate
                    FROM corruption_events
                    WHERE release_group IS NOT NULL AND release_group != 'Unknown'
                    GROUP BY release_group
                    HAVING COUNT(*) >= 2 AND corruption_rate > 50
                    ORDER BY corruption_rate DESC
                """)

                for p in bad_result:
                    f.write(f"# {p['release_group']:30s} -100  # {p['corruption_rate']}% failure rate\n")

        print(f"\n✓ Exported Radarr configuration to {output_file}")
        print(f"  Recommended publishers: {len(publishers)}")

    def export_json(self, output_file: str):
        """Export all data to JSON for external analysis"""
        result = self._execute_query("""
            SELECT * FROM corruption_events
            ORDER BY timestamp DESC
        """)

        data = [dict(row) for row in result]

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        print(f"\n✓ Exported {len(data)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze media corruption patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s summary                    # Show overall summary
  %(prog)s success-summary            # Show successful conversions stats
  %(prog)s worst-publishers           # Show publishers with highest corruption
  %(prog)s best-publishers            # Show most reliable publishers
  %(prog)s recommended                # Show recommended publishers for Radarr
  %(prog)s quality-scores             # Show quality scores for all publishers
  %(prog)s hdr-reliable               # Show most reliable HDR/DV publishers
  %(prog)s formats                    # Analyze by video format
  %(prog)s hdr                        # Detailed HDR/DV analysis
  %(prog)s search PUBLISHER           # Search for specific publisher
  %(prog)s export data.json           # Export all data to JSON
  %(prog)s export-radarr config.txt   # Export Radarr preferred publishers list
        """
    )

    parser.add_argument('command', choices=[
        'summary', 'worst-publishers', 'best-publishers',
        'formats', 'sources', 'hdr', 'corruption-types',
        'recent', 'search', 'export', 'all',
        'success-summary', 'recommended', 'quality-scores',
        'hdr-reliable', 'export-radarr'
    ], help='Command to run')

    parser.add_argument('args', nargs='*', help='Additional arguments for command')

    parser.add_argument('--db', default='/var/log/conversions/corruption_tracker.db',
                        help='Path to corruption tracker database')

    parser.add_argument('--limit', type=int, default=20,
                        help='Limit for list results (default: 20)')

    args = parser.parse_args()

    analytics = CorruptionAnalytics(args.db)

    if args.command == 'summary':
        analytics.summary()

    elif args.command == 'success-summary':
        analytics.success_summary()

    elif args.command == 'worst-publishers':
        analytics.worst_publishers(args.limit)

    elif args.command == 'best-publishers':
        analytics.best_publishers(args.limit)

    elif args.command == 'recommended':
        analytics.recommended_publishers()

    elif args.command == 'quality-scores':
        analytics.publisher_quality_score(args.limit)

    elif args.command == 'hdr-reliable':
        analytics.hdr_dv_reliable_publishers()

    elif args.command == 'formats':
        analytics.format_analysis()

    elif args.command == 'sources':
        analytics.source_analysis()

    elif args.command == 'hdr':
        analytics.hdr_dv_analysis()

    elif args.command == 'corruption-types':
        analytics.corruption_types()

    elif args.command == 'recent':
        analytics.recent_corruptions(args.limit)

    elif args.command == 'search':
        if not args.args:
            print("Error: Please provide a publisher name to search")
            exit(1)
        analytics.search_publisher(args.args[0])

    elif args.command == 'export':
        if not args.args:
            print("Error: Please provide an output filename")
            exit(1)
        analytics.export_json(args.args[0])

    elif args.command == 'export-radarr':
        if not args.args:
            print("Error: Please provide an output filename")
            exit(1)
        analytics.export_radarr_config(args.args[0])

    elif args.command == 'all':
        analytics.summary()
        analytics.success_summary()
        analytics.recommended_publishers()
        analytics.worst_publishers(args.limit)
        analytics.best_publishers(args.limit)
        analytics.publisher_quality_score(args.limit)
        analytics.format_analysis()
        analytics.hdr_dv_analysis()
        analytics.hdr_dv_reliable_publishers()
        analytics.source_analysis()
        analytics.corruption_types()
        analytics.recent_corruptions(args.limit)


if __name__ == "__main__":
    main()
