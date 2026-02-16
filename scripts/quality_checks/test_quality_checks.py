#!/usr/bin/env python3
"""
Tests for quality checks system.

Run with: python3 -m pytest scripts/quality_checks/test_quality_checks.py -v
Or: python3 scripts/quality_checks/test_quality_checks.py
"""

import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

import sys
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from quality_checks.checks import (
    LowRelevanceCheck,
    NoResultsCheck,
    HighLatencyCheck,
    IndexHealthCheck,
    EmbeddingDriftCheck,
    FalsePositiveCheck,
    UsageAnomalyCheck,
)
from quality_checks.runner import QualityCheckRunner
from quality_checks.alerts import AlertManager


class TestLowRelevanceCheck(unittest.TestCase):
    """Test low relevance quality check."""

    def test_low_relevance_detected(self):
        """Test detection of low quality scores."""
        quality_events = [
            {"event_id": "e1", "scores": {"overall": 0.3}},
            {"event_id": "e2", "scores": {"overall": 0.2}},
            {"event_id": "e3", "scores": {"overall": 0.8}},
        ]

        check = LowRelevanceCheck({"low_score_threshold": 0.4, "warning_percent": 0.3})
        result = check.run([], quality_events, [])

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.details["low_score_count"], 2)

    def test_acceptable_quality(self):
        """Test with acceptable quality scores."""
        quality_events = [
            {"event_id": "e1", "scores": {"overall": 0.8}},
            {"event_id": "e2", "scores": {"overall": 0.9}},
        ]

        check = LowRelevanceCheck()
        result = check.run([], quality_events, [])

        self.assertEqual(result.status, "pass")

    def test_no_data(self):
        """Test with no quality data."""
        check = LowRelevanceCheck()
        result = check.run([], [], [])

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.details["total_evaluations"], 0)


class TestNoResultsCheck(unittest.TestCase):
    """Test no results quality check."""

    def test_high_no_results_rate(self):
        """Test detection of high no-results rate."""
        telemetry_events = [
            {
                "event_type": "search_completed",
                "results": {"session_ids": []},
            },
            {
                "event_type": "search_completed",
                "results": {"session_ids": []},
            },
            {
                "event_type": "search_completed",
                "results": {"session_ids": ["s1"]},
            },
        ]

        check = NoResultsCheck({"no_results_threshold_percent": 0.5})
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.details["no_results_count"], 2)

    def test_acceptable_results_rate(self):
        """Test with acceptable results rate."""
        telemetry_events = [
            {
                "event_type": "search_completed",
                "results": {"session_ids": ["s1", "s2"]},
            },
            {
                "event_type": "search_completed",
                "results": {"session_ids": ["s3"]},
            },
        ]

        check = NoResultsCheck()
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "pass")


class TestHighLatencyCheck(unittest.TestCase):
    """Test high latency quality check."""

    def test_high_latency_detected(self):
        """Test detection of high latency."""
        telemetry_events = [
            {
                "event_type": "search_completed",
                "performance": {"total_latency_ms": 1500},
            },
            {
                "event_type": "search_completed",
                "performance": {"total_latency_ms": 1200},
            },
            {
                "event_type": "search_completed",
                "performance": {"total_latency_ms": 200},
            },
        ]

        check = HighLatencyCheck({"high_latency_ms": 1000, "warning_percent": 0.5})
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.details["high_latency_count"], 2)

    def test_acceptable_latency(self):
        """Test with acceptable latency."""
        telemetry_events = [
            {
                "event_type": "search_completed",
                "performance": {"total_latency_ms": 200},
            },
            {
                "event_type": "search_completed",
                "performance": {"total_latency_ms": 300},
            },
        ]

        check = HighLatencyCheck()
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "pass")
        self.assertLess(result.details["avg_latency_ms"], 500)


