#!/usr/bin/env python3
"""
Tests for recall analytics reporting system.

Run with: python3 -m pytest scripts/reporting/test_reporting.py -v
Or: python3 scripts/reporting/test_reporting.py
"""

import unittest
import json
import tempfile
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path for imports when run directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from reporting.aggregator import DataAggregator
from reporting.formatters import MarkdownFormatter, JSONFormatter, HTMLFormatter, ASCIIChart
from reporting.generator import ReportGenerator


class TestASCIIChart(unittest.TestCase):
    """Test ASCII chart generation."""

    def test_bar_chart(self):
        """Test horizontal bar chart generation."""
        data = {"mode_a": 10, "mode_b": 5, "mode_c": 2}
        chart = ASCIIChart.bar_chart(data, max_width=20)

        self.assertIn("mode_a", chart)
        self.assertIn("mode_b", chart)
        self.assertIn("mode_c", chart)
        self.assertIn("10", chart)
        self.assertIn("5", chart)
        self.assertIn("2", chart)

    def test_bar_chart_empty(self):
        """Test bar chart with empty data."""
        chart = ASCIIChart.bar_chart({})
        self.assertEqual(chart, "No data")

    def test_sparkline(self):
        """Test sparkline generation."""
        values = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        sparkline = ASCIIChart.sparkline(values)

        self.assertIsInstance(sparkline, str)
        self.assertEqual(len(sparkline), len(values))

    def test_sparkline_empty(self):
        """Test sparkline with empty data."""
        sparkline = ASCIIChart.sparkline([])
        self.assertEqual(sparkline, "")


