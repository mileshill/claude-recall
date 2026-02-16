"""
Quality scoring package for recall search results.

Provides LLM-based and heuristic quality evaluation with cost controls.
"""

from .cost_tracker import CostTracker
from .prompt_templates import QualityEvaluationPrompts
from .heuristic_scorer import HeuristicScorer
from .evaluator import LLMEvaluator
from .scorer import QualityScorer

__all__ = [
    'CostTracker',
    'QualityEvaluationPrompts',
    'HeuristicScorer',
    'LLMEvaluator',
    'QualityScorer'
]

__version__ = '1.0.0'
