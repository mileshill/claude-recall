"""
Main impact analyzer for recall context.

Orchestrates detection, scoring, and metrics to analyze recall impact.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from impact_analysis.detector import ContextUsageDetector
from impact_analysis.scorer import ContinuityScorer
from impact_analysis.metrics import EfficiencyMetrics
from metrics.jsonl_utils import JSONLWriter
from metrics.config import config


class ImpactAnalyzer:
    """
    Main class for analyzing recall context impact.

    Combines detection, scoring, and metrics to provide comprehensive
    impact analysis for each recall event.
    """

    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize analyzer.

        Args:
            log_path: Path to impact analysis log file
        """
        self.detector = ContextUsageDetector()
        self.scorer = ContinuityScorer()
        self.metrics = EfficiencyMetrics()

        # Configure logging
        if log_path is None:
            log_path_str = config.get(
                'impact_analysis.log_path',
                '.claude/context/sessions/context_impact.jsonl'
            )
            log_path = Path(log_path_str).expanduser()

        # Make absolute
        if not log_path.is_absolute():
            log_path = Path.cwd() / log_path

        self.log_path = log_path
        self.writer = JSONLWriter(log_path)

    def analyze_recall_event(
        self,
        recall_event_id: str,
        current_transcript: str,
        recalled_sessions: List[Dict],
        session_data: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze impact of a recall event.

        Args:
            recall_event_id: ID of recall telemetry event
            current_transcript: Current conversation transcript
            recalled_sessions: List of recalled session data
            session_data: Current session metadata (optional)

        Returns:
            Dictionary with complete impact analysis
        """
        if not recalled_sessions:
            return {
                'recall_event_id': recall_event_id,
                'analyzed_at': datetime.now(timezone.utc).isoformat(),
                'recall_used': False,
                'impact_score': 0.0,
                'analysis': {}
            }

        # 1. Detect context usage
        usage_analysis = self._detect_context_usage(
            current_transcript,
            recalled_sessions
        )

        # 2. Score continuity
        continuity_scores = self._score_continuity(
            current_transcript,
            recalled_sessions,
            session_data
        )

        # 3. Calculate efficiency
        efficiency_metrics = self._calculate_efficiency(
            session_data or {},
            recalled_sessions
        )

        # 4. Calculate overall impact
        impact_score = self._calculate_impact_score(
            usage_analysis,
            continuity_scores,
            efficiency_metrics
        )

        # Compile results
        result = {
            'recall_event_id': recall_event_id,
            'analyzed_at': datetime.now(timezone.utc).isoformat(),
            'recall_used': usage_analysis['usage_score']['total_score'] > 0.1,
            'impact_score': impact_score,
            'usage_analysis': usage_analysis,
            'continuity_scores': continuity_scores,
            'efficiency_metrics': efficiency_metrics,
            'recalled_session_count': len(recalled_sessions),
            'recalled_session_ids': [s.get('id', 'unknown') for s in recalled_sessions]
        }

        # Log result
        try:
            self.writer.append(result)
        except Exception as e:
            print(f"Warning: Failed to log impact analysis: {e}", file=sys.stderr)

        return result

    def _detect_context_usage(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict]
    ) -> Dict:
        """Detect how context was used."""
        # Explicit citations
        explicit_citations = self.detector.detect_explicit_citations(current_transcript)

        # Implicit usage
        implicit_usage = self.detector.detect_implicit_usage(
            current_transcript,
            recalled_sessions
        )

        # Reused topics
        reused_topics = self.detector.detect_reused_topics(
            current_transcript,
            recalled_sessions
        )

        # File references
        file_references = self.detector.detect_file_references(
            current_transcript,
            recalled_sessions
        )

        # Calculate usage score
        usage_score = self.detector.calculate_usage_score(
            explicit_citations,
            implicit_usage,
            reused_topics,
            file_references
        )

        return {
            'explicit_citations': explicit_citations,
            'implicit_usage': implicit_usage,
            'reused_topics': reused_topics,
            'file_references': file_references,
            'usage_score': usage_score
        }

    def _score_continuity(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict],
        session_data: Optional[Dict]
    ) -> Dict:
        """Score continuity and consistency."""
        # Get current session time if available
        current_time = None
        if session_data and 'timestamp' in session_data:
            try:
                timestamp_str = session_data['timestamp']
                current_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception:
                current_time = datetime.now(timezone.utc)

        # Calculate continuity scores
        continuity = self.scorer.score_continuity(
            current_transcript,
            recalled_sessions,
            current_time
        )

        # Add terminology evolution if we have session sequence
        if session_data:
            evolution = self.scorer.score_terminology_evolution(
                recalled_sessions + [session_data]
            )
            continuity['terminology_evolution'] = evolution

        return continuity

    def _calculate_efficiency(
        self,
        session_data: Dict,
        recalled_sessions: List[Dict]
    ) -> Dict:
        """Calculate efficiency gains."""
        # Efficiency gains
        efficiency_gain = self.metrics.calculate_efficiency_gain(
            session_data,
            recalled_sessions
        )

        # Productivity metrics (if we have multiple sessions)
        if len(recalled_sessions) > 1:
            productivity = self.metrics.calculate_productivity_metrics(
                recalled_sessions
            )
            efficiency_gain['productivity_metrics'] = productivity

        return efficiency_gain

    def _check_repetition_avoidance(
        self,
        session_data: Dict,
        recalled_sessions: List[Dict]
    ) -> Dict:
        """Check if recall helped avoid repetition."""
        return self.metrics._check_repetition_avoidance(
            session_data,
            recalled_sessions
        )

    def _calculate_impact_score(
        self,
        usage_analysis: Dict,
        continuity_scores: Dict,
        efficiency_metrics: Dict
    ) -> float:
        """
        Calculate overall impact score.

        Args:
            usage_analysis: Context usage analysis
            continuity_scores: Continuity scores
            efficiency_metrics: Efficiency metrics

        Returns:
            Overall impact score (0-1)
        """
        # Component scores
        usage_score = usage_analysis['usage_score']['total_score']
        continuity_score = continuity_scores['total_score']
        efficiency_score = efficiency_metrics['efficiency_score']

        # Weighted average
        weights = {
            'usage': 0.4,
            'continuity': 0.3,
            'efficiency': 0.3
        }

        impact_score = (
            weights['usage'] * usage_score +
            weights['continuity'] * continuity_score +
            weights['efficiency'] * efficiency_score
        )

        return impact_score

    def analyze_session_sequence(
        self,
        session_sequence: List[Dict],
        recall_events: List[Dict]
    ) -> Dict:
        """
        Analyze impact across a sequence of sessions.

        Args:
            session_sequence: Ordered list of sessions
            recall_events: List of recall events for these sessions

        Returns:
            Dictionary with sequence analysis
        """
        # Learning curve
        learning = self.metrics.calculate_learning_curve(session_sequence)

        # Productivity metrics
        productivity = self.metrics.calculate_productivity_metrics(session_sequence)

        # Terminology evolution
        evolution = self.scorer.score_terminology_evolution(session_sequence)

        # Recall effectiveness over time
        recall_usage_rate = len([
            e for e in recall_events
            if e.get('recall_used', False)
        ]) / max(len(recall_events), 1)

        avg_impact_score = sum(
            e.get('impact_score', 0)
            for e in recall_events
        ) / max(len(recall_events), 1)

        return {
            'session_count': len(session_sequence),
            'recall_event_count': len(recall_events),
            'learning_metrics': learning,
            'productivity_metrics': productivity,
            'terminology_evolution': evolution,
            'recall_usage_rate': recall_usage_rate,
            'avg_impact_score': avg_impact_score
        }

    def generate_summary_report(
        self,
        impact_analyses: List[Dict]
    ) -> str:
        """
        Generate human-readable summary report.

        Args:
            impact_analyses: List of impact analysis results

        Returns:
            Formatted summary string
        """
        if not impact_analyses:
            return "No impact analyses available."

        # Calculate aggregate metrics
        total_analyses = len(impact_analyses)
        used_count = sum(1 for a in impact_analyses if a.get('recall_used', False))
        usage_rate = used_count / total_analyses

        avg_impact = sum(a.get('impact_score', 0) for a in impact_analyses) / total_analyses

        # Time saved
        total_time_saved = sum(
            a.get('efficiency_metrics', {}).get('estimated_time_saved_minutes', 0)
            for a in impact_analyses
        )

        # Build report
        lines = []
        lines.append("=" * 60)
        lines.append("Recall Context Impact Summary")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Total Analyses: {total_analyses}")
        lines.append(f"Recall Usage Rate: {usage_rate:.1%}")
        lines.append(f"Average Impact Score: {avg_impact:.2f}")
        lines.append(f"Estimated Time Saved: {total_time_saved:.1f} minutes")
        lines.append("")

        # Impact distribution
        high_impact = sum(1 for a in impact_analyses if a.get('impact_score', 0) >= 0.7)
        medium_impact = sum(1 for a in impact_analyses if 0.4 <= a.get('impact_score', 0) < 0.7)
        low_impact = sum(1 for a in impact_analyses if a.get('impact_score', 0) < 0.4)

        lines.append("Impact Distribution:")
        lines.append(f"  High (0.7+):   {high_impact} ({high_impact/total_analyses:.1%})")
        lines.append(f"  Medium (0.4-0.7): {medium_impact} ({medium_impact/total_analyses:.1%})")
        lines.append(f"  Low (<0.4):    {low_impact} ({low_impact/total_analyses:.1%})")
        lines.append("")
        lines.append("=" * 60)

        return '\n'.join(lines)
