"""
Quality checks for recall analytics system.

Implements 7 automated checks to monitor system health:
1. LowRelevanceCheck - Detects searches with poor quality scores
2. NoResultsCheck - Monitors searches returning no results
3. HighLatencyCheck - Identifies performance degradation
4. IndexHealthCheck - Validates index integrity
5. EmbeddingDriftCheck - Detects embedding model changes
6. FalsePositiveCheck - Identifies irrelevant results
7. UsageAnomalyCheck - Detects unusual usage patterns
"""

import json
import statistics
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class CheckResult:
    """Result of a quality check."""
    check_name: str
    status: str  # "pass", "warning", "error"
    message: str
    details: Dict[str, Any]
    timestamp: str
    severity: str  # "info", "warning", "error"


class QualityCheck(ABC):
    """Base class for quality checks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize quality check.

        Args:
            config: Configuration dictionary with check-specific thresholds
        """
        self.config = config or {}

    @abstractmethod
    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """
        Run the quality check.

        Args:
            telemetry_events: List of telemetry events
            quality_events: List of quality scoring events
            impact_events: List of impact analysis events

        Returns:
            CheckResult with status and details
        """
        pass

    def _create_result(
        self,
        status: str,
        message: str,
        details: Dict[str, Any],
        severity: str = "info"
    ) -> CheckResult:
        """Create a CheckResult."""
        return CheckResult(
            check_name=self.__class__.__name__,
            status=status,
            message=message,
            details=details,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=severity,
        )


class LowRelevanceCheck(QualityCheck):
    """Check for searches with low quality scores."""

    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """Check for low relevance scores."""
        if not quality_events:
            return self._create_result(
                "pass",
                "No quality data to check",
                {"total_evaluations": 0},
                "info"
            )

        threshold = self.config.get("low_score_threshold", 0.4)
        warning_percent = self.config.get("warning_percent", 0.2)

        # Count low scores
        low_scores = [
            e for e in quality_events
            if e.get("scores", {}).get("overall", 1.0) < threshold
        ]

        low_percent = len(low_scores) / len(quality_events) if quality_events else 0

        if low_percent >= warning_percent:
            return self._create_result(
                "warning",
                f"{len(low_scores)} of {len(quality_events)} searches "
                f"({low_percent*100:.1f}%) have low quality scores (<{threshold})",
                {
                    "low_score_count": len(low_scores),
                    "total_evaluations": len(quality_events),
                    "low_score_percent": low_percent,
                    "threshold": threshold,
                    "sample_event_ids": [e.get("event_id") for e in low_scores[:5]],
                },
                "warning"
            )
        else:
            return self._create_result(
                "pass",
                f"Quality scores within acceptable range "
                f"({low_percent*100:.1f}% below {threshold})",
                {
                    "low_score_count": len(low_scores),
                    "total_evaluations": len(quality_events),
                    "low_score_percent": low_percent,
                },
                "info"
            )


class NoResultsCheck(QualityCheck):
    """Check for searches returning no results."""

    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """Check for high rate of empty results."""
        searches = [e for e in telemetry_events if e.get("event_type") == "search_completed"]

        if not searches:
            return self._create_result(
                "pass",
                "No search data to check",
                {"total_searches": 0},
                "info"
            )

        threshold_percent = self.config.get("no_results_threshold_percent", 0.3)

        # Count searches with no results
        no_results = [
            e for e in searches
            if len(e.get("results", {}).get("session_ids", [])) == 0
        ]

        no_results_percent = len(no_results) / len(searches)

        if no_results_percent >= threshold_percent:
            return self._create_result(
                "warning",
                f"{len(no_results)} of {len(searches)} searches "
                f"({no_results_percent*100:.1f}%) returned no results",
                {
                    "no_results_count": len(no_results),
                    "total_searches": len(searches),
                    "no_results_percent": no_results_percent,
                    "threshold_percent": threshold_percent,
                    "sample_queries": [e.get("query", "")[:50] for e in no_results[:5]],
                },
                "warning"
            )
        else:
            return self._create_result(
                "pass",
                f"Empty result rate acceptable ({no_results_percent*100:.1f}%)",
                {
                    "no_results_count": len(no_results),
                    "total_searches": len(searches),
                    "no_results_percent": no_results_percent,
                },
                "info"
            )


