"""
Metric calculation utilities.

Provides common metric calculations used across analytics:
- Score statistics (mean, median, percentiles)
- Score distributions (high/medium/low buckets)
- Text similarity calculations
- Common term extraction
"""

import re
import numpy as np
from typing import List, Dict
from collections import Counter


class MetricsCalculator:
    """Shared metric calculation utilities."""

    @staticmethod
    def score_stats(scores: List[float]) -> Dict[str, float]:
        """
        Calculate score statistics.

        Args:
            scores: List of scores (0-1 range)

        Returns:
            Dictionary with avg, min, max, median, std, percentiles, count
        """
        if not scores:
            return {
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "median": 0.0,
                "std": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "count": 0
            }

        scores_array = np.array(scores)

        return {
            "avg": float(np.mean(scores_array)),
            "min": float(np.min(scores_array)),
            "max": float(np.max(scores_array)),
            "median": float(np.median(scores_array)),
            "std": float(np.std(scores_array)),
            "p50": float(np.percentile(scores_array, 50)),
            "p95": float(np.percentile(scores_array, 95)),
            "p99": float(np.percentile(scores_array, 99)),
            "count": len(scores)
        }

    @staticmethod
    def score_distribution(scores: List[float]) -> Dict[str, any]:
        """
        Categorize scores into high/medium/low buckets.

        Args:
            scores: List of scores (0-1 range)

        Returns:
            Dictionary with counts and percentages for each bucket
        """
        if not scores:
            return {
                "high": 0,
                "medium": 0,
                "low": 0,
                "high_pct": 0.0,
                "medium_pct": 0.0,
                "low_pct": 0.0
            }

        high = sum(1 for s in scores if s > 0.7)
        medium = sum(1 for s in scores if 0.4 <= s <= 0.7)
        low = sum(1 for s in scores if s < 0.4)
        total = len(scores)

        return {
            "high": high,
            "medium": medium,
            "low": low,
            "high_pct": high / total if total > 0 else 0.0,
            "medium_pct": medium / total if total > 0 else 0.0,
            "low_pct": low / total if total > 0 else 0.0
        }

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate text similarity using Jaccard index.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score 0-1 (1 = identical)
        """
        # Handle empty texts
        if not text1 and not text2:
            return 1.0  # Both empty = identical
        if not text1 or not text2:
            return 0.0  # One empty = no similarity

        # Extract words
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total if total > 0 else 0.0

    @staticmethod
    def extract_common_terms(
        text1: str,
        text2: str,
        top_n: int = 10,
        min_length: int = 3
    ) -> List[str]:
        """
        Extract common important terms between two texts.

        Args:
            text1: First text
            text2: Second text
            top_n: Return top N terms
            min_length: Minimum term length

        Returns:
            List of common terms, sorted by frequency
        """
        # Extract words with frequency
        words1 = Counter(re.findall(r'\w+', text1.lower()))
        words2 = Counter(re.findall(r'\w+', text2.lower()))

        # Find intersection
        common = set(words1.keys()) & set(words2.keys())

        # Filter by length
        common = {word for word in common if len(word) >= min_length}

        # Weight by frequency (geometric mean)
        weighted = {
            word: (words1[word] * words2[word]) ** 0.5
            for word in common
        }

        # Sort by weight
        sorted_terms = sorted(
            weighted.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [word for word, weight in sorted_terms[:top_n]]

    @staticmethod
    def latency_stats(latencies_ms: List[float]) -> Dict[str, float]:
        """
        Calculate latency statistics.

        Args:
            latencies_ms: List of latency measurements in milliseconds

        Returns:
            Dictionary with latency statistics
        """
        if not latencies_ms:
            return {
                "avg_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "count": 0
            }

        latencies_array = np.array(latencies_ms)

        return {
            "avg_ms": float(np.mean(latencies_array)),
            "min_ms": float(np.min(latencies_array)),
            "max_ms": float(np.max(latencies_array)),
            "p50_ms": float(np.percentile(latencies_array, 50)),
            "p95_ms": float(np.percentile(latencies_array, 95)),
            "p99_ms": float(np.percentile(latencies_array, 99)),
            "count": len(latencies_ms)
        }

    @staticmethod
    def count_by_field(items: List[dict], field: str) -> Dict[str, int]:
        """
        Count occurrences by field value.

        Args:
            items: List of dictionaries
            field: Field to count by (supports dot notation)

        Returns:
            Dictionary mapping field values to counts
        """
        counts = Counter()

        for item in items:
            # Support dot notation (e.g., "search_config.mode")
            value = item
            for key in field.split('.'):
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                    break

            if value is not None:
                counts[str(value)] += 1

        return dict(counts)

    @staticmethod
    def average_by_field(items: List[dict], field: str) -> float:
        """
        Calculate average of numeric field.

        Args:
            items: List of dictionaries
            field: Field to average (supports dot notation)

        Returns:
            Average value
        """
        values = []

        for item in items:
            # Support dot notation
            value = item
            for key in field.split('.'):
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    value = None
                    break

            if value is not None and isinstance(value, (int, float)):
                values.append(float(value))

        return np.mean(values) if values else 0.0
