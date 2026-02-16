"""
Context usage detection for impact analysis.

Detects explicit citations, implicit usage, and reused topics from recalled sessions.
"""

import re
from typing import List, Dict, Set, Tuple
from collections import Counter


class ContextUsageDetector:
    """
    Detects how recalled context is used in conversations.

    Detects:
    - Explicit citations (direct references to recalled content)
    - Implicit usage (concepts/terms from recalled sessions)
    - Reused topics and technical terms
    """

    def __init__(self):
        """Initialize detector with citation patterns."""
        # Patterns for explicit citations
        self.citation_patterns = [
            r'(?:from|in|according to|as (?:mentioned|discussed|shown) in) (?:the )?(?:previous |last |earlier )?(?:session|conversation|discussion)',
            r'(?:previously|earlier) (?:we|you|i) (?:discussed|mentioned|talked about|worked on)',
            r'(?:like|as) (?:last time|before)',
            r'continuing (?:from|the work)',
            r'building on (?:the |our )?(?:previous|earlier)',
            r'(?:recall|remember) (?:that |when )?(?:we|you|i)',
            r'(?:as )?(?:you|we) (?:said|mentioned|noted|discussed)',
        ]

        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.citation_patterns]

    def detect_explicit_citations(self, transcript: str) -> List[Dict]:
        """
        Detect explicit references to recalled context.

        Args:
            transcript: Current conversation transcript

        Returns:
            List of citation detections with locations
        """
        citations = []

        for pattern in self.compiled_patterns:
            for match in pattern.finditer(transcript):
                citations.append({
                    'type': 'explicit_citation',
                    'text': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'pattern': pattern.pattern
                })

        return citations

    def detect_implicit_usage(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict]
    ) -> Dict:
        """
        Detect implicit usage of recalled context via term overlap.

        Args:
            current_transcript: Current conversation transcript
            recalled_sessions: List of recalled session data

        Returns:
            Dictionary with implicit usage metrics
        """
        # Extract terms from current transcript
        current_terms = self._extract_technical_terms(current_transcript)
        current_keywords = self._extract_keywords(current_transcript)

        # Extract terms from recalled sessions
        recalled_terms = set()
        recalled_keywords = set()

        for session in recalled_sessions:
            # From session metadata
            if 'topics' in session:
                recalled_keywords.update(t.lower() for t in session['topics'])

            # From session summary
            if 'summary' in session:
                recalled_terms.update(self._extract_technical_terms(session['summary']))
                recalled_keywords.update(self._extract_keywords(session['summary']))

        # Calculate overlap
        term_overlap = current_terms & recalled_terms
        keyword_overlap = current_keywords & recalled_keywords

        # Calculate similarity scores
        term_similarity = len(term_overlap) / max(len(current_terms), 1)
        keyword_similarity = len(keyword_overlap) / max(len(current_keywords), 1)

        return {
            'term_overlap': list(term_overlap),
            'term_overlap_count': len(term_overlap),
            'term_similarity': term_similarity,
            'keyword_overlap': list(keyword_overlap),
            'keyword_overlap_count': len(keyword_overlap),
            'keyword_similarity': keyword_similarity,
            'total_similarity': (term_similarity + keyword_similarity) / 2
        }

    def detect_reused_topics(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict]
    ) -> List[Dict]:
        """
        Detect topics from recalled sessions being reused.

        Args:
            current_transcript: Current conversation transcript
            recalled_sessions: List of recalled session data

        Returns:
            List of reused topics with frequency
        """
        reused_topics = []
        current_lower = current_transcript.lower()

        # Check each recalled session's topics
        for session in recalled_sessions:
            if 'topics' not in session:
                continue

            session_id = session.get('id', 'unknown')

            for topic in session['topics']:
                # Check if topic appears in current transcript
                topic_lower = topic.lower()
                if topic_lower in current_lower:
                    # Count occurrences
                    count = current_lower.count(topic_lower)
                    reused_topics.append({
                        'topic': topic,
                        'session_id': session_id,
                        'occurrences': count
                    })

        return reused_topics

    def detect_file_references(
        self,
        current_transcript: str,
        recalled_sessions: List[Dict]
    ) -> List[Dict]:
        """
        Detect references to files mentioned in recalled sessions.

        Args:
            current_transcript: Current conversation transcript
            recalled_sessions: List of recalled session data

        Returns:
            List of file references
        """
        file_refs = []

        for session in recalled_sessions:
            if 'files_modified' not in session:
                continue

            session_id = session.get('id', 'unknown')

            for file_path in session['files_modified']:
                # Extract filename
                filename = file_path.split('/')[-1]

                # Check if file is mentioned
                if filename in current_transcript or file_path in current_transcript:
                    file_refs.append({
                        'file': file_path,
                        'filename': filename,
                        'session_id': session_id
                    })

        return file_refs

    def _extract_technical_terms(self, text: str) -> Set[str]:
        """Extract technical terms from text."""
        terms = set()

        # Acronyms
        acronyms = re.findall(r'\b[A-Z]{2,5}\b', text)
        terms.update(a.lower() for a in acronyms)

        # camelCase/PascalCase
        camel = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b|\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', text)
        terms.update(t.lower() for t in camel)

        # snake_case
        snake = re.findall(r'\b[a-z]+_[a-z_]+\b', text)
        terms.update(snake)

        # kebab-case
        kebab = re.findall(r'\b[a-z]+-[a-z-]+\b', text)
        terms.update(kebab)

        # File extensions
        extensions = re.findall(r'\.\w{2,4}\b', text)
        terms.update(ext.lower() for ext in extensions)

        return terms

    def _extract_keywords(self, text: str, min_length: int = 4) -> Set[str]:
        """Extract important keywords from text."""
        # Simple keyword extraction (can be enhanced)
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Filter stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'this', 'that', 'these', 'those'
        }

        keywords = {w for w in words if len(w) >= min_length and w not in stop_words}

        return keywords

    def calculate_usage_score(
        self,
        explicit_citations: List[Dict],
        implicit_usage: Dict,
        reused_topics: List[Dict],
        file_references: List[Dict]
    ) -> Dict:
        """
        Calculate overall context usage score.

        Args:
            explicit_citations: List of explicit citations
            implicit_usage: Implicit usage metrics
            reused_topics: List of reused topics
            file_references: List of file references

        Returns:
            Dictionary with usage scores
        """
        # Count indicators
        citation_count = len(explicit_citations)
        topic_count = len(reused_topics)
        file_count = len(file_references)

        # Weights for scoring
        weights = {
            'explicit': 0.4,
            'implicit': 0.3,
            'topics': 0.2,
            'files': 0.1
        }

        # Component scores (0-1)
        explicit_score = min(citation_count / 3, 1.0)  # Saturate at 3 citations
        implicit_score = implicit_usage.get('total_similarity', 0.0)
        topic_score = min(topic_count / 5, 1.0)  # Saturate at 5 topics
        file_score = min(file_count / 3, 1.0)  # Saturate at 3 files

        # Weighted total
        total_score = (
            weights['explicit'] * explicit_score +
            weights['implicit'] * implicit_score +
            weights['topics'] * topic_score +
            weights['files'] * file_score
        )

        return {
            'total_score': total_score,
            'component_scores': {
                'explicit': explicit_score,
                'implicit': implicit_score,
                'topics': topic_score,
                'files': file_score
            },
            'raw_counts': {
                'explicit_citations': citation_count,
                'reused_topics': topic_count,
                'file_references': file_count,
                'term_overlap': implicit_usage.get('term_overlap_count', 0),
                'keyword_overlap': implicit_usage.get('keyword_overlap_count', 0)
            }
        }
