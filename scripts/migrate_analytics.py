#!/usr/bin/env python3
"""
Migration and upgrade utility for Claude Recall Analytics.

Handles:
- Upgrading from previous versions
- Detecting existing logs
- Ensuring backward compatibility
- Safe rollback

Usage:
    python3 scripts/migrate_analytics.py [--check|--migrate|--rollback]
"""

import json
import sys
import os
import argparse
import shutil
from pathlib import Path
from datetime import datetime, timezone


class AnalyticsMigrator:
    """Handles analytics migrations and upgrades."""

    def __init__(self):
        """Initialize migrator."""
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.sessions_dir = Path.home() / ".claude" / "context" / "sessions"

        self.analytics_config = self.config_dir / "analytics_config.json"
        self.analytics_config_backup = self.config_dir / "analytics_config.json.backup"

    def check_status(self):
        """Check current analytics setup status."""
        print("=" * 60)
        print("Analytics Migration Status Check")
        print("=" * 60 + "\n")

        status = {
            "config_exists": False,
            "logs_exist": False,
            "version": None,
            "needs_migration": False,
        }

        # Check config
        if self.analytics_config.exists():
            print("✅ Analytics config exists")
            status["config_exists"] = True

            try:
                with open(self.analytics_config, 'r') as f:
                    config = json.load(f)
                    status["version"] = config.get("version", "1.0.0")
                    print(f"   Version: {status['version']}")
            except Exception as e:
                print(f"   ⚠️  Error reading config: {e}")
        else:
            print("ℹ️  No analytics config found (fresh install)")

        # Check logs
        log_files = [
            self.sessions_dir / "recall_analytics.jsonl",
            self.sessions_dir / "quality_scores.jsonl",
            self.sessions_dir / "context_impact.jsonl",
        ]

        existing_logs = [f for f in log_files if f.exists()]
        if existing_logs:
            print(f"\n✅ Found {len(existing_logs)} existing log files:")
            for log in existing_logs:
                size = log.stat().st_size if log.exists() else 0
                line_count = sum(1 for _ in open(log, 'r')) if log.exists() else 0
                print(f"   • {log.name}: {line_count} events, {size:,} bytes")
            status["logs_exist"] = True
        else:
            print("\nℹ️  No existing log files found")

        # Check index
        index_path = self.sessions_dir / "index.json"
        if index_path.exists():
            print(f"\n✅ Index file exists: {index_path}")
            try:
                with open(index_path, 'r') as f:
                    index_data = json.load(f)
                    session_count = len(index_data.get("sessions", []))
                    print(f"   Sessions indexed: {session_count}")
            except Exception as e:
                print(f"   ⚠️  Error reading index: {e}")
        else:
            print("\nℹ️  No index file found")

        # Determine if migration needed
        if status["config_exists"] and status["version"] != "1.0.0":
            status["needs_migration"] = True
            print("\n⚠️  Migration recommended")
        else:
            print("\n✅ No migration needed")

        return status

    def backup_config(self):
        """Backup current configuration."""
        if not self.analytics_config.exists():
            print("ℹ️  No config to backup")
            return True

        try:
            # Create timestamped backup
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = self.config_dir / f"analytics_config.json.backup.{timestamp}"

            shutil.copy2(self.analytics_config, backup_path)
            print(f"✅ Config backed up to: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Error backing up config: {e}")
            return False

    def migrate(self):
        """Perform migration."""
        print("=" * 60)
        print("Analytics Migration")
        print("=" * 60 + "\n")

        # Check status first
        status = self.check_status()

        if not status["needs_migration"]:
            print("\n✅ System is up to date - no migration needed")
            return True

        print("\n📦 Starting migration...")

        # Backup config
        if not self.backup_config():
            print("\n❌ Migration aborted - backup failed")
            return False

        # Perform version-specific migrations
        current_version = status["version"] or "0.0.0"

        if current_version < "1.0.0":
            print("\n🔄 Migrating to 1.0.0...")
            # Add any version-specific migration logic here
            pass

        # Update version in config
        try:
            if self.analytics_config.exists():
                with open(self.analytics_config, 'r') as f:
                    config = json.load(f)
            else:
                config = {}

            config["version"] = "1.0.0"
            config["migrated_at"] = datetime.now(timezone.utc).isoformat()

            with open(self.analytics_config, 'w') as f:
                json.dump(config, f, indent=2)

            print("\n✅ Migration complete!")
            return True

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            return False

    def rollback(self):
        """Rollback to previous configuration."""
        print("=" * 60)
        print("Analytics Rollback")
        print("=" * 60 + "\n")

        # Find most recent backup
        backups = sorted(self.config_dir.glob("analytics_config.json.backup.*"))

        if not backups:
            print("❌ No backups found")
            return False

        latest_backup = backups[-1]
        print(f"📦 Found backup: {latest_backup.name}")

        # Confirm rollback
        response = input("\n⚠️  Rollback will overwrite current config. Continue? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Rollback cancelled")
            return False

        try:
            # Backup current config
            if self.analytics_config.exists():
                temp_backup = self.config_dir / "analytics_config.json.pre_rollback"
                shutil.copy2(self.analytics_config, temp_backup)

            # Restore from backup
            shutil.copy2(latest_backup, self.analytics_config)

            print(f"\n✅ Rolled back to: {latest_backup.name}")
            print(f"   Current config saved as: analytics_config.json.pre_rollback")
            return True

        except Exception as e:
            print(f"\n❌ Rollback failed: {e}")
            return False

    def validate(self):
        """Validate analytics setup."""
        print("=" * 60)
        print("Analytics Validation")
        print("=" * 60 + "\n")

        all_valid = True

        # Check config
        if self.analytics_config.exists():
            try:
                with open(self.analytics_config, 'r') as f:
                    config = json.load(f)
                print("✅ Config file valid JSON")

                # Check required fields
                required_sections = ["telemetry", "impact_analysis", "quality_scoring", "quality_checks"]
                for section in required_sections:
                    if section in config:
                        print(f"   ✅ {section} section present")
                    else:
                        print(f"   ⚠️  {section} section missing")
                        all_valid = False

            except json.JSONDecodeError as e:
                print(f"❌ Config file invalid JSON: {e}")
                all_valid = False
        else:
            print("ℹ️  No config file found")

        # Check log directory
        if self.sessions_dir.exists():
            print(f"\n✅ Sessions directory exists: {self.sessions_dir}")
            if os.access(self.sessions_dir, os.W_OK):
                print("   ✅ Directory is writable")
            else:
                print("   ❌ Directory not writable")
                all_valid = False
        else:
            print(f"\n⚠️  Sessions directory doesn't exist: {self.sessions_dir}")
            print("   (Will be created automatically when needed)")

        # Check index
        index_path = self.sessions_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    json.load(f)
                print(f"\n✅ Index file valid: {index_path}")
            except json.JSONDecodeError as e:
                print(f"\n❌ Index file corrupted: {e}")
                print("   Run: python3 scripts/build_index.py")
                all_valid = False
        else:
            print(f"\n⚠️  No index file found: {index_path}")
            print("   Run: python3 scripts/build_index.py")

        # Summary
        print("\n" + "=" * 60)
        if all_valid:
            print("✅ Validation passed - system ready")
        else:
            print("⚠️  Validation found issues - review above")

        return all_valid


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migration and upgrade utility for Claude Recall Analytics"
    )

    parser.add_argument(
        "action",
        nargs="?",
        default="check",
        choices=["check", "migrate", "rollback", "validate"],
        help="Action to perform (default: check)",
    )

    args = parser.parse_args()

    migrator = AnalyticsMigrator()

    if args.action == "check":
        migrator.check_status()
        return 0

    elif args.action == "migrate":
        success = migrator.migrate()
        return 0 if success else 1

    elif args.action == "rollback":
        success = migrator.rollback()
        return 0 if success else 1

    elif args.action == "validate":
        success = migrator.validate()
        return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
