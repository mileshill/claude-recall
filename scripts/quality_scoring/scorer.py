"""
Main quality scorer orchestrator.

Coordinates LLM evaluation, cost tracking, sampling, and fallbacks.
"""

import sys
import random
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
import asyncio

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quality_scoring.cost_tracker import CostTracker
from quality_scoring.prompt_templates import QualityEvaluationPrompts
from quality_scoring.heuristic_scorer import HeuristicScorer
from quality_scoring.evaluator import LLMEvaluator
from metrics.jsonl_utils import JSONLWriter
from metrics.config import config


class QualityScorer:
    """
    Main quality scoring orchestrator.

    Features:
    - Sampling rate control
    - Budget enforcement
    - Async evaluation
    - Heuristic fallback
    - Cost tracking
    """

    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize quality scorer.

        Args:
            log_path: Path to quality scores log
        """
        # Load configuration
        self.enabled = config.get('quality_scoring.enabled', False)
        self.mode = config.get('quality_scoring.mode', 'llm')
        self.sampling_rate = config.get('quality_scoring.sampling_rate', 0.1)
        self.monthly_budget = config.get('quality_scoring.monthly_budget_usd', 5.0)
        self.fallback_to_heuristic = config.get('quality_scoring.fallback_to_heuristic', True)
        self.async_evaluation = config.get('quality_scoring.async_evaluation', True)
        self.timeout = config.get('quality_scoring.timeout_sec', 30)
        self.model = config.get('quality_scoring.model', 'claude-3-haiku-20240307')

        # Configure logging
        if log_path is None:
            log_path_str = config.get(
                'quality_scoring.log_path',
                '.claude/context/sessions/quality_scores.jsonl'
            )
            log_path = Path(log_path_str).expanduser()

        if not log_path.is_absolute():
            log_path = Path.cwd() / log_path

        self.log_path = log_path
        self.writer = JSONLWriter(log_path)

        # Initialize components
        self.cost_tracker = CostTracker(log_path)
        self.heuristic_scorer = HeuristicScorer()
        self.prompts = QualityEvaluationPrompts()

        # Initialize LLM evaluator if enabled and available
        self.evaluator = None
        if self.mode == 'llm':
            try:
                self.evaluator = LLMEvaluator(
                    model=self.model,
                    timeout=self.timeout
                )
            except Exception as e:
                print(f"Warning: Failed to initialize LLM evaluator: {e}", file=sys.stderr)
                if not self.fallback_to_heuristic:
                    raise

    def should_evaluate(self) -> bool:
        """
        Determine if this query should be evaluated (sampling).

        Returns:
            True if should evaluate
        """
        if not self.enabled:
            return False

        # Check sampling rate
        if random.random() > self.sampling_rate:
            return False

        # Check budget
        within_budget, current_spend, remaining = self.cost_tracker.check_budget(
            self.monthly_budget
        )

        if not within_budget:
            print(f"Warning: Monthly budget exceeded (${current_spend:.2f} / ${self.monthly_budget:.2f})", file=sys.stderr)
            return False

        return True

    async def evaluate_async(
        self,
        event_id: str,
        query: str,
        results: List[Dict],
        config_dict: Dict
    ) -> Optional[Dict]:
        """
        Evaluate quality asynchronously.

        Args:
            event_id: Recall event ID
            query: Search query
            results: Search results
            config_dict: Search configuration

        Returns:
            Quality evaluation dictionary or None
        """
        if not self.should_evaluate():
            return None

        try:
            # Run evaluation
            evaluation = await self._run_evaluation_async(query, results, config_dict)

            # Add metadata
            evaluation['event_id'] = event_id
            evaluation['timestamp'] = datetime.now(timezone.utc).isoformat()
            evaluation['query'] = query
            evaluation['result_count'] = len(results)
            evaluation['search_mode'] = config_dict.get('mode', 'unknown')

            # Log result
            self.writer.append(evaluation)

            return evaluation

        except Exception as e:
            print(f"Warning: Quality evaluation failed for {event_id}: {e}", file=sys.stderr)
            return None

    def evaluate(
        self,
        event_id: str,
        query: str,
        results: List[Dict],
        config_dict: Dict
    ) -> Optional[Dict]:
        """
        Evaluate quality synchronously.

        Args:
            event_id: Recall event ID
            query: Search query
            results: Search results
            config_dict: Search configuration

        Returns:
            Quality evaluation dictionary or None
        """
        if not self.should_evaluate():
            return None

        try:
            # Run evaluation
            evaluation = self._run_evaluation(query, results, config_dict)

            # Add metadata
            evaluation['event_id'] = event_id
            evaluation['timestamp'] = datetime.now(timezone.utc).isoformat()
            evaluation['query'] = query
            evaluation['result_count'] = len(results)
            evaluation['search_mode'] = config_dict.get('mode', 'unknown')

            # Log result
            self.writer.append(evaluation)

            return evaluation

        except Exception as e:
            print(f"Warning: Quality evaluation failed for {event_id}: {e}", file=sys.stderr)
            return None

    async def _run_evaluation_async(
        self,
        query: str,
        results: List[Dict],
        config_dict: Dict
    ) -> Dict:
        """Run evaluation asynchronously (with fallback)."""
        # Try LLM evaluation first
        if self.evaluator:
            try:
                return await self._llm_evaluation_async(query, results, config_dict)
            except Exception as e:
                print(f"Warning: LLM evaluation failed: {e}", file=sys.stderr)
                if not self.fallback_to_heuristic:
                    raise

        # Fall back to heuristic
        return self._heuristic_evaluation(query, results, config_dict)

    def _run_evaluation(
        self,
        query: str,
        results: List[Dict],
        config_dict: Dict
    ) -> Dict:
        """Run evaluation synchronously (with fallback)."""
        # Try LLM evaluation first
        if self.evaluator:
            try:
                return self._llm_evaluation(query, results, config_dict)
            except Exception as e:
                print(f"Warning: LLM evaluation failed: {e}", file=sys.stderr)
                if not self.fallback_to_heuristic:
                    raise

        # Fall back to heuristic
        return self._heuristic_evaluation(query, results, config_dict)

    async def _llm_evaluation_async(
        self,
        query: str,
        results: List[Dict],
        config_dict: Dict
    ) -> Dict:
        """Perform LLM evaluation asynchronously."""
        # Generate prompt
        prompt = self.prompts.get_comprehensive_prompt(query, results, config_dict)

        # Call API
        evaluation, usage = await self.evaluator.evaluate_async(prompt)

        # Validate response
        if not self.evaluator.validate_response(evaluation):
            raise ValueError("Invalid evaluation response")

        # Calculate cost
        cost = self.cost_tracker.calculate_cost(
            self.model,
            usage['input_tokens'],
            usage['output_tokens']
        )

        # Add metadata
        evaluation['scoring_method'] = 'llm'
        evaluation['model'] = self.model
        evaluation['usage'] = usage
        evaluation['cost_usd'] = cost

        return evaluation

    def _llm_evaluation(
        self,
        query: str,
        results: List[Dict],
        config_dict: Dict
    ) -> Dict:
        """Perform LLM evaluation synchronously."""
        # Generate prompt
        prompt = self.prompts.get_comprehensive_prompt(query, results, config_dict)

        # Call API
        evaluation, usage = self.evaluator.evaluate(prompt)

        # Validate response
        if not self.evaluator.validate_response(evaluation):
            raise ValueError("Invalid evaluation response")

        # Calculate cost
        cost = self.cost_tracker.calculate_cost(
            self.model,
            usage['input_tokens'],
            usage['output_tokens']
        )

        # Add metadata
        evaluation['scoring_method'] = 'llm'
        evaluation['model'] = self.model
        evaluation['usage'] = usage
        evaluation['cost_usd'] = cost

        return evaluation

    def _heuristic_evaluation(
        self,
        query: str,
        results: List[Dict],
        config_dict: Dict
    ) -> Dict:
        """Perform heuristic evaluation (zero cost)."""
        evaluation = self.heuristic_scorer.score_quality(query, results, config_dict)

        # Add metadata
        evaluation['cost_usd'] = 0.0

        return evaluation

    def get_cost_summary(self) -> Dict:
        """Get cost summary."""
        return self.cost_tracker.get_cost_summary(self.monthly_budget)

    def suggest_sampling_rate(self, searches_per_day: int) -> Dict:
        """Suggest optimal sampling rate for budget."""
        return self.cost_tracker.suggest_sampling_rate(
            self.monthly_budget,
            searches_per_day
        )
