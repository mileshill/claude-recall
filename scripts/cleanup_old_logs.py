#!/usr/bin/env python3
"""
Log cleanup utility for Claude Recall Analytics.

Removes log entries older than the retention period to manage disk space.

Usage:
    python3 scripts/cleanup_old_logs.py [--retention-days 90] [--dry-run] [--backup]
"""

import json
import argparse
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta


class LogCleaner:
    """Handles log cleanup and rotation."""

    def __init__(self, sessions_dir=None, retention_days=90):
        """
        Initialize log cleaner.

        Args:
            sessions_dir: Path to sessions directory
            retention_days: Number of days to retain logs
        """
        if sessions_dir is None:
            sessions_dir = Path.home() / ".claude" / "context" / "sessions"

        self.sessions_dir = Path(sessions_dir)
        self.retention_days = retention_days
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        self.log_files = [
            "recall_analytics.jsonl",
            "quality_scores.jsonl",
            "context_impact.jsonl",
            "quality_check_log.jsonl",
            "quality_alerts.jsonl",
        ]

    def parse_timestamp(self, timestamp_str):
        """Parse timestamp string to datetime."""
        try:
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                return datetime.fromisoformat(timestamp_str)
            else:
                return datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def analyze_log(self, log_path):
        """
        Analyze log file.

        Returns:
            Dictionary with statistics
        """
        if not log_path.exists():
            return None

        stats = {
            "total_entries": 0,
            "old_entries": 0,
            "new_entries": 0,
            "file_size_bytes": log_path.stat().st_size,
            "oldest_entry": None,
            "newest_entry": None,
        }

        try:
            with open(log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        stats["total_entries"] += 1

                        # Parse timestamp
                        timestamp_str = entry.get('timestamp', '')
                        if timestamp_str:
                            timestamp = self.parse_timestamp(timestamp_str)
                            if timestamp:
                                # Track oldest/newest
                                if stats["oldest_entry"] is None or timestamp < stats["oldest_entry"]:
                                    stats["oldest_entry"] = timestamp
                                if stats["newest_entry"] is None or timestamp > stats["newest_entry"]:
                                    stats["newest_entry"] = timestamp

                                # Count old vs new
                                if timestamp < self.cutoff_date:
                                    stats["old_entries"] += 1
                                else:
                                    stats["new_entries"] += 1
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"Error analyzing {log_path}: {e}", file=sys.stderr)
            return None

        return stats

    def clean_log(self, log_path, dry_run=False, backup=True):
        """
        Clean old entries from log file.

        Args:
            log_path: Path to log file
            dry_run: If True, don't actually modify files
            backup: If True, backup before modifying

        Returns:
            Number of entries removed
        """
        if not log_path.exists():
            return 0

        # Read all entries
        entries_to_keep = []
        entries_removed = 0

        try:
            with open(log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)

                        # Parse timestamp
                        timestamp_str = entry.get('timestamp', '')
                        if timestamp_str:
                            timestamp = self.parse_timestamp(timestamp_str)
                            if timestamp and timestamp >= self.cutoff_date:
                                entries_to_keep.append(line)
                            else:
                                entries_removed += 1
                        else:
                            # Keep entries without timestamps
                            entries_to_keep.append(line)

                    except json.JSONDecodeError:
                        # Keep malformed entries (don't delete data we can't parse)
                        entries_to_keep.append(line)

        except Exception as e:
            print(f"Error reading {log_path}: {e}", file=sys.stderr)
            return 0

        # If dry run, just report
        if dry_run:
            return entries_removed

        # Backup if requested
        if backup and entries_removed > 0:
            backup_path = log_path.with_suffix(log_path.suffix + '.backup')
            try:
                shutil.copy2(log_path, backup_path)
            except Exception as e:
                print(f"Warning: Backup failed for {log_path}: {e}", file=sys.stderr)
                # Continue anyway

        # Write cleaned log
        if entries_removed > 0:
            try:
                with open(log_path, 'w') as f:
                    for line in entries_to_keep:
                        f.write(line + '\n')
            except Exception as e:
                print(f"Error writing {log_path}: {e}", file=sys.stderr)
                return 0

        return entries_removed

    def cleanup_all(self, dry_run=False, backup=True):
        """
        Clean all log files.

        Args:
            dry_run: If True, don't actually modify files
            backup: If True, backup before modifying

        Returns:
            Dictionary with results
        """
        results = {
            "total_removed": 0,
            "files_cleaned": 0,
            "space_saved_bytes": 0,
        }

        print("=" * 60)
        print(f"Log Cleanup - Retention: {self.retention_days} days")
        print(f"Cutoff date: {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if dry_run:
            print("DRY RUN - No files will be modified")
        print("=" * 60 + "\n")

        for log_file in self.log_files:
            log_path = self.sessions_dir / log_file

            if not log_path.exists():
                print(f"⏭️  {log_file}: Not found")
                continue

            # Analyze before cleanup
            stats = self.analyze_log(log_path)
            if stats is None:
                continue

            print(f"\n📄 {log_file}")
            print(f"   Total entries: {stats['total_entries']}")
            print(f"   Old entries: {stats['old_entries']}")
            print(f"   New entries: {stats['new_entries']}")
            print(f"   File size: {stats['file_size_bytes']:,} bytes")

            if stats['oldest_entry']:
                print(f"   Oldest: {stats['oldest_entry'].strftime('%Y-%m-%d')}")
            if stats['newest_entry']:
                print(f"   Newest: {stats['newest_entry'].strftime('%Y-%m-%d')}")

            # Clean
            if stats['old_entries'] > 0:
                removed = self.clean_log(log_path, dry_run=dry_run, backup=backup)
                if removed > 0:
                    # Estimate space saved
                    space_saved = int(stats['file_size_bytes'] * (removed / stats['total_entries']))
                    results["total_removed"] += removed
                    results["files_cleaned"] += 1
                    results["space_saved_bytes"] += space_saved

                    if dry_run:
                        print(f"   Would remove: {removed} entries (~{space_saved:,} bytes)")
                    else:
                        print(f"   ✅ Removed: {removed} entries (~{space_saved:,} bytes)")
                        if backup:
                            print(f"   📦 Backup: {log_file}.backup")
            else:
                print("   ✅ No cleanup needed")

        # Summary
        print("\n" + "=" * 60)
        print("Cleanup Summary")
        print("=" * 60)
        print(f"Files cleaned: {results['files_cleaned']}")
        print(f"Entries removed: {results['total_removed']}")
        print(f"Space saved: {results['space_saved_bytes']:,} bytes ({results['space_saved_bytes']/1024/1024:.2f} MB)")

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean old entries from recall analytics logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Clean logs older than 90 days
  %(prog)s --retention-days 30      # Clean logs older than 30 days
  %(prog)s --dry-run                # Preview what would be cleaned
  %(prog)s --no-backup              # Don't create backups

Scheduled cleanup (cron):
  # Monthly cleanup (keep 90 days)
  0 0 1 * * python3 /path/to/scripts/cleanup_old_logs.py
        """,
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=90,
        metavar="DAYS",
        help="Number of days to retain logs (default: 90)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleanup without modifying files",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup files",
    )

    parser.add_argument(
        "--sessions-dir",
        type=str,
        metavar="PATH",
        help="Path to sessions directory (default: ~/.claude/context/sessions)",
    )

    args = parser.parse_args()

    # Initialize cleaner
    sessions_dir = Path(args.sessions_dir) if args.sessions_dir else None
    cleaner = LogCleaner(
        sessions_dir=sessions_dir,
        retention_days=args.retention_days,
    )

    # Run cleanup
    try:
        results = cleaner.cleanup_all(
            dry_run=args.dry_run,
            backup=not args.no_backup,
        )

        if args.dry_run:
            print("\nℹ️  This was a dry run - no files were modified")
            print("   Run without --dry-run to perform cleanup")

        return 0

    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup cancelled by user")
        sys.exit(1)
