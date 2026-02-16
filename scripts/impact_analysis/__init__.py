"""
Impact analysis package for recall context.

Analyzes how recalled context is used and measures its impact on
conversation quality and efficiency.
"""

from .detector import ContextUsageDetector
from .scorer import ContinuityScorer
from .metrics import EfficiencyMetrics
from .analyzer import ImpactAnalyzer

__all__ = [
    'ContextUsageDetector',
    'ContinuityScorer',
    'EfficiencyMetrics',
    'ImpactAnalyzer'
]

__version__ = '1.0.0'
