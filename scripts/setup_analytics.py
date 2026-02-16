#!/usr/bin/env python3
"""
Interactive configuration wizard for Claude Recall Analytics.

Guides users through enabling and configuring analytics features.

Usage:
    python3 scripts/setup_analytics.py
"""

import json
import sys
import os
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")


def print_section(text):
    """Print formatted section."""
    print("\n" + "-" * 60)
    print(text)
    print("-" * 60 + "\n")


def get_yes_no(prompt, default=True):
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")


def get_number(prompt, default, min_val=None, max_val=None):
    """Get numeric input from user."""
    while True:
        response = input(f"{prompt} [{default}]: ").strip()
        if not response:
            return default
        try:
            value = float(response)
            if min_val is not None and value < min_val:
                print(f"Value must be >= {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"Value must be <= {max_val}")
                continue
            return value
        except ValueError:
            print("Please enter a valid number")


def get_string(prompt, default=""):
    """Get string input from user."""
    response = input(f"{prompt} [{default}]: ").strip()
    return response if response else default


def main():
    """Run interactive configuration wizard."""
    print_header("📊 Claude Recall Analytics Configuration Wizard")

    print("""
Welcome! This wizard will help you configure analytics for Claude Recall.

Analytics features:
  • Telemetry - Automatic tracking of all recall operations
  • Impact Analysis - Measure conversation continuity and efficiency
  • Quality Scoring - LLM-based evaluation (optional, ~$0.50/month)
  • Quality Checks - 7 automated health monitors
  • Reporting - Generate comprehensive analytics reports

Let's get started!
    """)

    config = {}

    # Telemetry Configuration
    print_section("1️⃣  Telemetry Configuration")
    print("Telemetry tracks all recall operations (queries, results, performance)")
    print("Cost: Free | Overhead: <1ms per search")

    telemetry_enabled = get_yes_no("Enable telemetry?", default=True)

    config["telemetry"] = {
        "enabled": telemetry_enabled,
        "log_path": ".claude/context/sessions/recall_analytics.jsonl",
        "sampling_rate": 1.0,
        "batch_size": 10,
        "pii_redaction": True,
    }

    if telemetry_enabled:
        print("✅ Telemetry enabled - all searches will be tracked")
    else:
        print("⏭️  Telemetry disabled - skipping dependent features")

    # Impact Analysis Configuration
    print_section("2️⃣  Impact Analysis Configuration")
    print("Impact analysis measures how recalled context affects conversations")
    print("Cost: Free | Runs: After each session")

    if telemetry_enabled:
        impact_enabled = get_yes_no("Enable impact analysis?", default=True)
    else:
        print("⏭️  Requires telemetry - skipping")
        impact_enabled = False

    config["impact_analysis"] = {
        "enabled": impact_enabled,
        "log_path": ".claude/context/sessions/context_impact.jsonl",
        "auto_analyze_on_session_end": True,
        "min_recall_events": 1,
    }

    if impact_enabled:
        print("✅ Impact analysis enabled")

    # Quality Scoring Configuration
    print_section("3️⃣  Quality Scoring Configuration")
    print("LLM-based evaluation of search result quality")
    print("Cost: ~$0.50/month (10% sampling) | Requires: ANTHROPIC_API_KEY")

    if telemetry_enabled:
        quality_enabled = get_yes_no("Enable quality scoring?", default=False)
    else:
        print("⏭️  Requires telemetry - skipping")
        quality_enabled = False

    config["quality_scoring"] = {
        "enabled": quality_enabled,
        "log_path": ".claude/context/sessions/quality_scores.jsonl",
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "model": "claude-haiku-4.5-20251001",
        "sampling_rate": 0.1,
        "monthly_budget_usd": 5.0,
        "fallback_to_heuristic": True,
    }

    if quality_enabled:
        print("\nQuality scoring configuration:")

        # Check API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")
        else:
            print("⚠️  API key not found - set ANTHROPIC_API_KEY environment variable")
            print("   export ANTHROPIC_API_KEY='your-api-key'")

        # Sampling rate
        print("\nSampling rate controls cost (0.1 = 10% of searches evaluated)")
        sampling_rate = get_number("Sampling rate", default=0.1, min_val=0.0, max_val=1.0)
        config["quality_scoring"]["sampling_rate"] = sampling_rate

        # Monthly budget
        print("\nMonthly budget limits spending (evaluation stops if exceeded)")
        budget = get_number("Monthly budget (USD)", default=5.0, min_val=0.0)
        config["quality_scoring"]["monthly_budget_usd"] = budget

        estimated_cost = budget * sampling_rate * 0.5  # Rough estimate
        print(f"✅ Estimated monthly cost: ~${estimated_cost:.2f}")

    # Quality Checks Configuration
    print_section("4️⃣  Quality Checks Configuration")
    print("Automated health monitoring with 7 checks")
    print("Cost: Free | Overhead: <1s per check run")

    checks_enabled = get_yes_no("Enable quality checks?", default=True)

    config["quality_checks"] = {
        "enabled": checks_enabled,
        "schedule": "0 8 * * *",
        "LowRelevanceCheck": {
            "low_score_threshold": 0.4,
            "warning_percent": 0.2,
        },
        "NoResultsCheck": {
            "no_results_threshold_percent": 0.3,
        },
        "HighLatencyCheck": {
            "high_latency_ms": 1000,
            "warning_percent": 0.1,
        },
        "UsageAnomalyCheck": {
            "spike_threshold": 3.0,
        },
        "alerts": {
            "email_enabled": False,
            "slack_webhook_url": "",
        },
    }

    if checks_enabled:
        print("✅ Quality checks enabled")

        # Alert configuration
        print("\nConfigure alerts (optional):")

        # Email alerts
        email_alerts = get_yes_no("Enable email alerts?", default=False)
        if email_alerts:
            config["quality_checks"]["alerts"]["email_enabled"] = True
            print("\n⚠️  Configure SMTP settings in config/analytics_config.json")
            print("   See docs/QUALITY_CHECKS_SCHEDULING.md for details")

        # Slack alerts
        slack_alerts = get_yes_no("Enable Slack alerts?", default=False)
        if slack_alerts:
            webhook_url = get_string("Slack webhook URL", default="")
            config["quality_checks"]["alerts"]["slack_webhook_url"] = webhook_url
            if webhook_url:
                print("✅ Slack webhook configured")
            else:
                print("⚠️  Set webhook URL in config/analytics_config.json")

    # Reporting Configuration
    print_section("5️⃣  Reporting Configuration")
    print("Generate analytics reports (Markdown, JSON, HTML)")
    print("Cost: Free")

    reporting_enabled = get_yes_no("Enable reporting?", default=True)

    config["reporting"] = {
        "enabled": reporting_enabled,
        "period_days": 30,
        "format": "markdown",
    }

    if reporting_enabled:
        print("✅ Reporting enabled")

    # Save Configuration
    print_section("💾 Saving Configuration")

    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "analytics_config.json"

    # Check if config exists
    if config_path.exists():
        print(f"⚠️  Configuration file already exists: {config_path}")
        overwrite = get_yes_no("Overwrite existing configuration?", default=False)
        if not overwrite:
            print("❌ Configuration not saved - exiting")
            return 1

    # Write config
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✅ Configuration saved to: {config_path}")
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return 1

    # Validate Configuration
    print_section("✅ Validation")

    # Check log directory
    sessions_dir = Path.home() / ".claude" / "context" / "sessions"
    if not sessions_dir.exists():
        print(f"⚠️  Sessions directory doesn't exist: {sessions_dir}")
        print("   It will be created automatically when needed")
    else:
        print(f"✅ Sessions directory exists: {sessions_dir}")

    # Test Configuration
    print_section("🧪 Testing Configuration")

    test_it = get_yes_no("Run configuration test?", default=True)

    if test_it:
        print("\nTesting analytics components...")

        # Test telemetry import
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from telemetry import TelemetryCollector
            print("✅ Telemetry module loaded")
        except Exception as e:
            print(f"❌ Error loading telemetry: {e}")

        # Test reporting import
        try:
            from reporting import ReportGenerator
            print("✅ Reporting module loaded")
        except Exception as e:
            print(f"❌ Error loading reporting: {e}")

        # Test quality checks import
        try:
            from quality_checks import QualityCheckRunner
            print("✅ Quality checks module loaded")
        except Exception as e:
            print(f"❌ Error loading quality checks: {e}")

    # Next Steps
    print_section("🎉 Setup Complete!")

    print("""
Analytics is now configured! Here's what to do next:

1. **Start using recall normally** - Analytics run automatically

2. **Generate your first report:**
   python3 scripts/generate_recall_report.py --summary

3. **Run quality checks:**
   python3 scripts/run_quality_checks.py --quick

4. **Schedule automated checks:**
   See docs/QUALITY_CHECKS_SCHEDULING.md for cron/hook setup

5. **Read the docs:**
   - docs/ANALYTICS_GUIDE.md - Complete guide
   - docs/TELEMETRY_SCHEMA.md - Event reference
   - docs/QUALITY_CHECKS_GUIDE.md - Health monitoring

Questions? Check the documentation or open an issue.

Happy analyzing! 📊
    """)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
