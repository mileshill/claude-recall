#!/usr/bin/env python3
"""
CLI tool for running quality checks on recall analytics.

Usage:
    python3 scripts/run_quality_checks.py [options]

Examples:
    # Run all checks
    python3 scripts/run_quality_checks.py

    # Run specific check
    python3 scripts/run_quality_checks.py --check HighLatencyCheck

    # Quick mode (skip expensive checks)
    python3 scripts/run_quality_checks.py --quick

    # Monitor mode (continuous checking)
    python3 scripts/run_quality_checks.py --monitor --interval 3600
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from quality_checks import QualityCheckRunner, AlertManager


def load_config():
    """Load configuration from analytics_config.json."""
    config_path = Path(__file__).parent.parent / "config" / "analytics_config.json"

    if not config_path.exists():
        return {}

    try:
        import json
        with open(config_path, 'r') as f:
            full_config = json.load(f)
            return full_config.get("quality_checks", {})
    except Exception as e:
        print(f"Warning: Failed to load config: {e}", file=sys.stderr)
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Run quality checks on recall analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all checks
  %(prog)s --check HighLatencyCheck # Run specific check
  %(prog)s --quick                  # Fast mode, skip expensive checks
  %(prog)s --monitor --interval 3600  # Continuous monitoring
        """,
    )

    parser.add_argument(
        "--check",
        type=str,
        metavar="NAME",
        help="Run specific check (e.g., HighLatencyCheck). Run multiple: --check Check1 --check Check2",
        action="append",
        dest="checks",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Fast mode - skip expensive checks (FalsePositiveCheck, EmbeddingDriftCheck)",
    )

    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Continuous monitoring mode - run checks repeatedly",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="Check interval in monitor mode (default: 3600 seconds / 1 hour)",
    )

    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        metavar="HOURS",
        help="Number of hours to look back for data (default: 24)",
    )

    parser.add_argument(
        "--sessions-dir",
        type=str,
        metavar="PATH",
        help="Path to sessions directory (default: ~/.claude/context/sessions)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output with full details",
    )

    parser.add_argument(
        "--no-alerts",
        action="store_true",
        help="Disable alert output (still logs to file)",
    )

    parser.add_argument(
        "--email",
        type=str,
        metavar="ADDRESS",
        help="Email address to send alerts to (requires SMTP config)",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Initialize runner
    sessions_dir = Path(args.sessions_dir) if args.sessions_dir else None
    runner = QualityCheckRunner(sessions_dir=sessions_dir, config=config)

    # Initialize alert manager
    alert_manager = AlertManager(config=config.get("alerts", {}))

    def run_checks_once():
        """Run checks once and handle results."""
        try:
            # Run checks
            results = runner.run_checks(
                check_names=args.checks,
                quick=args.quick,
                hours=args.hours,
            )

            # Print results
            output = runner.format_results(results, verbose=args.verbose)
            print(output)

            # Send alerts if not disabled
            if not args.no_alerts:
                failed = runner.get_failed_checks(results)
                if failed:
                    alert_manager.send_alerts(
                        failed,
                        interactive=True,
                        email=args.email,
                    )
                else:
                    print("\n✅ All checks passed - no alerts")

            # Return exit code based on results
            summary = runner.get_summary(results)
            if summary["errors"] > 0:
                return 2  # Errors
            elif summary["warnings"] > 0:
                return 1  # Warnings
            else:
                return 0  # All passed

        except Exception as e:
            print(f"Error: Failed to run quality checks: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 3

    # Run checks
    if args.monitor:
        # Monitor mode - continuous checking
        print(f"Starting monitor mode (interval: {args.interval}s)", file=sys.stderr)
        print("Press Ctrl+C to stop", file=sys.stderr)
        print("", file=sys.stderr)

        try:
            while True:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n{'='*60}", file=sys.stderr)
                print(f"Quality Check Run - {timestamp}", file=sys.stderr)
                print(f"{'='*60}\n", file=sys.stderr)

                run_checks_once()

                print(f"\nNext check in {args.interval} seconds...", file=sys.stderr)
                time.sleep(args.interval)

        except KeyboardInterrupt:
            print("\n\nMonitor mode stopped", file=sys.stderr)
            return 0
    else:
        # Single run
        return run_checks_once()


if __name__ == "__main__":
    sys.exit(main())