class TestIndexHealthCheck(unittest.TestCase):
    """Test index health check."""

    def setUp(self):
        """Set up test index."""
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = Path(self.temp_dir) / "index.json"

    def test_healthy_index(self):
        """Test with healthy index."""
        index_data = {
            "sessions": [
                {"id": "s1", "embeddings": [0.1, 0.2, 0.3]},
                {"id": "s2", "embeddings": [0.4, 0.5, 0.6]},
            ]
        }

        with open(self.index_path, 'w') as f:
            json.dump(index_data, f)

        check = IndexHealthCheck({"index_path": str(self.index_path)})
        result = check.run([], [], [])

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.details["total_sessions"], 2)

    def test_missing_embeddings(self):
        """Test with sessions missing embeddings."""
        index_data = {
            "sessions": [
                {"id": "s1", "embeddings": [0.1, 0.2]},
                {"id": "s2", "embeddings": []},
                {"id": "s3"},
            ]
        }

        with open(self.index_path, 'w') as f:
            json.dump(index_data, f)

        check = IndexHealthCheck({"index_path": str(self.index_path)})
        result = check.run([], [], [])

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.details["missing_embeddings"], 2)

    def test_missing_index(self):
        """Test with missing index file."""
        check = IndexHealthCheck({"index_path": "/nonexistent/index.json"})
        result = check.run([], [], [])

        self.assertEqual(result.status, "error")


class TestEmbeddingDriftCheck(unittest.TestCase):
    """Test embedding drift check."""

    def test_consistent_dimensions(self):
        """Test with consistent embedding dimensions."""
        telemetry_events = [
            {
                "event_type": "search_completed",
                "results": {"embedding_dim": 384},
            },
            {
                "event_type": "search_completed",
                "results": {"embedding_dim": 384},
            },
        ]

        check = EmbeddingDriftCheck()
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "pass")

    def test_dimension_drift(self):
        """Test detection of dimension changes."""
        telemetry_events = [
            {
                "event_type": "search_completed",
                "results": {"embedding_dim": 384},
            },
            {
                "event_type": "search_completed",
                "results": {"embedding_dim": 768},
            },
        ]

        check = EmbeddingDriftCheck()
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "warning")
        self.assertIn(384, result.details["embedding_dimensions"])
        self.assertIn(768, result.details["embedding_dimensions"])


class TestFalsePositiveCheck(unittest.TestCase):
    """Test false positive check."""

    def test_false_positives_detected(self):
        """Test detection of false positives."""
        quality_events = [
            {"event_id": "e1", "scores": {"overall": 0.8}},
            {"event_id": "e2", "scores": {"overall": 0.9}},
            {"event_id": "e3", "scores": {"overall": 0.75}},
            {"event_id": "e4", "scores": {"overall": 0.85}},
        ]

        impact_events = [
            {"event_id": "e1", "continuity_score": 0.2},
            {"event_id": "e2", "continuity_score": 0.1},
            {"event_id": "e3", "continuity_score": 0.8},
            {"event_id": "e4", "continuity_score": 0.25},
        ]

        check = FalsePositiveCheck()
        result = check.run([], quality_events, impact_events)

        # e1, e2, e4 have high quality but low continuity
        self.assertEqual(result.details["false_positive_count"], 3)

    def test_no_false_positives(self):
        """Test with no false positives."""
        quality_events = [
            {"event_id": "e1", "scores": {"overall": 0.8}},
        ]

        impact_events = [
            {"event_id": "e1", "continuity_score": 0.85},
        ]

        check = FalsePositiveCheck()
        result = check.run([], quality_events, impact_events)

        self.assertEqual(result.status, "pass")


class TestUsageAnomalyCheck(unittest.TestCase):
    """Test usage anomaly check."""

    def test_spike_detected(self):
        """Test detection of usage spike."""
        base_time = datetime.now(timezone.utc)

        # Create normal usage (1-2 per hour) plus spike (10 in one hour)
        telemetry_events = []

        # Normal hours
        for i in range(10):
            telemetry_events.append({
                "event_type": "search_completed",
                "timestamp": (base_time - timedelta(hours=i)).isoformat(),
            })

        # Spike hour
        for i in range(10):
            telemetry_events.append({
                "event_type": "search_completed",
                "timestamp": base_time.isoformat(),
            })

        check = UsageAnomalyCheck({"spike_threshold": 3.0})
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "warning")
        self.assertGreater(result.details["spike_ratio"], 3.0)

    def test_normal_usage(self):
        """Test with normal usage patterns."""
        base_time = datetime.now(timezone.utc)

        telemetry_events = [
            {
                "event_type": "search_completed",
                "timestamp": (base_time - timedelta(hours=i)).isoformat(),
            }
            for i in range(10)
        ]

        check = UsageAnomalyCheck()
        result = check.run(telemetry_events, [], [])

        self.assertEqual(result.status, "pass")


