"""
Telemetry package for recall analytics.

Provides event tracking for all recall operations with structured schemas,
buffered writes, and optional PII redaction.
"""

from .schema import (
    QueryData,
    SearchConfig,
    ScoreStats,
    ResultData,
    PerformanceData,
    SystemState,
    TelemetryEvent
)

from .collector import TelemetryCollector, get_collector
from .context import (
    get_current_session_id,
    get_system_state,
    get_project_dir,
    is_hook_triggered
)

__all__ = [
    # Schemas
    'QueryData',
    'SearchConfig',
    'ScoreStats',
    'ResultData',
    'PerformanceData',
    'SystemState',
    'TelemetryEvent',
    # Collector
    'TelemetryCollector',
    'get_collector',
    # Context
    'get_current_session_id',
    'get_system_state',
    'get_project_dir',
    'is_hook_triggered',
]

__version__ = '1.0.0'
