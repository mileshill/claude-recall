"""
Cost tracking for quality scoring API calls.

Tracks token usage, calculates costs, enforces budget limits.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict


class CostTracker:
    """
    Tracks API costs for quality scoring.

    Features:
    - Token counting and cost calculation
    - Monthly budget enforcement
    - Cost projections
    - Per-model pricing
    """

    # Pricing per 1M tokens (as of 2026)
    PRICING = {
        'claude-3-haiku-20240307': {
            'input': 0.25,   # $0.25 per 1M input tokens
            'output': 1.25   # $1.25 per 1M output tokens
        },
        'claude-3-5-haiku-20241022': {
            'input': 0.80,   # $0.80 per 1M input tokens
            'output': 4.00   # $4.00 per 1M output tokens
        }
    }

    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize cost tracker.

        Args:
            log_path: Path to quality scores log (for reading costs)
        """
        self.log_path = log_path
        self.monthly_totals = defaultdict(float)  # month -> cost

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for a single API call.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if model not in self.PRICING:
            # Default to Haiku pricing if model unknown
            model = 'claude-3-haiku-20240307'

        pricing = self.PRICING[model]

        # Calculate cost per token (divide by 1M)
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        return input_cost + output_cost

    def load_monthly_costs(self) -> Dict[str, float]:
        """
        Load monthly costs from log file.

        Returns:
            Dictionary of month -> total cost
        """
        if not self.log_path or not self.log_path.exists():
            return {}

        monthly_costs = defaultdict(float)

        try:
            with open(self.log_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)

                        # Get timestamp
                        timestamp_str = entry.get('timestamp', '')
                        if not timestamp_str:
                            continue

                        # Parse month (YYYY-MM)
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        month_key = timestamp.strftime('%Y-%m')

                        # Add cost
                        cost = entry.get('cost_usd', 0.0)
                        monthly_costs[month_key] += cost

                    except (json.JSONDecodeError, ValueError):
                        continue

        except Exception:
            pass

        return dict(monthly_costs)

    def get_current_month_spend(self) -> float:
        """
        Get total spend for current month.

        Returns:
            Total USD spent this month
        """
        monthly_costs = self.load_monthly_costs()
        current_month = datetime.now(timezone.utc).strftime('%Y-%m')
        return monthly_costs.get(current_month, 0.0)

    def check_budget(self, monthly_budget: float) -> Tuple[bool, float, float]:
        """
        Check if budget allows more API calls.

        Args:
            monthly_budget: Monthly budget limit in USD

        Returns:
            Tuple of (within_budget, current_spend, remaining)
        """
        current_spend = self.get_current_month_spend()
        remaining = monthly_budget - current_spend
        within_budget = remaining > 0

        return within_budget, current_spend, remaining

    def estimate_monthly_cost(
        self,
        searches_per_day: int,
        sampling_rate: float,
        avg_tokens_per_eval: int = 1500
    ) -> Dict:
        """
        Estimate monthly cost based on usage patterns.

        Args:
            searches_per_day: Average searches per day
            sampling_rate: Sampling rate (0-1)
            avg_tokens_per_eval: Average tokens per evaluation

        Returns:
            Dictionary with cost projections
        """
        # Evaluations per month
        evals_per_month = searches_per_day * 30 * sampling_rate

        # Assume 80% input, 20% output split
        input_tokens = int(avg_tokens_per_eval * 0.8)
        output_tokens = int(avg_tokens_per_eval * 0.2)

        # Calculate cost (use Haiku by default)
        cost_per_eval = self.calculate_cost(
            'claude-3-haiku-20240307',
            input_tokens,
            output_tokens
        )

        monthly_cost = evals_per_month * cost_per_eval

        return {
            'searches_per_day': searches_per_day,
            'sampling_rate': sampling_rate,
            'evals_per_month': evals_per_month,
            'cost_per_eval_usd': cost_per_eval,
            'estimated_monthly_cost_usd': monthly_cost,
            'avg_tokens_per_eval': avg_tokens_per_eval
        }

    def get_cost_summary(self, monthly_budget: float) -> Dict:
        """
        Get comprehensive cost summary.

        Args:
            monthly_budget: Monthly budget limit

        Returns:
            Dictionary with cost summary
        """
        within_budget, current_spend, remaining = self.check_budget(monthly_budget)

        # Get all monthly costs
        monthly_costs = self.load_monthly_costs()

        # Calculate average
        avg_monthly = sum(monthly_costs.values()) / max(len(monthly_costs), 1)

        current_month = datetime.now(timezone.utc).strftime('%Y-%m')

        return {
            'current_month': current_month,
            'monthly_budget_usd': monthly_budget,
            'current_spend_usd': current_spend,
            'remaining_budget_usd': remaining,
            'within_budget': within_budget,
            'budget_utilization': current_spend / monthly_budget if monthly_budget > 0 else 0,
            'avg_monthly_spend_usd': avg_monthly,
            'total_months_tracked': len(monthly_costs),
            'monthly_history': monthly_costs
        }

    def suggest_sampling_rate(
        self,
        monthly_budget: float,
        searches_per_day: int,
        avg_tokens_per_eval: int = 1500
    ) -> Dict:
        """
        Suggest optimal sampling rate for budget.

        Args:
            monthly_budget: Monthly budget limit
            searches_per_day: Average searches per day
            avg_tokens_per_eval: Average tokens per evaluation

        Returns:
            Dictionary with suggested rate and analysis
        """
        # Calculate cost per eval
        input_tokens = int(avg_tokens_per_eval * 0.8)
        output_tokens = int(avg_tokens_per_eval * 0.2)
        cost_per_eval = self.calculate_cost(
            'claude-3-haiku-20240307',
            input_tokens,
            output_tokens
        )

        # Total searches per month
        searches_per_month = searches_per_day * 30

        # Max evals within budget
        max_evals = monthly_budget / cost_per_eval

        # Suggested sampling rate
        suggested_rate = min(max_evals / searches_per_month, 1.0)

        # Round to nearest 0.05
        suggested_rate = round(suggested_rate * 20) / 20

        return {
            'suggested_sampling_rate': suggested_rate,
            'monthly_budget_usd': monthly_budget,
            'searches_per_day': searches_per_day,
            'searches_per_month': searches_per_month,
            'cost_per_eval_usd': cost_per_eval,
            'max_evals_per_month': int(max_evals),
            'actual_evals_per_month': int(searches_per_month * suggested_rate),
            'estimated_monthly_cost_usd': searches_per_month * suggested_rate * cost_per_eval
        }

    def log_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create log entry for API call.

        Args:
            model: Model used
            input_tokens: Input tokens
            output_tokens: Output tokens
            cost_usd: Calculated cost
            metadata: Optional metadata

        Returns:
            Log entry dictionary
        """
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'model': model,
            'usage': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens
            },
            'cost_usd': cost_usd,
            'pricing': self.PRICING.get(model, {})
        }

        if metadata:
            entry['metadata'] = metadata

        return entry
