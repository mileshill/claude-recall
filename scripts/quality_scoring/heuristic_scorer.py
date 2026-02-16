"""
Heuristic quality scoring (zero-cost fallback).

Provides rule-based quality scoring without API calls.
"""

from typing import List, Dict
import re


class HeuristicScorer:
    """
    Rule-based quality scorer (no API calls).

    Uses heuristics to estimate quality:
    - Query-result term overlap
    - Score distribution analysis
    - Result count appropriateness
    - Topic diversity
    """

    def score_quality(
        self,
        query: str,
        results: List[Dict],
        config: Dict
    ) -> Dict:
        """
        Score quality using heuristics.

        Args:
            query: Search query
            results: List of search results
            config: Search configuration

        Returns:
            Dictionary with quality scores
        """
        if not results:
            return self._empty_results_score(query, config)

        # Calculate component scores
        relevance = self._score_relevance(query, results)
        accuracy = self._score_accuracy(results)
        helpfulness = self._score_helpfulness(query, results)
        coverage = self._score_coverage(query, results, config)

        # Overall quality (weighted average)
        weights = {
            'relevance': 0.4,
            'accuracy': 0.25,
            'helpfulness': 0.2,
            'coverage': 0.15
        }

        overall_quality = (
            weights['relevance'] * relevance +
            weights['accuracy'] * accuracy +
            weights['helpfulness'] * helpfulness +
            weights['coverage'] * coverage
        )

        # Determine rating
        if overall_quality >= 0.75:
            rating = "excellent"
        elif overall_quality >= 0.6:
            rating = "good"
        elif overall_quality >= 0.4:
            rating = "acceptable"
        else:
            rating = "poor"

        # Analyze strengths and weaknesses
        strengths, weaknesses = self._analyze_results(
            query, results, relevance, accuracy, helpfulness, coverage
        )

        return {
            'overall_quality': overall_quality,
            'relevance': relevance,
            'accuracy': accuracy,
            'helpfulness': helpfulness,
            'coverage': coverage,
            'result_count_appropriate': self._is_count_appropriate(results, config),
            'top_result_quality': results[0].get('relevance_score', 0) if results else 0,
            'quality_rating': rating,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendation': self._get_recommendation(rating, weaknesses),
            'scoring_method': 'heuristic'
        }

    def _score_relevance(self, query: str, results: List[Dict]) -> float:
        """Score relevance based on term overlap and scores."""
        # Extract query terms
        query_terms = set(re.findall(r'\w+', query.lower()))

        if not query_terms:
            return 0.5

        relevance_scores = []

        for result in results:
            # Get result text
            summary = result.get('summary', '').lower()
            topics = ' '.join(result.get('topics', [])).lower()
            result_text = summary + ' ' + topics

            # Calculate term overlap
            result_terms = set(re.findall(r'\w+', result_text))
            overlap = len(query_terms & result_terms)
            overlap_score = overlap / len(query_terms)

            # Use relevance score if available
            relevance_score = result.get('relevance_score', overlap_score)

            # Combine
            combined_score = (overlap_score + relevance_score) / 2
            relevance_scores.append(combined_score)

        # Average across results (weighted towards top results)
        if relevance_scores:
            weights = [1.0 / (i + 1) for i in range(len(relevance_scores))]
            weight_sum = sum(weights)
            weighted_avg = sum(s * w for s, w in zip(relevance_scores, weights)) / weight_sum
            return min(weighted_avg, 1.0)

        return 0.0

    def _score_accuracy(self, results: List[Dict]) -> float:
        """Score accuracy based on score consistency."""
        if not results:
            return 0.0

        # Check score distribution
        scores = [r.get('relevance_score', 0) for r in results]

        # High scores are good
        avg_score = sum(scores) / len(scores)

        # Low variance is good (consistent quality)
        variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        consistency_score = 1.0 - min(variance, 1.0)

        # Combine
        accuracy = (avg_score + consistency_score) / 2

        return min(accuracy, 1.0)

    def _score_helpfulness(self, query: str, results: List[Dict]) -> float:
        """Score helpfulness based on content richness."""
        if not results:
            return 0.0

        helpfulness_scores = []

        for result in results:
            score = 0.0

            # Has detailed summary
            summary = result.get('summary', '')
            if len(summary) > 50:
                score += 0.3

            # Has topics
            topics = result.get('topics', [])
            if len(topics) >= 2:
                score += 0.3

            # Has modified files (actionable)
            files = result.get('files_modified', [])
            if files:
                score += 0.4

            helpfulness_scores.append(score)

        # Average
        avg_helpfulness = sum(helpfulness_scores) / len(helpfulness_scores)

        return min(avg_helpfulness, 1.0)

    def _score_coverage(
        self,
        query: str,
        results: List[Dict],
        config: Dict
    ) -> float:
        """Score coverage based on result diversity and count."""
        if not results:
            return 0.0

        # Check result count
        requested = config.get('limit', 5)
        found = len(results)

        count_score = min(found / requested, 1.0)

        # Check topic diversity
        all_topics = set()
        for result in results:
            all_topics.update(t.lower() for t in result.get('topics', []))

        diversity_score = min(len(all_topics) / max(found, 1), 1.0)

        # Combine
        coverage = (count_score + diversity_score) / 2

        return min(coverage, 1.0)

    def _is_count_appropriate(self, results: List[Dict], config: Dict) -> bool:
        """Check if result count is appropriate."""
        requested = config.get('limit', 5)
        found = len(results)

        # Appropriate if we got at least 60% of requested
        return found >= requested * 0.6

    def _analyze_results(
        self,
        query: str,
        results: List[Dict],
        relevance: float,
        accuracy: float,
        helpfulness: float,
        coverage: float
    ) -> tuple:
        """Analyze strengths and weaknesses."""
        strengths = []
        weaknesses = []

        # Relevance
        if relevance >= 0.7:
            strengths.append("High relevance scores")
        elif relevance < 0.4:
            weaknesses.append("Low relevance scores")

        # Accuracy
        if accuracy >= 0.7:
            strengths.append("Consistent quality across results")
        elif accuracy < 0.4:
            weaknesses.append("Inconsistent result quality")

        # Helpfulness
        if helpfulness >= 0.6:
            strengths.append("Results contain actionable information")
        elif helpfulness < 0.4:
            weaknesses.append("Limited actionable information")

        # Coverage
        if coverage >= 0.7:
            strengths.append("Good coverage and diversity")
        elif coverage < 0.4:
            weaknesses.append("Limited coverage or diversity")

        # Top result quality
        if results:
            top_score = results[0].get('relevance_score', 0)
            if top_score >= 0.8:
                strengths.append("Excellent top result")
            elif top_score < 0.5:
                weaknesses.append("Weak top result")

        return strengths, weaknesses

    def _get_recommendation(self, rating: str, weaknesses: List[str]) -> str:
        """Generate recommendation based on rating and weaknesses."""
        if rating == "excellent":
            return "Results are highly relevant and useful"

        if rating == "good":
            return "Results are generally good with minor issues"

        if rating == "acceptable":
            if "Low relevance" in ' '.join(weaknesses):
                return "Consider refining the query for better relevance"
            elif "Limited coverage" in ' '.join(weaknesses):
                return "Consider broadening the search or adjusting filters"
            else:
                return "Results are acceptable but could be improved"

        # Poor rating
        if not weaknesses:
            return "Results are poor quality - query may be too broad or specific"

        issue = weaknesses[0]
        if "relevance" in issue.lower():
            return "Poor relevance - try rephrasing the query"
        elif "coverage" in issue.lower():
            return "Limited results - try broader terms or fewer filters"
        else:
            return "Results need improvement - consider refining search strategy"

    def _empty_results_score(self, query: str, config: Dict) -> Dict:
        """Score for empty results."""
        return {
            'overall_quality': 0.0,
            'relevance': 0.0,
            'accuracy': 0.0,
            'helpfulness': 0.0,
            'coverage': 0.0,
            'result_count_appropriate': False,
            'top_result_quality': 0.0,
            'quality_rating': 'poor',
            'strengths': [],
            'weaknesses': ['No results found'],
            'recommendation': 'No results - try broader terms or different keywords',
            'scoring_method': 'heuristic'
        }
