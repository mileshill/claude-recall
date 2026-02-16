"""
Recall analytics reporting system.

Provides data aggregation, formatting, and report generation for analytics data.
"""

from .aggregator import DataAggregator
from .formatters import MarkdownFormatter, JSONFormatter, HTMLFormatter, ASCIIChart
from .generator import ReportGenerator

__all__ = [
    'DataAggregator',
    'MarkdownFormatter',
    'JSONFormatter',
    'HTMLFormatter',
    'ASCIIChart',
    'ReportGenerator',
]