class TestQualityCheckRunner(unittest.TestCase):
    """Test quality check runner."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir)

        # Create sample telemetry log
        telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        with open(telemetry_log, 'w') as f:
            event = {
                "event_id": "test1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "search_completed",
                "results": {"session_ids": ["s1"]},
                "performance": {"total_latency_ms": 200},
            }
            f.write(json.dumps(event) + "\n")

        self.runner = QualityCheckRunner(sessions_dir=self.sessions_dir)

    def test_runner_initialization(self):
        """Test runner initializes correctly."""
        self.assertEqual(self.runner.sessions_dir, self.sessions_dir)
        self.assertTrue(self.runner.telemetry_log.parent.exists())

    def test_load_events(self):
        """Test loading events from log."""
        events = self.runner.load_events(self.runner.telemetry_log, hours=24)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], "test1")

    def test_run_all_checks(self):
        """Test running all checks."""
        results = self.runner.run_checks(quick=False, hours=24)

        # Should run all 7 checks
        self.assertEqual(len(results), 7)

        # All should have required fields
        for result in results:
            self.assertIsNotNone(result.check_name)
            self.assertIn(result.status, ["pass", "warning", "error"])

    def test_run_specific_check(self):
        """Test running specific check."""
        results = self.runner.run_checks(
            check_names=["NoResultsCheck"],
            hours=24,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].check_name, "NoResultsCheck")

    def test_quick_mode(self):
        """Test quick mode skips expensive checks."""
        results = self.runner.run_checks(quick=True, hours=24)

        # Should skip FalsePositiveCheck and EmbeddingDriftCheck
        check_names = [r.check_name for r in results]
        self.assertNotIn("FalsePositiveCheck", check_names)
        self.assertNotIn("EmbeddingDriftCheck", check_names)

    def test_get_summary(self):
        """Test result summary."""
        results = self.runner.run_checks(hours=24)
        summary = self.runner.get_summary(results)

        self.assertIn("total_checks", summary)
        self.assertIn("passed", summary)
        self.assertIn("warnings", summary)
        self.assertIn("errors", summary)
        self.assertIn("pass_rate", summary)

    def test_format_results(self):
        """Test result formatting."""
        results = self.runner.run_checks(hours=24)
        formatted = self.runner.format_results(results, verbose=False)

        self.assertIsInstance(formatted, str)
        self.assertIn("Quality Check Results", formatted)


class TestAlertManager(unittest.TestCase):
    """Test alert manager."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.alert_log = Path(self.temp_dir) / "alerts.jsonl"
        self.manager = AlertManager({
            "alert_log_path": str(self.alert_log),
        })

    def test_alert_manager_initialization(self):
        """Test alert manager initializes correctly."""
        self.assertEqual(self.manager.alert_log, self.alert_log)

    def test_log_alerts(self):
        """Test alert logging."""
        from quality_checks.checks import CheckResult

        results = [
            CheckResult(
                check_name="TestCheck",
                status="warning",
                message="Test warning",
                details={},
                timestamp=datetime.now(timezone.utc).isoformat(),
                severity="warning",
            ),
        ]

        self.manager._log_alerts(results)

        # Check log file created
        self.assertTrue(self.alert_log.exists())

        # Check content
        with open(self.alert_log, 'r') as f:
            logged = json.loads(f.read().strip())
            self.assertEqual(logged["check_name"], "TestCheck")

    def test_deduplication(self):
        """Test alert deduplication."""
        from quality_checks.checks import CheckResult

        # Create identical alerts
        result1 = CheckResult(
            check_name="TestCheck",
            status="warning",
            message="Test",
            details={},
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="warning",
        )

        result2 = CheckResult(
            check_name="TestCheck",
            status="warning",
            message="Test",
            details={},
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="warning",
        )

        # Deduplicate
        deduplicated = self.manager._deduplicate_alerts([result1, result2])

        # Should only keep first one
        self.assertEqual(len(deduplicated), 1)


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
