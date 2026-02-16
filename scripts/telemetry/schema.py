"""
Event schemas for telemetry system.

Defines dataclasses for structured event data with type hints and validation.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class QueryData:
    """Query information."""
    raw_query: str
    extracted_keywords: List[str] = field(default_factory=list)
    technical_terms: List[str] = field(default_factory=list)
    query_length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SearchConfig:
    """Search configuration."""
    mode: str  # "auto", "hybrid", "bm25", "semantic"
    mode_resolved: str  # Actual mode used
    limit: int = 5
    min_relevance: float = 0.0
    filters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ScoreStats:
    """Score statistics."""
    top_score: float = 0.0
    avg_score: float = 0.0
    min_score: float = 0.0
    score_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ResultData:
    """Search results information."""
    count: int = 0
    retrieved_sessions: List[str] = field(default_factory=list)
    scores: ScoreStats = field(default_factory=ScoreStats)
    search_modes_used: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        return data


@dataclass
class PerformanceData:
    """Performance metrics."""
    total_latency_ms: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)
    cache_hit: bool = False
    model_loaded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SystemState:
    """System state information."""
    index_size: int = 0
    embeddings_available: bool = False
    model_cached: bool = False
    memory_usage_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TelemetryEvent:
    """Complete telemetry event."""
    event_id: str
    timestamp: str
    event_type: str  # "recall_triggered", "context_analyzed", etc.
    session_id: Optional[str] = None
    trigger_mode: str = "manual"  # "manual", "proactive", "session_start"
    trigger_source: str = "unknown"  # "search_index", "smart_recall", etc.
    query: Optional[QueryData] = None
    search_config: Optional[SearchConfig] = None
    results: Optional[ResultData] = None
    performance: Optional[PerformanceData] = None
    system_state: Optional[SystemState] = None
    outcome: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling nested dataclasses."""
        data = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
        }

        # Add optional fields if present
        if self.session_id:
            data["session_id"] = self.session_id
        if self.trigger_mode:
            data["trigger_mode"] = self.trigger_mode
        if self.trigger_source:
            data["trigger_source"] = self.trigger_source

        # Handle nested dataclasses
        if self.query:
            data["query"] = self.query.to_dict() if hasattr(self.query, 'to_dict') else self.query
        if self.search_config:
            data["search_config"] = self.search_config.to_dict() if hasattr(self.search_config, 'to_dict') else self.search_config
        if self.results:
            data["results"] = self.results.to_dict() if hasattr(self.results, 'to_dict') else self.results
        if self.performance:
            data["performance"] = self.performance.to_dict() if hasattr(self.performance, 'to_dict') else self.performance
        if self.system_state:
            data["system_state"] = self.system_state.to_dict() if hasattr(self.system_state, 'to_dict') else self.system_state
        if self.outcome:
            data["outcome"] = self.outcome
        if self.error:
            data["error"] = self.error
        if self.error_type:
            data["error_type"] = self.error_type

        return data

    @classmethod
    def create(
        cls,
        event_id: str,
        event_type: str,
        session_id: Optional[str] = None,
        trigger_mode: str = "manual",
        trigger_source: str = "unknown"
    ) -> "TelemetryEvent":
        """Create a new event with timestamp."""
        return cls(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            session_id=session_id,
            trigger_mode=trigger_mode,
            trigger_source=trigger_source
        )
