#!/usr/bin/env python3
"""
Analytics status dashboard for Claude Recall.

Provides quick overview of analytics system health and activity.

Usage:
    python3 scripts/analytics_status.py [--detailed] [--json]
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict


class AnalyticsStatus:
    """Analytics status dashboard."""

    def __init__(self, sessions_dir=None):
        """Initialize status checker."""
        if sessions_dir is None:
            sessions_dir = Path.home() / ".claude" / "context" / "sessions"

        self.sessions_dir = Path(sessions_dir)

        # Log paths
        self.telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        self.quality_log = self.sessions_dir / "quality_scores.jsonl"
        self.impact_log = self.sessions_dir / "context_impact.jsonl"
        self.check_log = self.sessions_dir / "quality_check_log.jsonl"

        # Config
        self.config_path = Path(__file__).parent.parent / "config" / "analytics_config.json"

    def load_config(self):
        """Load analytics configuration."""
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def parse_timestamp(self, timestamp_str):
        """Parse timestamp string."""
        try:
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                return datetime.fromisoformat(timestamp_str)
            else:
                return datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def count_recent_events(self, log_path, hours=24):
        """Count events in last N hours."""
        if not log_path.exists():
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        count = 0

        try:
            with open(log_path, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        timestamp = self.parse_timestamp(event.get('timestamp', ''))
                        if timestamp and timestamp >= cutoff:
                            count += 1
                    except:
                        continue
        except Exception:
            pass

        return count

    def get_telemetry_status(self):
        """Get telemetry status."""
        config = self.load_config()
        enabled = config.get("telemetry", {}).get("enabled", False)

        status = {
            "enabled": enabled,
            "log_exists": self.telemetry_log.exists(),
            "last_24h": 0,
            "total": 0,
        }

        if status["log_exists"]:
            # Count events
            status["last_24h"] = self.count_recent_events(self.telemetry_log, hours=24)

            # Total events
            try:
                with open(self.telemetry_log, 'r') as f:
                    status["total"] = sum(1 for _ in f)
            except Exception:
                pass

        return status

    def get_quality_scoring_status(self):
        """Get quality scoring status."""
        config = self.load_config()
        enabled = config.get("quality_scoring", {}).get("enabled", False)

        status = {
            "enabled": enabled,
            "log_exists": self.quality_log.exists(),
            "last_24h": 0,
            "total": 0,
            "sampling_rate": config.get("quality_scoring", {}).get("sampling_rate", 0.0),
        }

        if status["log_exists"]:
            status["last_24h"] = self.count_recent_events(self.quality_log, hours=24)

            try:
                with open(self.quality_log, 'r') as f:
                    status["total"] = sum(1 for _ in f)
            except Exception:
                pass

        return status

    def get_impact_analysis_status(self):
        """Get impact analysis status."""
        config = self.load_config()
        enabled = config.get("impact_analysis", {}).get("enabled", False)

        status = {
            "enabled": enabled,
            "log_exists": self.impact_log.exists(),
            "last_24h": 0,
            "total": 0,
        }

        if status["log_exists"]:
            status["last_24h"] = self.count_recent_events(self.impact_log, hours=24)

            try:
                with open(self.impact_log, 'r') as f:
                    status["total"] = sum(1 for _ in f)
            except Exception:
                pass

        return status

    def get_quality_checks_status(self):
        """Get quality checks status."""
        config = self.load_config()
        enabled = config.get("quality_checks", {}).get("enabled", False)

        status = {
            "enabled": enabled,
            "log_exists": self.check_log.exists(),
            "last_run": None,
            "last_result": None,
        }

        if status["log_exists"]:
            # Get most recent check
            try:
                with open(self.check_log, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        last_check = json.loads(last_line)
                        status["last_run"] = last_check.get("timestamp")
                        status["last_result"] = last_check.get("status")
            except Exception:
                pass

        return status

    def get_last_24h_metrics(self):
        """Get metrics for last 24 hours."""
        metrics = {
            "searches": 0,
            "avg_latency_ms": 0,
            "cache_hit_rate": 0,
            "issues": 0,
        }

        if not self.telemetry_log.exists():
            return metrics

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        latencies = []
        cache_hits = 0
        cache_total = 0

        try:
            with open(self.telemetry_log, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())

                        # Check timestamp
                        timestamp = self.parse_timestamp(event.get('timestamp', ''))
                        if not timestamp or timestamp < cutoff:
                            continue

                        # Count searches
                        if event.get('event_type') == 'search_completed':
                            metrics["searches"] += 1

                            # Latency
                            latency = event.get('performance', {}).get('total_latency_ms')
                            if latency:
                                latencies.append(latency)

                            # Cache hits
                            cache_hit = event.get('performance', {}).get('cache_hit')
                            if cache_hit is not None:
                                cache_total += 1
                                if cache_hit:
                                    cache_hits += 1

                    except:
                        continue
        except Exception:
            pass

        # Calculate averages
        if latencies:
            metrics["avg_latency_ms"] = round(sum(latencies) / len(latencies), 1)
        if cache_total > 0:
            metrics["cache_hit_rate"] = round(cache_hits / cache_total, 2)

        # Check for issues
        if self.check_log.exists():
            try:
                with open(self.check_log, 'r') as f:
                    for line in f:
                        try:
                            check = json.loads(line.strip())
                            timestamp = self.parse_timestamp(check.get('timestamp', ''))
                            if timestamp and timestamp >= cutoff:
                                if check.get('status') in ['warning', 'error']:
                                    metrics["issues"] += 1
                        except:
                            continue
            except Exception:
                pass

        return metrics

    def display_status(self, detailed=False):
        """Display status to console."""
        print("=" * 60)
        print("📊 Claude Recall Analytics Status")
        print("=" * 60 + "\n")

        # Telemetry
        telemetry = self.get_telemetry_status()
        icon = "✅" if telemetry["enabled"] else "⏸️"
        print(f"{icon} Telemetry: {'Enabled' if telemetry['enabled'] else 'Disabled'}")
        if telemetry["log_exists"]:
            print(f"   Events (24h): {telemetry['last_24h']}")
            print(f"   Events (total): {telemetry['total']}")

        # Quality Scoring
        quality = self.get_quality_scoring_status()
        icon = "✅" if quality["enabled"] else "⏸️"
        print(f"\n{icon} Quality Scoring: {'Enabled' if quality['enabled'] else 'Disabled'}")
        if quality["enabled"]:
            print(f"   Sampling rate: {quality['sampling_rate']:.0%}")
            if quality["log_exists"]:
                print(f"   Evaluations (24h): {quality['last_24h']}")
                print(f"   Evaluations (total): {quality['total']}")

        # Impact Analysis
        impact = self.get_impact_analysis_status()
        icon = "✅" if impact["enabled"] else "⏸️"
        print(f"\n{icon} Impact Analysis: {'Enabled' if impact['enabled'] else 'Disabled'}")
        if impact["log_exists"]:
            print(f"   Analyses (24h): {impact['last_24h']}")
            print(f"   Analyses (total): {impact['total']}")

        # Quality Checks
        checks = self.get_quality_checks_status()
        icon = "✅" if checks["enabled"] else "⏸️"
        print(f"\n{icon} Quality Checks: {'Enabled' if checks['enabled'] else 'Disabled'}")
        if checks["last_run"]:
            last_run = self.parse_timestamp(checks["last_run"])
            if last_run:
                time_ago = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
                print(f"   Last run: {time_ago:.1f} hours ago")
                if checks["last_result"]:
                    result_icon = "✅" if checks["last_result"] == "pass" else "⚠️"
                    print(f"   Last result: {result_icon} {checks['last_result']}")

        # Last 24h Metrics
        print("\n" + "-" * 60)
        print("📈 Last 24 Hours")
        print("-" * 60)

        metrics = self.get_last_24h_metrics()
        print(f"Searches: {metrics['searches']}")
        if metrics['searches'] > 0:
            print(f"Avg latency: {metrics['avg_latency_ms']:.0f}ms")
            print(f"Cache hit rate: {metrics['cache_hit_rate']:.0%}")
        if metrics['issues'] > 0:
            print(f"⚠️  Issues detected: {metrics['issues']}")
        else:
            print("✅ No issues detected")

        # Detailed mode
        if detailed:
            print("\n" + "-" * 60)
            print("📂 File Locations")
            print("-" * 60)
            print(f"Sessions dir: {self.sessions_dir}")
            print(f"Telemetry log: {self.telemetry_log}")
            print(f"Quality log: {self.quality_log}")
            print(f"Impact log: {self.impact_log}")
            print(f"Check log: {self.check_log}")
            print(f"Config: {self.config_path}")

        print("")

    def get_status_dict(self):
        """Get status as dictionary for JSON export."""
        return {
            "telemetry": self.get_telemetry_status(),
            "quality_scoring": self.get_quality_scoring_status(),
            "impact_analysis": self.get_impact_analysis_status(),
            "quality_checks": self.get_quality_checks_status(),
            "last_24h_metrics": self.get_last_24h_metrics(),
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analytics status dashboard for Claude Recall"
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    parser.add_argument(
        "--sessions-dir",
        type=str,
        metavar="PATH",
        help="Path to sessions directory (default: ~/.claude/context/sessions)",
    )

    args = parser.parse_args()

    # Initialize status checker
    sessions_dir = Path(args.sessions_dir) if args.sessions_dir else None
    status = AnalyticsStatus(sessions_dir=sessions_dir)

    try:
        if args.json:
            # JSON output
            data = status.get_status_dict()
            print(json.dumps(data, indent=2, default=str))
        else:
            # Console output
            status.display_status(detailed=args.detailed)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
