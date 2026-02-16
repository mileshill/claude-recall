# Metrics Package - Shared Utilities

This package provides common utilities used across all analytics components in the Claude Recall system.

## Overview

The metrics package contains shared functionality that prevents code duplication and ensures consistency across the analytics system:

- **jsonl_utils**: Thread-safe JSONL file reading and writing
- **calculator**: Metric calculations (scores, distributions, similarity)
- **event_correlation**: Event ID generation and cross-log correlation
- **session_loader**: Load and cache session content
- **config**: Unified configuration management

## Modules

### jsonl_utils.py

Thread-safe JSONL reading and writing with file locking and batching.

**Classes**:
- `JSONLReader`: Read and filter JSONL logs
- `JSONLWriter`: Atomic single-entry writes with fcntl locking
- `BatchedJSONLWriter`: Buffered writes with automatic flushing

**Usage**:
```python
from metrics.jsonl_utils import JSONLReader, BatchedJSONLWriter

# Read log with date filtering
entries = JSONLReader.read_log(
    Path(".claude/context/sessions/recall_analytics.jsonl"),
    days=30,  # Last 30 days only
    filter_fn=lambda e: e.get("event_type") == "recall_triggered"
)

# Buffered writing
with BatchedJSONLWriter(log_path, batch_size=10) as writer:
    for event in events:
        writer.append(event)
    # Automatically flushes on exit
```

**Features**:
- File locking prevents corruption from concurrent writes
- Date filtering for efficient log queries
- Custom filter functions
- Automatic batching for performance
- Graceful handling of malformed JSON lines

### calculator.py

Common metric calculations used across analytics.

**Class**: `MetricsCalculator`

**Methods**:
- `score_stats(scores)`: Calculate mean, median, percentiles, std dev
- `score_distribution(scores)`: Bucket scores into high/medium/low
- `calculate_similarity(text1, text2)`: Jaccard similarity between texts
- `extract_common_terms(text1, text2)`: Find common important terms
- `latency_stats(latencies_ms)`: Calculate latency statistics
- `count_by_field(items, field)`: Count occurrences (supports dot notation)
- `average_by_field(items, field)`: Average numeric field (supports dot notation)

**Usage**:
```python
from metrics.calculator import MetricsCalculator

# Score statistics
scores = [0.85, 0.72, 0.91, 0.68]
stats = MetricsCalculator.score_stats(scores)
# Returns: {avg, min, max, median, std, p50, p95, p99, count}

# Distribution
dist = MetricsCalculator.score_distribution(scores)
# Returns: {high, medium, low, high_pct, medium_pct, low_pct}

# Text similarity
sim = MetricsCalculator.calculate_similarity(
    "implement authentication",
    "add authentication system"
)
# Returns: 0.67 (Jaccard similarity)
```

**Features**:
- Handles empty inputs gracefully
- Uses numpy for efficient calculations
- Supports dot notation for nested fields
- All division-by-zero cases handled

### event_correlation.py

Event ID generation and cross-log correlation.

**Class**: `EventCorrelator`

**Methods**:
- `generate_event_id()`: Generate UUID for events
- `find_related_events(event_id, *log_paths)`: Find events across logs
- `build_event_timeline(event_id, all_logs)`: Chronological event history
- `get_event_chain(event_id, ...)`: Get telemetry → impact → quality chain
- `find_session_events(session_id, telemetry_log)`: All events for session
- `get_event_count_by_type(log_path)`: Count events by type

**Usage**:
```python
from metrics.event_correlation import EventCorrelator

# Generate event ID
event_id = EventCorrelator.generate_event_id()

# Find related events across logs
related = EventCorrelator.find_related_events(
    event_id,
    Path(".claude/context/sessions/recall_analytics.jsonl"),
    Path(".claude/context/sessions/context_impact.jsonl"),
    Path(".claude/context/sessions/quality_scores.jsonl")
)

# Get complete event chain
chain = EventCorrelator.get_event_chain(
    event_id,
    telemetry_log=Path("recall_analytics.jsonl"),
    impact_log=Path("context_impact.jsonl"),
    quality_log=Path("quality_scores.jsonl")
)
# Returns: {telemetry: {...}, impact: {...}, quality: {...}}
```

**Features**:
- Links events across telemetry, impact analysis, and quality scoring
- Supports both `event_id` and `recall_event_id` fields
- Chronological timeline construction
- Session-level event aggregation

### session_loader.py

Load and cache session content for performance.

**Class**: `SessionLoader`

