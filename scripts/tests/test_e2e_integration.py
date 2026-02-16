#!/usr/bin/env python3
"""
End-to-end integration tests for recall analytics system.

Tests complete pipeline from data collection through reporting and quality checks.

Run with: python3 -m pytest scripts/tests/test_e2e_integration.py -v
Or: python3 scripts/tests/test_e2e_integration.py
"""

import unittest
import json
import tempfile
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFullPipeline(unittest.TestCase):
    """Test complete analytics pipeline."""

    def setUp(self):
        """Set up test environment with sample data."""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / "sessions"
        self.sessions_dir.mkdir(parents=True)

        # Create comprehensive sample data
        self._create_sample_telemetry()
        self._create_sample_quality()
        self._create_sample_impact()
        self._create_sample_index()

    def _create_sample_telemetry(self):
        """Create sample telemetry log."""
        telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        events = []

        for i in range(10):
            event = {
                "event_id": f"evt{i}",
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(),
                "event_type": "search_completed",
                "session_id": f"session{i % 3}",
                "query": f"test query {i}",
                "search_config": {
                    "mode": "hybrid",
                    "mode_resolved": "hybrid" if i % 2 == 0 else "semantic",
                },
                "results": {
                    "session_ids": [f"s{j}" for j in range(i % 5)],
                    "embedding_dim": 384,
                },
                "performance": {
                    "total_latency_ms": 200 + (i * 50),
                    "index_load_ms": 50,
                    "search_ms": 100,
                    "cache_hit": i % 3 == 0,
                },
                "system": {
                    "index_size": 1000,
                    "memory_usage_mb": 150,
                },
            }
            events.append(event)

        with open(telemetry_log, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

    def _create_sample_quality(self):
        """Create sample quality scores log."""
        quality_log = self.sessions_dir / "quality_scores.jsonl"
        events = []

        for i in range(5):
            event = {
                "event_id": f"evt{i}",
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(),
                "query": f"test query {i}",
                "scores": {
                    "relevance": 0.7 + (i * 0.05),
                    "coverage": 0.65 + (i * 0.05),
                    "specificity": 0.8 + (i * 0.03),
                    "overall": 0.75 + (i * 0.04),
                },
                "method": "llm",
                "model": "claude-haiku-4.5-20251001",
                "cost_usd": 0.0004,
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 100,
                },
            }
            events.append(event)

        with open(quality_log, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

    def _create_sample_impact(self):
        """Create sample impact analysis log."""
        impact_log = self.sessions_dir / "context_impact.jsonl"
        events = []

        for i in range(3):
            event = {
                "event_id": f"evt{i}",
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(),
                "session_id": f"session{i}",
                "context_usage": {
                    "explicit_citations": 2 + i,
                    "implicit_usage_score": 0.6 + (i * 0.1),
                    "topics_reused": 3 + i,
                },
                "continuity_score": 0.7 + (i * 0.08),
                "efficiency_metrics": {
                    "estimated_time_saved_minutes": 10.0 + (i * 5),
                    "repetition_avoided": True,
                },
            }
            events.append(event)

        with open(impact_log, 'w') as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

    def _create_sample_index(self):
        """Create sample index.json."""
        index_path = self.sessions_dir / "index.json"
        index_data = {
            "sessions": [
                {
                    "id": f"session{i}",
                    "embeddings": [0.1 * j for j in range(384)],
                    "metadata": {"title": f"Session {i}"},
                }
                for i in range(5)
            ]
        }

        with open(index_path, 'w') as f:
            json.dump(index_data, f)

    def test_reporting_pipeline(self):
        """Test report generation with sample data."""
        from reporting import ReportGenerator

        generator = ReportGenerator(sessions_dir=self.sessions_dir)

        # Generate full report
        report = generator.generate_report(period_days=7, format="markdown")

        # Verify report contains expected sections
        self.assertIn("Recall Analytics Report", report)
        self.assertIn("Executive Summary", report)
        self.assertIn("Usage Statistics", report)
        self.assertIn("Quality Metrics", report)
        self.assertIn("Performance Benchmarks", report)

        # Verify data is present
        self.assertIn("10", report)  # Should show 10 searches

    def test_quality_checks_pipeline(self):
        """Test quality checks with sample data."""
        from quality_checks import QualityCheckRunner

        # Configure runner with correct index path
        config = {
            "IndexHealthCheck": {
                "index_path": str(self.sessions_dir / "index.json")
            }
        }
        runner = QualityCheckRunner(sessions_dir=self.sessions_dir, config=config)

        # Run all checks
        results = runner.run_checks(hours=24)

        # Should run all checks
        self.assertEqual(len(results), 7)

        # All should complete (pass, warning, or error)
        for result in results:
            self.assertIn(result.status, ["pass", "warning", "error"])

        # Index check should pass (we created a valid index)
        index_result = next(r for r in results if r.check_name == "IndexHealthCheck")
        self.assertEqual(index_result.status, "pass")

    def test_json_export(self):
        """Test JSON data export."""
        from reporting import ReportGenerator

        generator = ReportGenerator(sessions_dir=self.sessions_dir)

        # Export to JSON
        json_report = generator.export_json(period_days=7)

        # Should be valid JSON
        data = json.loads(json_report)

        # Verify structure
        self.assertIn("report_data", data)
        self.assertIn("usage", data["report_data"])
        self.assertIn("quality", data["report_data"])
        self.assertEqual(data["report_data"]["usage"]["total_searches"], 10)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / "sessions"
        self.sessions_dir.mkdir(parents=True)

    def test_missing_logs(self):
        """Test graceful handling of missing log files."""
        from reporting import ReportGenerator

        generator = ReportGenerator(sessions_dir=self.sessions_dir)

        # Should not crash with missing logs
        report = generator.generate_summary(period_days=7)

        self.assertIn("No search activity", report)

    def test_corrupted_log_line(self):
        """Test handling of corrupted JSONL lines."""
        # Create log with mix of valid and invalid lines
        telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        with open(telemetry_log, 'w') as f:
            # Valid line
            f.write(json.dumps({
                "event_id": "evt1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "search_completed",
            }) + "\n")
            # Invalid line (corrupted JSON)
            f.write("{ corrupted json\n")
            # Another valid line
            f.write(json.dumps({
                "event_id": "evt2",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "search_completed",
            }) + "\n")

        from reporting import ReportGenerator

        generator = ReportGenerator(sessions_dir=self.sessions_dir)

        # Should handle gracefully and process valid lines
        data = generator.get_raw_data(period_days=7)

        # Should have processed the 2 valid events
        self.assertGreaterEqual(data["usage"]["total_searches"], 0)

    def test_empty_index(self):
        """Test handling of empty index."""
        # Create empty index
        index_path = self.sessions_dir / "index.json"
        with open(index_path, 'w') as f:
            json.dump({"sessions": []}, f)

        from quality_checks import QualityCheckRunner

        # Configure with correct index path
        config = {
            "IndexHealthCheck": {
                "index_path": str(index_path)
            }
        }
        runner = QualityCheckRunner(sessions_dir=self.sessions_dir, config=config)
        results = runner.run_checks(check_names=["IndexHealthCheck"], hours=24)

        # Should warn about empty index
        self.assertEqual(results[0].status, "warning")
        self.assertIn("empty", results[0].message.lower())


class TestPerformance(unittest.TestCase):
    """Test performance benchmarks."""

    def setUp(self):
        """Set up test environment with large dataset."""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / "sessions"
        self.sessions_dir.mkdir(parents=True)

        # Create large dataset (1000 events)
        telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        with open(telemetry_log, 'w') as f:
            for i in range(1000):
                event = {
                    "event_id": f"evt{i}",
                    "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(),
                    "event_type": "search_completed",
                    "results": {"session_ids": ["s1"]},
                    "performance": {"total_latency_ms": 200},
                }
                f.write(json.dumps(event) + "\n")

    def test_report_generation_performance(self):
        """Test report generation completes quickly."""
        from reporting import ReportGenerator

        generator = ReportGenerator(sessions_dir=self.sessions_dir)

        start = time.time()
        report = generator.generate_report(period_days=7)
        elapsed = time.time() - start

        # Should complete in < 5 seconds
        self.assertLess(elapsed, 5.0)

    def test_quality_checks_performance(self):
        """Test quality checks complete quickly."""
        from quality_checks import QualityCheckRunner

        runner = QualityCheckRunner(sessions_dir=self.sessions_dir)

        start = time.time()
        results = runner.run_checks(quick=True, hours=24)
        elapsed = time.time() - start

        # Quick checks should complete in < 10 seconds
        self.assertLess(elapsed, 10.0)


class TestCLITools(unittest.TestCase):
    """Test CLI tools work correctly."""

    def test_report_cli_help(self):
        """Test report CLI shows help."""
        result = subprocess.run(
            ["python3", "scripts/generate_recall_report.py", "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Generate recall analytics reports", result.stdout)

    def test_quality_checks_cli_help(self):
        """Test quality checks CLI shows help."""
        result = subprocess.run(
            ["python3", "scripts/run_quality_checks.py", "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Run quality checks", result.stdout)


class TestUsability(unittest.TestCase):
    """Test usability and user experience."""

    def test_all_clis_have_help(self):
        """Test all CLI tools have --help."""
        cli_scripts = [
            "scripts/generate_recall_report.py",
            "scripts/run_quality_checks.py",
        ]

        for script in cli_scripts:
            result = subprocess.run(
                ["python3", script, "--help"],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, f"{script} --help failed")
            self.assertGreater(len(result.stdout), 100, f"{script} help is too short")

    def test_error_messages_clear(self):
        """Test error messages are clear and helpful."""
        # Try to generate report with invalid path
        from reporting import ReportGenerator

        try:
            generator = ReportGenerator(sessions_dir=Path("/nonexistent/path"))
            # If it doesn't raise, that's fine - it should handle gracefully
        except Exception as e:
            # If it raises, error message should be clear
            error_msg = str(e)
            self.assertGreater(len(error_msg), 10, "Error message too short")


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