class HighLatencyCheck(QualityCheck):
    """Check for performance degradation."""

    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """Check for high latency searches."""
        searches = [e for e in telemetry_events if e.get("event_type") == "search_completed"]

        if not searches:
            return self._create_result(
                "pass",
                "No search data to check",
                {"total_searches": 0},
                "info"
            )

        latency_threshold = self.config.get("high_latency_ms", 1000)
        warning_percent = self.config.get("warning_percent", 0.1)

        # Get latencies
        latencies = []
        high_latency_searches = []
        for e in searches:
            latency = e.get("performance", {}).get("total_latency_ms")
            if latency is not None:
                latencies.append(latency)
                if latency > latency_threshold:
                    high_latency_searches.append(e)

        if not latencies:
            return self._create_result(
                "pass",
                "No latency data available",
                {},
                "info"
            )

        high_latency_percent = len(high_latency_searches) / len(latencies)
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

        if high_latency_percent >= warning_percent:
            return self._create_result(
                "warning",
                f"{len(high_latency_searches)} searches ({high_latency_percent*100:.1f}%) "
                f"exceeded {latency_threshold}ms latency",
                {
                    "high_latency_count": len(high_latency_searches),
                    "total_searches": len(latencies),
                    "high_latency_percent": high_latency_percent,
                    "avg_latency_ms": round(avg_latency, 2),
                    "p95_latency_ms": round(p95_latency, 2),
                    "threshold_ms": latency_threshold,
                },
                "warning"
            )
        else:
            return self._create_result(
                "pass",
                f"Latency within acceptable range (avg: {avg_latency:.0f}ms, "
                f"P95: {p95_latency:.0f}ms)",
                {
                    "avg_latency_ms": round(avg_latency, 2),
                    "p95_latency_ms": round(p95_latency, 2),
                    "high_latency_count": len(high_latency_searches),
                },
                "info"
            )


class IndexHealthCheck(QualityCheck):
    """Check index integrity and health."""

    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """Check index health."""
        # Get index path from config
        index_path = self.config.get("index_path", Path.home() / ".claude" / "context" / "sessions" / "index.json")
        index_path = Path(index_path)

        if not index_path.exists():
            return self._create_result(
                "error",
                f"Index file not found: {index_path}",
                {"index_path": str(index_path)},
                "error"
            )

        try:
            # Load and validate index
            with open(index_path, 'r') as f:
                index_data = json.load(f)

            sessions = index_data.get("sessions", [])

            if not sessions:
                return self._create_result(
                    "warning",
                    "Index is empty - no sessions indexed",
                    {
                        "session_count": 0,
                        "index_path": str(index_path),
                    },
                    "warning"
                )

            # Check for sessions without embeddings
            # Embeddings can be indicated by either:
            # 1. has_embedding flag (set by embed_sessions.py)
            # 2. embeddings array (legacy format)
            missing_embeddings = [
                s for s in sessions
                if not s.get("has_embedding", False) and
                   (not s.get("embeddings") or len(s.get("embeddings", [])) == 0)
            ]

            missing_percent = len(missing_embeddings) / len(sessions)

            if missing_percent > 0.1:  # >10% missing
                return self._create_result(
                    "warning",
                    f"{len(missing_embeddings)} of {len(sessions)} sessions "
                    f"({missing_percent*100:.1f}%) lack embeddings",
                    {
                        "total_sessions": len(sessions),
                        "missing_embeddings": len(missing_embeddings),
                        "missing_percent": missing_percent,
                        "index_path": str(index_path),
                    },
                    "warning"
                )
            else:
                return self._create_result(
                    "pass",
                    f"Index healthy: {len(sessions)} sessions indexed",
                    {
                        "total_sessions": len(sessions),
                        "missing_embeddings": len(missing_embeddings),
                        "index_path": str(index_path),
                    },
                    "info"
                )

        except json.JSONDecodeError as e:
            return self._create_result(
                "error",
                f"Index file corrupted: {e}",
                {"index_path": str(index_path), "error": str(e)},
                "error"
            )
        except Exception as e:
            return self._create_result(
                "error",
                f"Error checking index: {e}",
                {"index_path": str(index_path), "error": str(e)},
                "error"
            )


class EmbeddingDriftCheck(QualityCheck):
    """Check for embedding model changes or drift."""

    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """Check for embedding drift."""
        searches = [e for e in telemetry_events if e.get("event_type") == "search_completed"]

        if not searches:
            return self._create_result(
                "pass",
                "No search data to check",
                {"total_searches": 0},
                "info"
            )

        # Check for consistent embedding dimensions
        embedding_dims = []
        for search in searches:
            results = search.get("results", {})
            if "embedding_dim" in results:
                embedding_dims.append(results["embedding_dim"])

        if not embedding_dims:
            return self._create_result(
                "pass",
                "No embedding dimension data available",
                {},
                "info"
            )

        # Check for dimension changes
        unique_dims = set(embedding_dims)
        if len(unique_dims) > 1:
            return self._create_result(
                "warning",
                f"Detected {len(unique_dims)} different embedding dimensions: {unique_dims}",
                {
                    "embedding_dimensions": list(unique_dims),
                    "total_searches": len(embedding_dims),
                },
                "warning"
            )
        else:
            return self._create_result(
                "pass",
                f"Embedding dimensions consistent: {list(unique_dims)[0]}",
                {
                    "embedding_dimension": list(unique_dims)[0],
                    "total_searches": len(embedding_dims),
                },
                "info"
            )