**Methods**:
- `load_session(session_id)`: Load markdown with metadata parsing
- `load_transcript(session_id)`: Load JSONL transcript
- `load_multiple_sessions(session_ids)`: Batch loading
- `get_session_summary(session_id)`: Get just the summary
- `get_session_topics(session_id)`: Get just the topics
- `extract_section(content, section_title)`: Extract markdown section
- `clear_cache()`: Clear cached sessions

**Usage**:
```python
from metrics.session_loader import SessionLoader

loader = SessionLoader(Path(".claude/context/sessions"))

# Load session with metadata
session = loader.load_session("2026-02-16_093045")
# Returns: {summary, topics, status, files_modified, content, ...}

# Load transcript
transcript = loader.load_transcript("2026-02-16_093045")
# Returns: List of message dictionaries

# Batch loading (efficient)
sessions = loader.load_multiple_sessions([
    "2026-02-16_093045",
    "2026-02-15_140532"
])
```

**Features**:
- In-memory caching for performance
- Automatic metadata parsing from markdown
- Graceful handling of missing files
- Supports batch operations

### config.py

Unified configuration management with defaults and env var overrides.

**Class**: `AnalyticsConfig` (singleton)

**Usage**:
```python
from metrics.config import config

# Check if feature enabled
if config.is_enabled('telemetry'):
    # ... telemetry code

# Get configuration value (dot notation)
log_path = config.get('telemetry.log_path')
sampling_rate = config.get('quality_scoring.sampling_rate', 0.1)

# Set value (runtime only)
config.set('telemetry.enabled', False)

# Get all configuration
all_config = config.get_all()
```

**Configuration File**: `config/analytics_config.json`

**Environment Variable Overrides**:
- `ANTHROPIC_API_KEY`: Quality scoring API key
- `RECALL_ANALYTICS_TELEMETRY_ENABLED`: Enable/disable telemetry
- `RECALL_ANALYTICS_QUALITY_SCORING_ENABLED`: Enable/disable quality scoring

**Features**:
- Singleton pattern (single instance across all modules)
- Loads from JSON with fallback to defaults
- Environment variable overrides
- Dot-notation access for nested values
- Feature enable/disable checks

## Common Patterns

### Error Handling

All modules handle errors gracefully:
- Missing files return empty lists/None
- Malformed data is logged but doesn't crash
- Division by zero returns sensible defaults (0 or 0.0)

### Thread Safety

JSONL writers use fcntl file locking:
```python
# Safe for concurrent writes
writer = JSONLWriter(path)
writer.append(data)  # Atomically appends
```

### Caching

SessionLoader caches loaded sessions:
```python
loader = SessionLoader(session_dir)
session = loader.load_session(id)  # Loads from disk
session = loader.load_session(id)  # Returns from cache
loader.clear_cache()  # Clear when needed
```

### Batching

Use BatchedJSONLWriter for performance:
```python
with BatchedJSONLWriter(path, batch_size=10) as writer:
    for item in large_list:
        writer.append(item)
        # Automatically flushes every 10 items
```

## Testing

All modules should have corresponding test files:
```bash
pytest scripts/metrics/test_jsonl_utils.py
pytest scripts/metrics/test_calculator.py
pytest scripts/metrics/test_config.py
# etc.
```

## Dependencies

- Python 3.8+
- numpy (for efficient calculations)
- Standard library: json, pathlib, datetime, fcntl, uuid, re

## Performance Considerations

- **Batched writes**: Use `BatchedJSONLWriter` instead of `JSONLWriter` for high-volume logging
- **Caching**: `SessionLoader` caches sessions in memory - clear when memory constrained
- **Date filtering**: Use `days` parameter to avoid loading entire logs
- **Custom filters**: Filter early in `JSONLReader.read_log()` to reduce memory usage

## Best Practices

1. **Always use timezone-aware datetimes**: `datetime.now(timezone.utc)`
2. **Use default=str for JSON**: `json.dumps(data, default=str)` for numpy types
3. **Handle empty inputs**: Check for None/empty before calculations
4. **Use context managers**: `with BatchedJSONLWriter(...) as writer:`
5. **Log warnings, don't crash**: Use try/except with warnings for non-critical errors

## Version

Current version: 1.0.0

## See Also

- `config/ANALYTICS_CONFIG.md` - Configuration reference
- `docs/ANALYTICS_EPIC_GUIDE.md` - Implementation guide
- `docs/TELEMETRY_SCHEMA.md` - Event schemas (Phase 1)