class TestDataAggregator(unittest.TestCase):
    """Test data aggregation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir)

        # Create sample telemetry log
        self.telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        telemetry_data = [
            {
                "event_id": "evt1",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "event_type": "search_completed",
                "session_id": "session1",
                "query": "test query",
                "search_config": {"mode_resolved": "hybrid"},
                "results": {"session_ids": ["s1", "s2", "s3"]},
                "performance": {
                    "total_latency_ms": 250,
                    "cache_hit": False,
                },
            },
            {
                "event_id": "evt2",
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
                "event_type": "search_completed",
                "session_id": "session2",
                "query": "another query",
                "search_config": {"mode_resolved": "semantic"},
                "results": {"session_ids": ["s4", "s5"]},
                "performance": {
                    "total_latency_ms": 180,
                    "cache_hit": True,
                },
            },
        ]

        with open(self.telemetry_log, 'w') as f:
            for event in telemetry_data:
                f.write(json.dumps(event) + "\n")

        # Create sample quality log
        self.quality_log = self.sessions_dir / "quality_scores.jsonl"
        quality_data = [
            {
                "event_id": "evt1",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "scores": {
                    "relevance": 0.85,
                    "coverage": 0.75,
                    "specificity": 0.90,
                    "overall": 0.83,
                },
                "cost_usd": 0.0004,
                "usage": {"input_tokens": 500, "output_tokens": 100},
            },
        ]

        with open(self.quality_log, 'w') as f:
            for event in quality_data:
                f.write(json.dumps(event) + "\n")

        # Create sample impact log
        self.impact_log = self.sessions_dir / "context_impact.jsonl"
        impact_data = [
            {
                "event_id": "evt1",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "session_id": "session1",
                "context_usage": {
                    "explicit_citations": 3,
                    "implicit_usage_score": 0.7,
                },
                "continuity_score": 0.85,
                "efficiency_metrics": {
                    "estimated_time_saved_minutes": 15.5,
                },
            },
        ]

        with open(self.impact_log, 'w') as f:
            for event in impact_data:
                f.write(json.dumps(event) + "\n")

    def test_aggregator_initialization(self):
        """Test aggregator initializes correctly."""
        aggregator = DataAggregator(self.sessions_dir)
        self.assertEqual(aggregator.sessions_dir, self.sessions_dir)
        self.assertTrue(aggregator.telemetry_log.exists())

    def test_load_events(self):
        """Test loading events from JSONL."""
        aggregator = DataAggregator(self.sessions_dir)
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        events = aggregator._load_events(self.telemetry_log, cutoff)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_id"], "evt1")

    def test_analyze_usage(self):
        """Test usage analysis."""
        aggregator = DataAggregator(self.sessions_dir)
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        events = aggregator._load_events(self.telemetry_log, cutoff)
        usage = aggregator._analyze_usage(events)

        self.assertEqual(usage["total_searches"], 2)
        self.assertEqual(usage["unique_sessions"], 2)
        self.assertIn("hybrid", usage["mode_distribution"])
        self.assertIn("semantic", usage["mode_distribution"])

    def test_analyze_quality(self):
        """Test quality analysis."""
        aggregator = DataAggregator(self.sessions_dir)
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        events = aggregator._load_events(self.quality_log, cutoff)
        quality = aggregator._analyze_quality(events)

        self.assertEqual(quality["total_evaluations"], 1)
        self.assertAlmostEqual(quality["avg_relevance"], 0.85, places=2)
        self.assertAlmostEqual(quality["overall_score"], 0.83, places=2)

    def test_analyze_impact(self):
        """Test impact analysis."""
        aggregator = DataAggregator(self.sessions_dir)
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        events = aggregator._load_events(self.impact_log, cutoff)
        impact = aggregator._analyze_impact(events)

        self.assertEqual(impact["total_analyses"], 1)
        self.assertAlmostEqual(impact["avg_explicit_citations"], 3.0, places=1)
        self.assertAlmostEqual(impact["avg_continuity_score"], 0.85, places=2)

    def test_analyze_performance(self):
        """Test performance analysis."""
        aggregator = DataAggregator(self.sessions_dir)
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        events = aggregator._load_events(self.telemetry_log, cutoff)
        performance = aggregator._analyze_performance(events)

        self.assertGreater(performance["avg_latency_ms"], 0)
        self.assertGreater(performance["p50_latency_ms"], 0)
        self.assertGreaterEqual(performance["cache_hit_rate"], 0)

    def test_generate_report_data(self):
        """Test full report data generation."""
        aggregator = DataAggregator(self.sessions_dir)
        data = aggregator.generate_report_data(period_days=7)

        # Check all sections present
        self.assertIn("period", data)
        self.assertIn("usage", data)
        self.assertIn("quality", data)
        self.assertIn("impact", data)
        self.assertIn("top_sessions", data)
        self.assertIn("performance", data)
        self.assertIn("issues", data)
        self.assertIn("costs", data)

    def test_handle_missing_logs(self):
        """Test graceful handling of missing log files."""
        empty_dir = Path(tempfile.mkdtemp())
        aggregator = DataAggregator(empty_dir)
        data = aggregator.generate_report_data(period_days=7)

        # Should return empty/default values
        self.assertEqual(data["usage"]["total_searches"], 0)
        self.assertEqual(data["quality"]["total_evaluations"], 0)
        self.assertEqual(data["impact"]["total_analyses"], 0)


class TestFormatters(unittest.TestCase):
    """Test report formatters."""

    def setUp(self):
        """Set up sample data."""
        self.sample_data = {
            "period": {
                "days": 7,
                "start_date": "2024-01-01T00:00:00+00:00",
                "end_date": "2024-01-08T00:00:00+00:00",
            },
            "usage": {
                "total_searches": 10,
                "unique_sessions": 5,
                "searches_per_day": 1.43,
                "mode_distribution": {"hybrid": 6, "semantic": 4},
                "avg_results_per_search": 3.5,
            },
            "quality": {
                "total_evaluations": 5,
                "avg_relevance": 0.80,
                "avg_coverage": 0.75,
                "avg_specificity": 0.85,
                "overall_score": 0.80,
                "score_distribution": {"excellent": 2, "good": 2, "fair": 1, "poor": 0},
            },
            "impact": {
                "total_analyses": 3,
                "avg_explicit_citations": 2.5,
                "avg_implicit_usage": 0.65,
                "avg_continuity_score": 0.75,
                "avg_efficiency_gain": 12.3,
            },
            "top_sessions": [
                {
                    "session_id": "session1",
                    "composite_score": 0.85,
                    "avg_continuity": 0.90,
                    "time_saved_minutes": 20.0,
                    "total_citations": 5,
                }
            ],
            "performance": {
                "avg_latency_ms": 250.5,
                "p50_latency_ms": 200.0,
                "p95_latency_ms": 450.0,
                "p99_latency_ms": 500.0,
                "cache_hit_rate": 0.35,
            },
            "issues": [],
            "costs": {
                "total_evaluations": 5,
                "total_cost_usd": 0.0020,
                "avg_cost_per_eval": 0.0004,
                "total_tokens": 3000,
            },
        }

    def test_markdown_full_format(self):
        """Test full Markdown report formatting."""
        report = MarkdownFormatter.format(self.sample_data, full=True)

        # Check major sections present
        self.assertIn("# Recall Analytics Report", report)
        self.assertIn("## Executive Summary", report)
        self.assertIn("## Usage Statistics", report)
        self.assertIn("## Quality Metrics", report)
        self.assertIn("## Performance Benchmarks", report)

        # Check data values present
        self.assertIn("10", report)  # total searches
        self.assertIn("0.800", report)  # quality score

    def test_markdown_summary_format(self):
        """Test brief Markdown summary formatting."""
        report = MarkdownFormatter.format(self.sample_data, full=False)

        # Should be much shorter than full report
        self.assertLess(len(report), 1000)

        # Check key elements
        self.assertIn("# Recall Analytics Summary", report)
        self.assertIn("10 searches", report)

    def test_json_format(self):
        """Test JSON formatting."""
        report = JSONFormatter.format(self.sample_data)

        # Should be valid JSON
        parsed = json.loads(report)
        self.assertIn("report_data", parsed)
        self.assertIn("generated_at", parsed)

        # Check data preserved
        self.assertEqual(parsed["report_data"]["usage"]["total_searches"], 10)

    def test_html_format(self):
        """Test HTML formatting."""
        report = HTMLFormatter.format(self.sample_data)

        # Check HTML structure
        self.assertIn("<!DOCTYPE html>", report)
        self.assertIn("<html>", report)
        self.assertIn("</html>", report)
        self.assertIn("Recall Analytics Report", report)

        # Check data present
        self.assertIn("10", report)  # total searches


class TestReportGenerator(unittest.TestCase):
    """Test report generator."""

    def setUp(self):
        """Set up test generator."""
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir)

        # Create minimal test data
        telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        with open(telemetry_log, 'w') as f:
            event = {
                "event_id": "test1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "search_completed",
                "session_id": "s1",
                "search_config": {"mode_resolved": "hybrid"},
                "results": {"session_ids": []},
                "performance": {"total_latency_ms": 100},
            }
            f.write(json.dumps(event) + "\n")

        self.generator = ReportGenerator(sessions_dir=self.sessions_dir)

    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        self.assertIsNotNone(self.generator.aggregator)
        self.assertEqual(self.generator.sessions_dir, self.sessions_dir)

    def test_generate_summary(self):
        """Test summary generation."""
        summary = self.generator.generate_summary(period_days=7)

        self.assertIsInstance(summary, str)
        self.assertIn("Summary", summary)

    def test_generate_report_markdown(self):
        """Test full Markdown report generation."""
        report = self.generator.generate_report(
            period_days=7,
            format="markdown",
        )

        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 100)

    def test_generate_report_json(self):
        """Test JSON report generation."""
        report = self.generator.generate_report(
            period_days=7,
            format="json",
        )

        # Should be valid JSON
        parsed = json.loads(report)
        self.assertIn("report_data", parsed)

    def test_generate_report_html(self):
        """Test HTML report generation."""
        report = self.generator.generate_report(
            period_days=7,
            format="html",
        )

        self.assertIn("<!DOCTYPE html>", report)

    def test_generate_report_with_output_file(self):
        """Test report generation with file output."""
        output_file = Path(self.temp_dir) / "test_report.md"

        report = self.generator.generate_report(
            period_days=7,
            format="markdown",
            output_path=output_file,
        )

        # File should exist
        self.assertTrue(output_file.exists())

        # File should contain report
        with open(output_file, 'r') as f:
            content = f.read()
            self.assertEqual(content, report)

    def test_get_raw_data(self):
        """Test raw data retrieval."""
        data = self.generator.get_raw_data(period_days=7)

        self.assertIsInstance(data, dict)
        self.assertIn("usage", data)
        self.assertIn("quality", data)
        self.assertIn("impact", data)


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
