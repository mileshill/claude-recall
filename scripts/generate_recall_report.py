#!/usr/bin/env python3
"""
CLI tool for generating recall analytics reports.

Usage:
    python3 scripts/generate_recall_report.py [options]

Examples:
    # Generate 30-day report
    python3 scripts/generate_recall_report.py --period 30 --output report.md

    # Quick summary
    python3 scripts/generate_recall_report.py --summary

    # JSON export
    python3 scripts/generate_recall_report.py --format json --output metrics.json

    # Email-friendly format
    python3 scripts/generate_recall_report.py --format email --output email_report.md

    # Specific sections only
    python3 scripts/generate_recall_report.py --sections usage,quality,performance
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from reporting import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate recall analytics reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --period 30 --output report.md
  %(prog)s --summary
  %(prog)s --format json --output metrics.json
  %(prog)s --format email --output email_report.md
  %(prog)s --sections usage,quality,performance
        """,
    )

    parser.add_argument(
        "--period",
        type=int,
        default=30,
        metavar="DAYS",
        help="Number of days to include in report (default: 30)",
    )

    parser.add_argument(
        "--format",
        choices=["markdown", "json", "html", "email"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    parser.add_argument(
        "--output",
        type=str,
        metavar="PATH",
        help="Output file path (default: print to stdout)",
    )

    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate brief summary instead of full report (overrides --period to 7 days)",
    )

    parser.add_argument(
        "--sections",
        type=str,
        metavar="SECTIONS",
        help="Comma-separated list of sections to include (e.g., usage,quality,impact)",
    )

    parser.add_argument(
        "--sessions-dir",
        type=str,
        metavar="PATH",
        help="Path to sessions directory (default: ~/.claude/context/sessions)",
    )

    parser.add_argument(
        "--no-template",
        action="store_true",
        help="Disable Jinja2 templates, use built-in formatters",
    )

    args = parser.parse_args()

    # Initialize generator
    sessions_dir = Path(args.sessions_dir) if args.sessions_dir else None
    try:
        generator = ReportGenerator(sessions_dir=sessions_dir)
    except Exception as e:
        print(f"Error: Failed to initialize report generator: {e}", file=sys.stderr)
        return 1

    # Generate report
    try:
        if args.summary:
            # Generate summary
            report = generator.generate_summary(
                period_days=7,
                use_template=not args.no_template,
            )
        else:
            # Generate full report
            sections = None
            if args.sections:
                sections = [s.strip() for s in args.sections.split(",")]

            report = generator.generate_report(
                period_days=args.period,
                format=args.format,
                output_path=Path(args.output) if args.output else None,
                sections=sections,
                use_template=not args.no_template,
            )

        # Output report (unless already written to file)
        if not args.output:
            print(report)

        # Success message if written to file
        if args.output:
            print(f"Report written to: {args.output}", file=sys.stderr)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Make sure analytics logs exist in the sessions directory.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Failed to generate report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
