"""
Continuity and consistency scoring for impact analysis.

Scores how well recalled context maintains continuity and consistency.
"""

import re
from typing import List, Dict, Set
from collections import Counter
from datetime import datetime


class ContinuityScorer:
    """
    Scores continuity between recalled sessions and current conversation.

    Measures:
    - Temporal continuity (time gap handling)
    - Terminology alignment (consistent usage)
    - Approach consistency (similar patterns/methods)
    """

    def score_continuity(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict],
        current_session_time: datetime = None
    ) -> Dict:
        """
        Calculate overall continuity score.

        Args:
            current_transcript: Current conversation transcript
            recalled_sessions: List of recalled session data
            current_session_time: Current session timestamp

        Returns:
            Dictionary with continuity scores
        """
        if not recalled_sessions:
            return {
                'total_score': 0.0,
                'temporal_score': 0.0,
                'terminology_score': 0.0,
                'approach_score': 0.0
            }

        # Calculate component scores
        temporal_score = self._score_temporal_continuity(
            recalled_sessions,
            current_session_time
        )

        terminology_score = self._score_terminology_alignment(
            current_transcript,
            recalled_sessions
        )

        approach_score = self._score_approach_consistency(
            current_transcript,
            recalled_sessions
        )

        # Weighted average
        weights = {
            'temporal': 0.2,
            'terminology': 0.4,
            'approach': 0.4
        }

        total_score = (
            weights['temporal'] * temporal_score +
            weights['terminology'] * terminology_score +
            weights['approach'] * approach_score
        )

        return {
            'total_score': total_score,
            'temporal_score': temporal_score,
            'terminology_score': terminology_score,
            'approach_score': approach_score
        }

    def _score_temporal_continuity(
        self,
        recalled_sessions: List[Dict],
        current_time: datetime = None
    ) -> float:
        """
        Score temporal continuity (how recent/relevant sessions are).

        Args:
            recalled_sessions: List of recalled sessions
            current_time: Current session time

        Returns:
            Temporal continuity score (0-1)
        """
        if not current_time:
            current_time = datetime.now()

        scores = []

        for session in recalled_sessions:
            # Get session timestamp
            timestamp_str = session.get('captured') or session.get('timestamp')
            if not timestamp_str:
                continue

            try:
                # Parse timestamp
                if 'T' in timestamp_str:
                    session_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    session_time = datetime.strptime(timestamp_str, '%Y-%m-%d')

                # Calculate time gap in days
                time_gap = (current_time - session_time).total_seconds() / 86400

                # Score based on recency (exponential decay)
                # Half-life of 30 days
                temporal_score = 2 ** (-time_gap / 30)
                scores.append(temporal_score)

            except Exception:
                # If parsing fails, use neutral score
                scores.append(0.5)

        return sum(scores) / len(scores) if scores else 0.5

    def _score_terminology_alignment(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict]
    ) -> float:
        """
        Score terminology alignment (consistent term usage).

        Args:
            current_transcript: Current conversation
            recalled_sessions: Recalled sessions

        Returns:
            Terminology alignment score (0-1)
        """
        # Extract terminology from current transcript
        current_terms = self._extract_terminology(current_transcript)

        # Extract terminology from recalled sessions
        recalled_terms = Counter()

        for session in recalled_sessions:
            if 'summary' in session:
                terms = self._extract_terminology(session['summary'])
                recalled_terms.update(terms)

            if 'topics' in session:
                recalled_terms.update(t.lower() for t in session['topics'])

        # Calculate overlap
        if not recalled_terms or not current_terms:
            return 0.0

        # Terms that appear in both
        common_terms = set(current_terms.keys()) & set(recalled_terms.keys())

        if not common_terms:
            return 0.0

        # Weighted by frequency
        current_total = sum(current_terms.values())
        common_frequency = sum(current_terms[t] for t in common_terms)

        alignment_score = common_frequency / current_total

        return min(alignment_score, 1.0)

    def _score_approach_consistency(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict]
    ) -> float:
        """
        Score approach consistency (similar patterns/methods).

        Args:
            current_transcript: Current conversation
            recalled_sessions: Recalled sessions

        Returns:
            Approach consistency score (0-1)
        """
        # Detect patterns in current transcript
        current_patterns = self._detect_approach_patterns(current_transcript)

        # Detect patterns in recalled sessions
        recalled_patterns = Counter()

        for session in recalled_sessions:
            if 'summary' in session:
                patterns = self._detect_approach_patterns(session['summary'])
                recalled_patterns.update(patterns)

        # Calculate overlap
        if not recalled_patterns or not current_patterns:
            return 0.0

        common_patterns = set(current_patterns.keys()) & set(recalled_patterns.keys())

        if not common_patterns:
            return 0.0

        # Ratio of common patterns
        consistency_score = len(common_patterns) / len(set(current_patterns.keys()))

        return min(consistency_score, 1.0)

    def _extract_terminology(self, text: str) -> Counter:
        """Extract and count terminology from text."""
        terms = Counter()

        # Technical terms
        acronyms = re.findall(r'\b[A-Z]{2,5}\b', text)
        terms.update(a.lower() for a in acronyms)

        # camelCase/PascalCase
        camel = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b|\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', text)
        terms.update(t.lower() for t in camel)

        # snake_case
        snake = re.findall(r'\b[a-z]+_[a-z_]+\b', text)
        terms.update(snake)

        # Important keywords (excluding common words)
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        stop_words = {
            'the', 'this', 'that', 'with', 'from', 'have', 'will', 'would',
            'could', 'should', 'been', 'were', 'their', 'there', 'where'
        }
        terms.update(w for w in words if w not in stop_words)

        return terms

    def _detect_approach_patterns(self, text: str) -> Counter:
        """Detect approach patterns in text."""
        patterns = Counter()

        text_lower = text.lower()

        # Development approaches
        approach_keywords = {
            'tdd': ['test', 'tdd', 'test-driven'],
            'agile': ['agile', 'sprint', 'scrum'],
            'refactor': ['refactor', 'restructure', 'clean up'],
            'debug': ['debug', 'fix', 'troubleshoot', 'investigate'],
            'implement': ['implement', 'add', 'create', 'build'],
            'optimize': ['optimize', 'improve', 'performance'],
            'document': ['document', 'documentation', 'readme'],
            'review': ['review', 'audit', 'check'],
            'deploy': ['deploy', 'release', 'production'],
            'security': ['security', 'authentication', 'authorization']
        }

        for pattern, keywords in approach_keywords.items():
            if any(kw in text_lower for kw in keywords):
                patterns[pattern] += 1

        return patterns

    def score_terminology_evolution(
        self,
        session_sequence: List[Dict]
    ) -> Dict:
        """
        Score how terminology evolves across session sequence.

        Args:
            session_sequence: Ordered list of sessions

        Returns:
            Dictionary with evolution metrics
        """
        if len(session_sequence) < 2:
            return {
                'consistency_score': 1.0,
                'evolution_rate': 0.0,
                'stable_terms': [],
                'new_terms': []
            }

        # Track terms across sessions
        session_terms = []
        for session in session_sequence:
            terms = set()
            if 'summary' in session:
                terms.update(self._extract_terminology(session['summary']).keys())
            if 'topics' in session:
                terms.update(t.lower() for t in session['topics'])
            session_terms.append(terms)

        # Calculate stability
        stable_terms = set.intersection(*session_terms) if session_terms else set()
        all_terms = set.union(*session_terms) if session_terms else set()
        new_terms = session_terms[-1] - session_terms[0] if len(session_terms) >= 2 else set()

        consistency_score = len(stable_terms) / max(len(all_terms), 1)
        evolution_rate = len(new_terms) / max(len(session_terms[0]), 1) if session_terms else 0

        return {
            'consistency_score': consistency_score,
            'evolution_rate': evolution_rate,
            'stable_terms': list(stable_terms),
            'new_terms': list(new_terms),
            'total_unique_terms': len(all_terms)
        }
