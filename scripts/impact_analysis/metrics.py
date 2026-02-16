"""
Efficiency and impact metrics for recall analysis.

Calculates efficiency gains, repetition avoidance, and user behavior patterns.
"""

from typing import List, Dict, Optional
from datetime import datetime
import re


class EfficiencyMetrics:
    """
    Calculates efficiency metrics for recalled context.

    Measures:
    - Time/effort saved by recalling vs. re-explaining
    - Repetition avoidance (not asking same questions)
    - Context switching reduction
    - User engagement and productivity
    """

    def calculate_efficiency_gain(
        self,
        session_data: Dict,
        recalled_sessions: List[Dict]
    ) -> Dict:
        """
        Calculate efficiency gains from recalled context.

        Args:
            session_data: Current session data
            recalled_sessions: List of recalled sessions

        Returns:
            Dictionary with efficiency metrics
        """
        # Estimate time saved
        time_saved = self._estimate_time_saved(session_data, recalled_sessions)

        # Check for repetition avoidance
        repetition_avoided = self._check_repetition_avoidance(
            session_data,
            recalled_sessions
        )

        # Calculate context switching
        context_switching = self._calculate_context_switching(
            session_data,
            recalled_sessions
        )

        # Overall efficiency score
        efficiency_score = self._calculate_efficiency_score(
            time_saved,
            repetition_avoided,
            context_switching
        )

        return {
            'efficiency_score': efficiency_score,
            'estimated_time_saved_minutes': time_saved,
            'repetition_avoided': repetition_avoided,
            'context_switching_score': context_switching,
            'overall_impact': self._categorize_impact(efficiency_score)
        }

    def _estimate_time_saved(
        self,
        session_data: Dict,
        recalled_sessions: List[Dict]
    ) -> float:
        """
        Estimate time saved by having recalled context.

        Args:
            session_data: Current session data
            recalled_sessions: Recalled sessions

        Returns:
            Estimated minutes saved
        """
        # Base time saved per recalled session (heuristic)
        base_time_per_session = 5.0  # minutes

        # Adjust based on session relevance
        time_saved = 0.0

        for session in recalled_sessions:
            # Get relevance score if available
            relevance = session.get('relevance_score', 0.5)

            # High relevance = more time saved
            if relevance > 0.7:
                time_saved += base_time_per_session * 1.5
            elif relevance > 0.4:
                time_saved += base_time_per_session
            else:
                time_saved += base_time_per_session * 0.5

        return time_saved

    def _check_repetition_avoidance(
        self,
        session_data: Dict,
        recalled_sessions: List[Dict]
    ) -> Dict:
        """
        Check if recall helped avoid repeating questions/explanations.

        Args:
            session_data: Current session
            recalled_sessions: Recalled sessions

        Returns:
            Dictionary with repetition metrics
        """
        # Look for question patterns in current session
        current_text = session_data.get('summary', '') + ' ' + \
                      ' '.join(session_data.get('topics', []))

        # Question indicators
        question_patterns = [
            r'\bhow (?:do|does|can|to)\b',
            r'\bwhat (?:is|are|does|about)\b',
            r'\bwhy (?:is|does|did)\b',
            r'\bwhere (?:is|are|can)\b',
            r'\bwhen (?:should|to|can)\b',
            r'\bcan (?:you|we|i)\b',
            r'\bshould (?:i|we)\b'
        ]

        current_questions = []
        for pattern in question_patterns:
            matches = re.findall(pattern, current_text.lower())
            current_questions.extend(matches)

        # Check if similar questions were answered in recalled sessions
        answered_questions = 0
        for session in recalled_sessions:
            session_text = session.get('summary', '').lower()

            for question in current_questions:
                # Simple check - if question topic appears in recalled session
                if question in session_text:
                    answered_questions += 1

        # Calculate avoidance rate
        total_questions = len(current_questions)
        avoidance_rate = answered_questions / max(total_questions, 1)

        return {
            'total_potential_questions': total_questions,
            'questions_avoided': answered_questions,
            'avoidance_rate': avoidance_rate,
            'repetition_score': min(avoidance_rate, 1.0)
        }

    def _calculate_context_switching(
        self,
        session_data: Dict,
        recalled_sessions: List[Dict]
    ) -> float:
        """
        Calculate context switching reduction.

        Args:
            session_data: Current session
            recalled_sessions: Recalled sessions

        Returns:
            Context switching score (0-1, higher is better)
        """
        # Check topic continuity
        current_topics = set(t.lower() for t in session_data.get('topics', []))

        if not current_topics:
            return 0.5

        # Check overlap with recalled sessions
        total_overlap = 0
        for session in recalled_sessions:
            recalled_topics = set(t.lower() for t in session.get('topics', []))

            if recalled_topics:
                overlap = len(current_topics & recalled_topics)
                total_overlap += overlap / len(current_topics)

        # Average overlap across recalled sessions
        avg_overlap = total_overlap / max(len(recalled_sessions), 1)

        # High overlap = low context switching = high score
        return min(avg_overlap, 1.0)

    def _calculate_efficiency_score(
        self,
        time_saved: float,
        repetition_avoided: Dict,
        context_switching: float
    ) -> float:
        """
        Calculate overall efficiency score.

        Args:
            time_saved: Minutes saved
            repetition_avoided: Repetition metrics
            context_switching: Context switching score

        Returns:
            Efficiency score (0-1)
        """
        # Normalize time saved (saturate at 20 minutes)
        time_score = min(time_saved / 20.0, 1.0)

        # Repetition score
        repetition_score = repetition_avoided.get('repetition_score', 0.0)

        # Weighted average
        weights = {
            'time': 0.4,
            'repetition': 0.3,
            'context': 0.3
        }

        efficiency_score = (
            weights['time'] * time_score +
            weights['repetition'] * repetition_score +
            weights['context'] * context_switching
        )

        return efficiency_score

    def _categorize_impact(self, efficiency_score: float) -> str:
        """Categorize impact level."""
        if efficiency_score >= 0.7:
            return "HIGH"
        elif efficiency_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def calculate_productivity_metrics(
        self,
        session_sequence: List[Dict]
    ) -> Dict:
        """
        Calculate productivity metrics across session sequence.

        Args:
            session_sequence: Ordered list of sessions

        Returns:
            Dictionary with productivity metrics
        """
        if not session_sequence:
            return {
                'avg_session_duration': 0.0,
                'files_modified_rate': 0.0,
                'completion_rate': 0.0,
                'productivity_trend': 'stable'
            }

        # Calculate session durations (if available)
        durations = []
        for session in session_sequence:
            # Heuristic: estimate from content length
            summary_length = len(session.get('summary', ''))
            # Assume 5 words per minute, 60 chars per word estimate
            estimated_minutes = (summary_length / 60) / 5
            durations.append(estimated_minutes)

        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Files modified rate
        total_files = sum(len(s.get('files_modified', [])) for s in session_sequence)
        files_rate = total_files / len(session_sequence)

        # Completion indicators (check for completion keywords)
        completion_keywords = ['complete', 'done', 'finish', 'implement', 'fix', 'add']
        completed = 0
        for session in session_sequence:
            summary = session.get('summary', '').lower()
            if any(kw in summary for kw in completion_keywords):
                completed += 1

        completion_rate = completed / len(session_sequence)

        # Trend analysis (compare first half to second half)
        mid = len(session_sequence) // 2
        if mid > 0:
            first_half_files = sum(len(s.get('files_modified', [])) for s in session_sequence[:mid]) / mid
            second_half_files = sum(len(s.get('files_modified', [])) for s in session_sequence[mid:]) / (len(session_sequence) - mid)

            if second_half_files > first_half_files * 1.2:
                trend = 'increasing'
            elif second_half_files < first_half_files * 0.8:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'avg_session_duration_minutes': avg_duration,
            'files_modified_per_session': files_rate,
            'completion_rate': completion_rate,
            'productivity_trend': trend,
            'total_sessions': len(session_sequence)
        }

    def calculate_learning_curve(
        self,
        session_sequence: List[Dict]
    ) -> Dict:
        """
        Calculate learning curve metrics.

        Args:
            session_sequence: Ordered list of sessions

        Returns:
            Dictionary with learning metrics
        """
        if len(session_sequence) < 2:
            return {
                'learning_rate': 0.0,
                'mastery_indicators': [],
                'knowledge_retention': 0.0
            }

        # Track unique topics over time
        topics_over_time = []
        all_topics = set()

        for session in session_sequence:
            topics = set(t.lower() for t in session.get('topics', []))
            topics_over_time.append(topics)
            all_topics.update(topics)

        # New topics per session (learning rate)
        new_topics_counts = []
        seen_topics = set()
        for topics in topics_over_time:
            new_topics = topics - seen_topics
            new_topics_counts.append(len(new_topics))
            seen_topics.update(topics)

        # Learning rate (new topics per session)
        learning_rate = sum(new_topics_counts) / len(new_topics_counts) if new_topics_counts else 0

        # Mastery indicators (repeated topics = mastery)
        topic_frequencies = {}
        for topics in topics_over_time:
            for topic in topics:
                topic_frequencies[topic] = topic_frequencies.get(topic, 0) + 1

        mastery_indicators = [
            topic for topic, freq in topic_frequencies.items()
            if freq >= 3  # Appears in 3+ sessions
        ]

        # Knowledge retention (topics that persist)
        if len(topics_over_time) >= 2:
            early_topics = topics_over_time[0]
            recent_topics = topics_over_time[-1]
            retained = len(early_topics & recent_topics)
            retention_rate = retained / max(len(early_topics), 1)
        else:
            retention_rate = 0.0

        return {
            'learning_rate': learning_rate,
            'mastery_indicators': mastery_indicators,
            'knowledge_retention': retention_rate,
            'total_unique_topics': len(all_topics)
        }
