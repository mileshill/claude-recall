"""
Quality checks system for recall analytics.

Provides automated health monitoring with 7 different checks,
orchestration, and multi-channel alerting.
"""

from .checks import (
    QualityCheck,
    CheckResult,
    LowRelevanceCheck,
    NoResultsCheck,
    HighLatencyCheck,
    IndexHealthCheck,
    EmbeddingDriftCheck,
    FalsePositiveCheck,
    UsageAnomalyCheck,
    ALL_CHECKS,
)
from .runner import QualityCheckRunner
from .alerts import AlertManager

__all__ = [
    'QualityCheck',
    'CheckResult',
    'LowRelevanceCheck',
    'NoResultsCheck',
    'HighLatencyCheck',
    'IndexHealthCheck',
    'EmbeddingDriftCheck',
    'FalsePositiveCheck',
    'UsageAnomalyCheck',
    'ALL_CHECKS',
    'QualityCheckRunner',
    'AlertManager',
]