class FalsePositiveCheck(QualityCheck):
    """Check for searches with low continuity despite high scores."""

    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """Check for potential false positives."""
        if not quality_events or not impact_events:
            return self._create_result(
                "pass",
                "Insufficient data for false positive detection",
                {
                    "quality_events": len(quality_events),
                    "impact_events": len(impact_events),
                },
                "info"
            )

        # Build map of event_id to quality and impact
        quality_map = {e.get("event_id"): e for e in quality_events}
        impact_map = {e.get("event_id"): e for e in impact_events}

        # Find events with high quality but low impact
        high_quality_threshold = self.config.get("high_quality_threshold", 0.7)
        low_continuity_threshold = self.config.get("low_continuity_threshold", 0.3)

        false_positives = []
        for event_id in quality_map:
            if event_id not in impact_map:
                continue

            quality_score = quality_map[event_id].get("scores", {}).get("overall", 0)
            continuity_score = impact_map[event_id].get("continuity_score", 0)

            if quality_score >= high_quality_threshold and continuity_score < low_continuity_threshold:
                false_positives.append({
                    "event_id": event_id,
                    "quality_score": quality_score,
                    "continuity_score": continuity_score,
                })

        if len(false_positives) > 3:  # More than 3 potential false positives
            return self._create_result(
                "warning",
                f"Detected {len(false_positives)} potential false positives "
                f"(high quality, low continuity)",
                {
                    "false_positive_count": len(false_positives),
                    "samples": false_positives[:5],
                },
                "warning"
            )
        else:
            return self._create_result(
                "pass",
                f"False positive rate acceptable ({len(false_positives)} detected)",
                {
                    "false_positive_count": len(false_positives),
                },
                "info"
            )


class UsageAnomalyCheck(QualityCheck):
    """Check for unusual usage patterns."""

    def run(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict],
        impact_events: List[Dict],
    ) -> CheckResult:
        """Check for usage anomalies."""
        searches = [e for e in telemetry_events if e.get("event_type") == "search_completed"]

        if len(searches) < 10:  # Need minimum data
            return self._create_result(
                "pass",
                "Insufficient data for anomaly detection",
                {"total_searches": len(searches)},
                "info"
            )

        # Check for sudden spike in search volume
        # Group searches by hour
        hourly_counts = {}
        for search in searches:
            timestamp_str = search.get("timestamp", "")
            if timestamp_str:
                try:
                    if timestamp_str.endswith('Z'):
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    else:
                        timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)

                    hour_key = timestamp.strftime("%Y-%m-%d-%H")
                    hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
                except:
                    continue

        if not hourly_counts:
            return self._create_result(
                "pass",
                "No timestamp data for anomaly detection",
                {},
                "info"
            )

        counts = list(hourly_counts.values())
        avg_count = statistics.mean(counts)
        max_count = max(counts)

        # Check for spike (>3x average)
        spike_threshold = self.config.get("spike_threshold", 3.0)
        if max_count > avg_count * spike_threshold and avg_count > 0:
            return self._create_result(
                "warning",
                f"Usage spike detected: {max_count} searches in one hour "
                f"(avg: {avg_count:.1f})",
                {
                    "max_hourly_searches": max_count,
                    "avg_hourly_searches": round(avg_count, 2),
                    "spike_ratio": round(max_count / avg_count, 2),
                },
                "warning"
            )
        else:
            return self._create_result(
                "pass",
                f"Usage patterns normal (max: {max_count}/hour, avg: {avg_count:.1f}/hour)",
                {
                    "max_hourly_searches": max_count,
                    "avg_hourly_searches": round(avg_count, 2),
                },
                "info"
            )


# Registry of all checks
ALL_CHECKS = [
    LowRelevanceCheck,
    NoResultsCheck,
    HighLatencyCheck,
    IndexHealthCheck,
    EmbeddingDriftCheck,
    FalsePositiveCheck,
    UsageAnomalyCheck,
]
