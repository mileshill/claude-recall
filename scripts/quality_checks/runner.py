"""
Quality check runner for recall analytics.

Orchestrates running multiple quality checks and aggregating results.
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from .checks import QualityCheck, CheckResult, ALL_CHECKS


class QualityCheckRunner:
    """Orchestrates running quality checks."""

    def __init__(
        self,
        sessions_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize quality check runner.

        Args:
            sessions_dir: Path to sessions directory
            config: Configuration dictionary with check settings
        """
        if sessions_dir is None:
            home = Path.home()
            sessions_dir = home / ".claude" / "context" / "sessions"

        self.sessions_dir = Path(sessions_dir)
        self.config = config or {}

        # Log paths
        self.telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        self.quality_log = self.sessions_dir / "quality_scores.jsonl"
        self.impact_log = self.sessions_dir / "context_impact.jsonl"
        self.check_log = self.sessions_dir / "quality_check_log.jsonl"

    def load_events(self, log_path: Path, hours: int = 24) -> List[Dict]:
        """
        Load events from JSONL log file.

        Args:
            log_path: Path to log file
            hours: Number of hours to look back

        Returns:
            List of event dictionaries
        """
        if not log_path.exists():
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        events = []

        try:
            with open(log_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        # Parse timestamp
                        timestamp_str = event.get('timestamp', '')
                        if timestamp_str:
                            try:
                                if timestamp_str.endswith('Z'):
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                                    timestamp = datetime.fromisoformat(timestamp_str)
                                else:
                                    timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)

                                if timestamp >= cutoff:
                                    events.append(event)
                            except ValueError:
                                # Include event if timestamp parsing fails
                                events.append(event)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Warning: Error loading {log_path}: {e}")

        return events

    def run_checks(
        self,
        check_names: Optional[List[str]] = None,
        quick: bool = False,
        hours: int = 24,
    ) -> List[CheckResult]:
        """
        Run quality checks.

        Args:
            check_names: List of check names to run (None = all)
            quick: If True, skip expensive checks
            hours: Number of hours to look back for data

        Returns:
            List of CheckResult objects
        """
        # Load data
        telemetry_events = self.load_events(self.telemetry_log, hours)
        quality_events = self.load_events(self.quality_log, hours)
        impact_events = self.load_events(self.impact_log, hours)

        # Determine which checks to run
        if check_names:
            # Run specific checks
            checks_to_run = [
                check_class for check_class in ALL_CHECKS
                if check_class.__name__ in check_names
            ]
        else:
            # Run all checks
            checks_to_run = ALL_CHECKS

        # Skip expensive checks in quick mode
        if quick:
            expensive_checks = ["FalsePositiveCheck", "EmbeddingDriftCheck"]
            checks_to_run = [
                c for c in checks_to_run
                if c.__name__ not in expensive_checks
            ]

        # Run checks
        results = []
        for check_class in checks_to_run:
            try:
                # Get check-specific config
                check_config = self.config.get(check_class.__name__, {}).copy()

                # Inject sessions_dir-specific paths for checks that need them
                if check_class.__name__ == "IndexHealthCheck":
                    # Set index_path based on sessions_dir
                    check_config["index_path"] = str(self.sessions_dir / "index.json")

                # Instantiate and run check
                check = check_class(config=check_config)
                result = check.run(telemetry_events, quality_events, impact_events)
                results.append(result)
            except Exception as e:
                # Log error but continue with other checks
                error_result = CheckResult(
                    check_name=check_class.__name__,
                    status="error",
                    message=f"Check failed with exception: {e}",
                    details={"error": str(e)},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    severity="error",
                )
                results.append(error_result)

        # Log results
        self._log_results(results)

        return results

    def _log_results(self, results: List[CheckResult]):
        """Log check results to file."""
        try:
            with open(self.check_log, 'a') as f:
                for result in results:
                    log_entry = {
                        "timestamp": result.timestamp,
                        "check_name": result.check_name,
                        "status": result.status,
                        "severity": result.severity,
                        "message": result.message,
                        "details": result.details,
                    }
                    f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Warning: Failed to log results: {e}")

    def get_summary(self, results: List[CheckResult]) -> Dict[str, Any]:
        """
        Get summary of check results.

        Args:
            results: List of CheckResult objects

        Returns:
            Summary dictionary
        """
        total = len(results)
        passed = len([r for r in results if r.status == "pass"])
        warnings = len([r for r in results if r.status == "warning"])
        errors = len([r for r in results if r.status == "error"])

        return {
            "total_checks": total,
            "passed": passed,
            "warnings": warnings,
            "errors": errors,
            "pass_rate": passed / total if total > 0 else 0,
        }

    def get_failed_checks(self, results: List[CheckResult]) -> List[CheckResult]:
        """
        Get list of failed checks (warnings + errors).

        Args:
            results: List of CheckResult objects

        Returns:
            List of failed CheckResult objects
        """
        return [r for r in results if r.status in ("warning", "error")]

    def format_results(self, results: List[CheckResult], verbose: bool = False) -> str:
        """
        Format results as human-readable string.

        Args:
            results: List of CheckResult objects
            verbose: If True, include full details

        Returns:
            Formatted string
        """
        lines = []
        summary = self.get_summary(results)

        # Summary header
        lines.append("=" * 60)
        lines.append("Quality Check Results")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Total checks: {summary['total_checks']}")
        lines.append(f"Passed: {summary['passed']}")
        lines.append(f"Warnings: {summary['warnings']}")
        lines.append(f"Errors: {summary['errors']}")
        lines.append(f"Pass rate: {summary['pass_rate']:.1%}")
        lines.append("")

        # Individual results
        for result in results:
            # Icon based on status
            if result.status == "pass":
                icon = "✓"
            elif result.status == "warning":
                icon = "⚠"
            else:
                icon = "✗"

            lines.append(f"{icon} {result.check_name}: {result.message}")

            if verbose and result.details:
                for key, value in result.details.items():
                    lines.append(f"    {key}: {value}")
                lines.append("")

        return "\n".join(lines)
