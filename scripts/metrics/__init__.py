"""
Shared utilities for recall analytics system.

This package provides common utilities used across all analytics components:
- jsonl_utils: JSONL file reading/writing with locking
- calculator: Metric calculations (scores, distributions, similarity)
- event_correlation: Event ID generation and correlation
- session_loader: Load and cache session content
- config: Unified configuration management
"""

from .jsonl_utils import JSONLReader, JSONLWriter, BatchedJSONLWriter
from .calculator import MetricsCalculator
from .event_correlation import EventCorrelator
from .session_loader import SessionLoader
from .config import AnalyticsConfig, config

__all__ = [
    'JSONLReader',
    'JSONLWriter',
    'BatchedJSONLWriter',
    'MetricsCalculator',
    'EventCorrelator',
    'SessionLoader',
    'AnalyticsConfig',
    'config',
]

__version__ = '1.0.0'
