"""
Prompt templates for LLM-based quality evaluation.

Provides structured prompts with JSON schema for consistent evaluation.
"""

from typing import Dict


class QualityEvaluationPrompts:
    """
    Prompt templates for quality scoring.

    Provides prompts for evaluating:
    - Relevance: How well results match the query
    - Accuracy: Correctness of retrieved information
    - Helpfulness: Usefulness of results
    - Coverage: Completeness of results
    """

    @staticmethod
    def get_relevance_prompt(query: str, results: list) -> str:
        """
        Generate prompt for relevance evaluation.

        Args:
            query: Search query
            results: List of search results

        Returns:
            Formatted prompt string
        """
        results_text = "\n\n".join([
            f"Result {i+1}:\n"
            f"- Session ID: {r.get('id', 'unknown')}\n"
            f"- Summary: {r.get('summary', 'N/A')}\n"
            f"- Topics: {', '.join(r.get('topics', []))}\n"
            f"- Relevance Score: {r.get('relevance_score', 0):.2f}"
            for i, r in enumerate(results[:5])  # Limit to top 5
        ])

        return f"""Evaluate the relevance of these search results for the given query.

Query: "{query}"

Results:
{results_text}

Evaluate each result's relevance to the query and provide an overall assessment.

Respond with JSON in this exact format:
{{
  "overall_relevance": <float 0-1>,
  "high_relevance_count": <int>,
  "result_scores": [<float 0-1>, ...],
  "issues": [<list of issues found>],
  "recommendation": "<brief recommendation>"
}}

Focus on:
1. How well each result matches the query intent
2. Whether results contain information that answers the query
3. Topical alignment between query and results
4. Whether results are likely to be helpful"""

    @staticmethod
    def get_accuracy_prompt(query: str, results: list, context: str = None) -> str:
        """
        Generate prompt for accuracy evaluation.

        Args:
            query: Search query
            results: List of search results
            context: Optional context for validation

        Returns:
            Formatted prompt string
        """
        results_text = "\n\n".join([
            f"Result {i+1}:\n"
            f"- Session: {r.get('id', 'unknown')}\n"
            f"- Summary: {r.get('summary', 'N/A')}\n"
            f"- Topics: {', '.join(r.get('topics', []))}"
            for i, r in enumerate(results[:5])
        ])

        context_section = ""
        if context:
            context_section = f"\n\nContext:\n{context[:500]}\n"

        return f"""Evaluate the accuracy and appropriateness of these search results.

Query: "{query}"
{context_section}
Results:
{results_text}

Assess whether the retrieved results are accurate and appropriate.

Respond with JSON in this exact format:
{{
  "overall_accuracy": <float 0-1>,
  "appropriate_results": <int>,
  "mismatched_results": <int>,
  "accuracy_issues": [<list of issues>],
  "confidence": <float 0-1>
}}

Consider:
1. Are the results actually related to the query topic?
2. Are there any obvious mismatches or errors?
3. Do the topics align with what was queried?
4. Would these results be helpful in the given context?"""

    @staticmethod
    def get_helpfulness_prompt(query: str, results: list) -> str:
        """
        Generate prompt for helpfulness evaluation.

        Args:
            query: Search query
            results: List of search results

        Returns:
            Formatted prompt string
        """
        results_text = "\n\n".join([
            f"Result {i+1}:\n"
            f"- Summary: {r.get('summary', 'N/A')}\n"
            f"- Topics: {', '.join(r.get('topics', []))}\n"
            f"- Files: {', '.join(r.get('files_modified', []))}"
            for i, r in enumerate(results[:5])
        ])

        return f"""Evaluate how helpful these search results would be for the query.

Query: "{query}"

Results:
{results_text}

Assess the practical helpfulness of these results.

Respond with JSON in this exact format:
{{
  "overall_helpfulness": <float 0-1>,
  "actionable_results": <int>,
  "provides_context": <bool>,
  "provides_examples": <bool>,
  "helpfulness_rating": "<high|medium|low>",
  "reasoning": "<brief explanation>"
}}

Consider:
1. Do results provide actionable information?
2. Do they give enough context to be useful?
3. Would someone be able to act on this information?
4. Are there concrete examples or references?"""

    @staticmethod
    def get_comprehensive_prompt(query: str, results: list, config: dict) -> str:
        """
        Generate comprehensive quality evaluation prompt.

        Args:
            query: Search query
            results: List of search results
            config: Search configuration

        Returns:
            Formatted prompt string
        """
        results_text = "\n\n".join([
            f"Result {i+1}:\n"
            f"- ID: {r.get('id', 'unknown')}\n"
            f"- Summary: {r.get('summary', 'N/A')}\n"
            f"- Topics: {', '.join(r.get('topics', []))}\n"
            f"- BM25: {r.get('bm25_score', 0):.2f} | "
            f"Semantic: {r.get('semantic_score', 'N/A')} | "
            f"Final: {r.get('relevance_score', 0):.2f}"
            for i, r in enumerate(results[:5])
        ])

        search_mode = config.get('mode', 'unknown')
        limit = config.get('limit', 'N/A')

        return f"""Evaluate the quality of these search results across multiple dimensions.

Query: "{query}"
Search Mode: {search_mode}
Results Requested: {limit}
Results Found: {len(results)}

Results:
{results_text}

Provide a comprehensive quality assessment.

Respond with JSON in this exact format:
{{
  "overall_quality": <float 0-1>,
  "relevance": <float 0-1>,
  "accuracy": <float 0-1>,
  "helpfulness": <float 0-1>,
  "coverage": <float 0-1>,
  "result_count_appropriate": <bool>,
  "top_result_quality": <float 0-1>,
  "quality_rating": "<excellent|good|acceptable|poor>",
  "strengths": [<list of strengths>],
  "weaknesses": [<list of weaknesses>],
  "recommendation": "<brief recommendation>"
}}

Evaluate:
1. **Relevance**: How well do results match the query?
2. **Accuracy**: Are results appropriate and correct?
3. **Helpfulness**: Would these results help someone?
4. **Coverage**: Is the set of results complete enough?
5. **Quality**: Overall quality and usefulness

Be critical but fair. Consider both the query and the results."""

    @staticmethod
    def get_json_schema() -> Dict:
        """
        Get JSON schema for comprehensive evaluation.

        Returns:
            JSON schema dictionary
        """
        return {
            "type": "object",
            "required": [
                "overall_quality",
                "relevance",
                "accuracy",
                "helpfulness",
                "coverage",
                "quality_rating"
            ],
            "properties": {
                "overall_quality": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Overall quality score"
                },
                "relevance": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "accuracy": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "helpfulness": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "coverage": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "result_count_appropriate": {
                    "type": "boolean"
                },
                "top_result_quality": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1
                },
                "quality_rating": {
                    "type": "string",
                    "enum": ["excellent", "good", "acceptable", "poor"]
                },
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "recommendation": {
                    "type": "string"
                }
            }
        }
