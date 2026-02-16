"""
Data aggregation for recall analytics reporting.

Loads telemetry, impact, and quality logs, then computes aggregate statistics,
distributions, trends, and identifies top sessions.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics


class DataAggregator:
    """Aggregates analytics data from multiple log sources."""

    def __init__(self, sessions_dir: Path):
        """Initialize aggregator with sessions directory path."""
        self.sessions_dir = Path(sessions_dir)
        self.telemetry_log = self.sessions_dir / "recall_analytics.jsonl"
        self.impact_log = self.sessions_dir / "context_impact.jsonl"
        self.quality_log = self.sessions_dir / "quality_scores.jsonl"

    def generate_report_data(self, period_days: int = 30) -> Dict[str, Any]:
        """
        Generate complete report data for the specified period.

        Args:
            period_days: Number of days to include in report

        Returns:
            Dictionary with all aggregated metrics
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Load filtered data
        telemetry_events = self._load_events(self.telemetry_log, cutoff_date)
        impact_events = self._load_events(self.impact_log, cutoff_date)
        quality_events = self._load_events(self.quality_log, cutoff_date)

        return {
            "period": {
                "days": period_days,
                "start_date": cutoff_date.isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat(),
            },
            "usage": self._analyze_usage(telemetry_events),
            "quality": self._analyze_quality(quality_events),
            "impact": self._analyze_impact(impact_events),
            "top_sessions": self._identify_top_sessions(telemetry_events, impact_events),
            "performance": self._analyze_performance(telemetry_events),
            "issues": self._identify_issues(telemetry_events, quality_events),
            "costs": self._analyze_costs(quality_events),
        }

    def _load_events(self, log_path: Path, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Load and filter events from JSONL log."""
        events = []
        if not log_path.exists():
            return events

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
                            # Handle both ISO format with/without timezone
                            if timestamp_str.endswith('Z'):
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                                timestamp = datetime.fromisoformat(timestamp_str)
                            else:
                                # No timezone, assume UTC
                                timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)

                            if timestamp >= cutoff_date:
                                events.append(event)
                    except (json.JSONDecodeError, ValueError) as e:
                        # Skip malformed lines
                        continue
        except Exception as e:
            print(f"Warning: Error loading {log_path}: {e}")

        return events

    def _analyze_usage(self, telemetry_events: List[Dict]) -> Dict[str, Any]:
        """Analyze usage patterns from telemetry."""
        if not telemetry_events:
            return {
                "total_searches": 0,
                "unique_sessions": 0,
                "searches_per_day": 0.0,
                "mode_distribution": {},
                "avg_results_per_search": 0.0,
            }

        # Filter to search_completed events
        searches = [e for e in telemetry_events if e.get('event_type') == 'search_completed']

        if not searches:
            return {
                "total_searches": 0,
                "unique_sessions": 0,
                "searches_per_day": 0.0,
                "mode_distribution": {},
                "avg_results_per_search": 0.0,
            }

        # Count by mode
        mode_counts = defaultdict(int)
        for search in searches:
            mode = search.get('search_config', {}).get('mode_resolved', 'unknown')
            mode_counts[mode] += 1

        # Unique sessions
        unique_sessions = len(set(
            e.get('session_id') for e in searches if e.get('session_id')
        ))

        # Results per search
        result_counts = [
            len(e.get('results', {}).get('session_ids', []))
            for e in searches
        ]
        avg_results = statistics.mean(result_counts) if result_counts else 0.0

        # Calculate daily rate
        if searches:
            timestamps = []
            for s in searches:
                ts_str = s.get('timestamp', '')
                if ts_str:
                    try:
                        if ts_str.endswith('Z'):
                            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        elif '+' in ts_str or ts_str.count('-') > 2:
                            ts = datetime.fromisoformat(ts_str)
                        else:
                            ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                        timestamps.append(ts)
                    except:
                        continue

            if timestamps and len(timestamps) > 1:
                time_span = (max(timestamps) - min(timestamps)).total_seconds() / 86400
                searches_per_day = len(searches) / max(time_span, 1.0)
            else:
                searches_per_day = len(searches)
        else:
            searches_per_day = 0.0

        return {
            "total_searches": len(searches),
            "unique_sessions": unique_sessions,
            "searches_per_day": round(searches_per_day, 2),
            "mode_distribution": dict(mode_counts),
            "avg_results_per_search": round(avg_results, 2),
        }

    def _analyze_quality(self, quality_events: List[Dict]) -> Dict[str, Any]:
        """Analyze quality scores."""
        if not quality_events:
            return {
                "total_evaluations": 0,
                "avg_relevance": 0.0,
                "avg_coverage": 0.0,
                "avg_specificity": 0.0,
                "overall_score": 0.0,
                "score_distribution": {},
            }

        relevance_scores = []
        coverage_scores = []
        specificity_scores = []
        overall_scores = []

        for event in quality_events:
            scores = event.get('scores', {})
            if 'relevance' in scores:
                relevance_scores.append(scores['relevance'])
            if 'coverage' in scores:
                coverage_scores.append(scores['coverage'])
            if 'specificity' in scores:
                specificity_scores.append(scores['specificity'])
            if 'overall' in scores:
                overall_scores.append(scores['overall'])

        # Score distribution (binned)
        score_bins = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        for score in overall_scores:
            if score >= 0.8:
                score_bins["excellent"] += 1
            elif score >= 0.6:
                score_bins["good"] += 1
            elif score >= 0.4:
                score_bins["fair"] += 1
            else:
                score_bins["poor"] += 1

        return {
            "total_evaluations": len(quality_events),
            "avg_relevance": round(statistics.mean(relevance_scores), 3) if relevance_scores else 0.0,
            "avg_coverage": round(statistics.mean(coverage_scores), 3) if coverage_scores else 0.0,
            "avg_specificity": round(statistics.mean(specificity_scores), 3) if specificity_scores else 0.0,
            "overall_score": round(statistics.mean(overall_scores), 3) if overall_scores else 0.0,
            "score_distribution": score_bins,
        }

    def _analyze_impact(self, impact_events: List[Dict]) -> Dict[str, Any]:
        """Analyze context impact."""
        if not impact_events:
            return {
                "total_analyses": 0,
                "avg_explicit_citations": 0.0,
                "avg_implicit_usage": 0.0,
                "avg_continuity_score": 0.0,
                "avg_efficiency_gain": 0.0,
            }

        explicit_citations = []
        implicit_usage = []
        continuity_scores = []
        efficiency_gains = []

        for event in impact_events:
            usage = event.get('context_usage', {})
            if 'explicit_citations' in usage:
                explicit_citations.append(usage['explicit_citations'])
            if 'implicit_usage_score' in usage:
                implicit_usage.append(usage['implicit_usage_score'])

            continuity = event.get('continuity_score')
            if continuity is not None:
                continuity_scores.append(continuity)

            efficiency = event.get('efficiency_metrics', {})
            if 'estimated_time_saved_minutes' in efficiency:
                efficiency_gains.append(efficiency['estimated_time_saved_minutes'])

        return {
            "total_analyses": len(impact_events),
            "avg_explicit_citations": round(statistics.mean(explicit_citations), 2) if explicit_citations else 0.0,
            "avg_implicit_usage": round(statistics.mean(implicit_usage), 3) if implicit_usage else 0.0,
            "avg_continuity_score": round(statistics.mean(continuity_scores), 3) if continuity_scores else 0.0,
            "avg_efficiency_gain": round(statistics.mean(efficiency_gains), 2) if efficiency_gains else 0.0,
        }

    def _identify_top_sessions(
        self,
        telemetry_events: List[Dict],
        impact_events: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Identify most valuable sessions."""
        # Group impact by session
        session_impact = defaultdict(list)
        for event in impact_events:
            session_id = event.get('session_id')
            if session_id:
                session_impact[session_id].append(event)

        # Calculate aggregate value per session
        session_scores = []
        for session_id, events in session_impact.items():
            # Average continuity score
            continuity_scores = [
                e.get('continuity_score', 0) for e in events if e.get('continuity_score') is not None
            ]
            avg_continuity = statistics.mean(continuity_scores) if continuity_scores else 0

            # Total time saved
            time_saved = sum(
                e.get('efficiency_metrics', {}).get('estimated_time_saved_minutes', 0)
                for e in events
            )

            # Total explicit citations
            total_citations = sum(
                e.get('context_usage', {}).get('explicit_citations', 0)
                for e in events
            )

            # Composite score
            composite = (avg_continuity * 0.4) + (min(time_saved / 60, 1.0) * 0.4) + (min(total_citations / 10, 1.0) * 0.2)

            session_scores.append({
                "session_id": session_id,
                "composite_score": composite,
                "avg_continuity": round(avg_continuity, 3),
                "time_saved_minutes": round(time_saved, 2),
                "total_citations": total_citations,
            })

        # Sort by composite score
        session_scores.sort(key=lambda x: x['composite_score'], reverse=True)

        return session_scores[:10]  # Top 10

    def _analyze_performance(self, telemetry_events: List[Dict]) -> Dict[str, Any]:
        """Analyze performance metrics."""
        searches = [e for e in telemetry_events if e.get('event_type') == 'search_completed']

        if not searches:
            return {
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "cache_hit_rate": 0.0,
            }

        # Collect latencies
        latencies = []
        cache_hits = 0
        cache_total = 0

        for search in searches:
            perf = search.get('performance', {})
            if 'total_latency_ms' in perf:
                latencies.append(perf['total_latency_ms'])

            if 'cache_hit' in perf:
                cache_total += 1
                if perf['cache_hit']:
                    cache_hits += 1

        if latencies:
            latencies.sort()
            p50_idx = int(len(latencies) * 0.50)
            p95_idx = int(len(latencies) * 0.95)
            p99_idx = int(len(latencies) * 0.99)

            return {
                "avg_latency_ms": round(statistics.mean(latencies), 2),
                "p50_latency_ms": round(latencies[p50_idx], 2),
                "p95_latency_ms": round(latencies[p95_idx], 2),
                "p99_latency_ms": round(latencies[p99_idx], 2),
                "cache_hit_rate": round(cache_hits / cache_total, 3) if cache_total > 0 else 0.0,
            }

        return {
            "avg_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "cache_hit_rate": 0.0,
        }

    def _identify_issues(
        self,
        telemetry_events: List[Dict],
        quality_events: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Identify potential issues and recommendations."""
        issues = []

        # Check for low quality scores
        if quality_events:
            low_quality = [e for e in quality_events if e.get('scores', {}).get('overall', 1.0) < 0.4]
            if len(low_quality) > len(quality_events) * 0.2:  # >20% low quality
                issues.append({
                    "severity": "warning",
                    "category": "quality",
                    "message": f"{len(low_quality)} searches ({len(low_quality)/len(quality_events)*100:.1f}%) had low quality scores (<0.4)",
                    "recommendation": "Review index content and search query patterns. Consider reindexing or improving query formulation.",
                })

        # Check for high latency
        searches = [e for e in telemetry_events if e.get('event_type') == 'search_completed']
        if searches:
            high_latency = [
                e for e in searches
                if e.get('performance', {}).get('total_latency_ms', 0) > 1000
            ]
            if len(high_latency) > len(searches) * 0.1:  # >10% slow
                issues.append({
                    "severity": "warning",
                    "category": "performance",
                    "message": f"{len(high_latency)} searches ({len(high_latency)/len(searches)*100:.1f}%) exceeded 1000ms latency",
                    "recommendation": "Consider optimizing index, enabling caching, or reducing index size.",
                })

        # Check for no results
        if searches:
            no_results = [
                e for e in searches
                if len(e.get('results', {}).get('session_ids', [])) == 0
            ]
            if len(no_results) > len(searches) * 0.3:  # >30% empty
                issues.append({
                    "severity": "info",
                    "category": "usage",
                    "message": f"{len(no_results)} searches ({len(no_results)/len(searches)*100:.1f}%) returned no results",
                    "recommendation": "Review query patterns. Users may need different search terms or more indexed content.",
                })

        return issues

    def _analyze_costs(self, quality_events: List[Dict]) -> Dict[str, Any]:
        """Analyze quality scoring costs."""
        if not quality_events:
            return {
                "total_evaluations": 0,
                "total_cost_usd": 0.0,
                "avg_cost_per_eval": 0.0,
                "total_tokens": 0,
            }

        total_cost = sum(e.get('cost_usd', 0) for e in quality_events)
        total_tokens = sum(
            e.get('usage', {}).get('input_tokens', 0) + e.get('usage', {}).get('output_tokens', 0)
            for e in quality_events
        )

        return {
            "total_evaluations": len(quality_events),
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_eval": round(total_cost / len(quality_events), 6) if quality_events else 0.0,
            "total_tokens": total_tokens,
        }
