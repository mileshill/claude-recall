# Telemetry System

Comprehensive event tracking for all recall operations.

## Overview

The telemetry system captures structured events for every recall operation, enabling analytics, impact analysis, and quality monitoring.

## Architecture

```
telemetry/
├── schema.py           # Event schemas (dataclasses)
├── collector.py        # Event collection with buffering
├── context.py          # Session/system info helpers
├── test_collector.py   # Unit tests
├── test_integration.py # Integration tests
└── run_tests.sh        # Test runner
```

## Event Types

### recall_triggered
Logged by `search_index.py` for every search operation.

**Fields:**
- `query`: Raw query, keywords, technical terms, query length
- `search_config`: Mode (bm25/hybrid/semantic), limit, filters
- `results`: Count, retrieved sessions, scores (top/avg/min), distribution
- `performance`: Total latency, breakdown (index_load, filter, search)
- `system_state`: Index size, embeddings available, memory usage
- `outcome`: Success status

### context_analyzed
Logged by `smart_recall.py` when analyzing context.

**Fields:**
- `context`: Context length, keywords, technical terms, search query
- `performance`: Analysis time

### smart_recall_completed
Logged by `smart_recall.py` after filtering results.

**Fields:**
- `query`: Generated query, extracted keywords, technical terms
- `search_config`: Mode, limit, min_relevance threshold
- `results`: Final count, sessions, filtering stats
- `performance`: Total latency, breakdown (analysis, search)

## Usage

### Collector API

```python
from telemetry import get_collector

collector = get_collector()

# Start event
event_id = collector.start_event(
    event_type="recall_triggered",
    context={"initial": "data"}
)

# Update with more data
collector.update_event(event_id, {
    "results": {"count": 5}
})

# End event
collector.end_event(event_id, outcome={"success": True})

# Flush to disk (automatic with buffering)
collector.flush()
```

### Log Events Directly

```python
# For simple events without lifecycle
collector.log_event({
    "event_type": "context_analyzed",
    "context": {"keywords": ["auth", "bug"]}
})
```

## Configuration

Configured via `config/analytics_config.json`:

```json
{
  "telemetry": {
    "enabled": true,
    "log_path": ".claude/context/sessions/recall_analytics.jsonl",
    "sampling_rate": 1.0,
    "batch_size": 10,
    "batch_flush_interval_sec": 5.0,
    "pii_redaction": true,
    "buffer_writes": true
  }
}
```

## Features

### Buffered Writes
Events are batched in memory and flushed when:
- Buffer reaches `batch_size` (default: 10)
- Time since last flush exceeds `batch_flush_interval_sec` (default: 5s)
- `flush()` is called explicitly

### PII Redaction
Automatically redacts API keys and secrets from queries using `SecretRedactor` (if available).

### Error Handling
Graceful degradation - telemetry failures never crash the main application.

### Event Correlation
All events include `session_id` and `event_id` for correlation:
- Track complete flow: context analysis → search → results
- Correlate with impact analysis and quality scoring
- Debug issues by following event chains

## Log Format

JSONL format (one JSON object per line):

```json
{
  "event_id": "uuid",
  "timestamp": "2026-02-16T19:00:00+00:00",
  "event_type": "recall_triggered",
  "trigger_source": "search_index",
  "session_id": "pid_12345",
  "query": {...},
  "results": {...},
  "performance": {...},
  "outcome": {"success": true}
}
```

## Testing

Run all tests:
```bash
./scripts/telemetry/run_tests.sh
```

Run specific tests:
```bash
python3 scripts/telemetry/test_collector.py
python3 scripts/telemetry/test_integration.py
```

### Test Coverage

**Collector Tests (`test_collector.py`):**
- Event lifecycle (start → update → end)
- Buffering behavior
- PII redaction (if available)
- Disabled telemetry handling
- Error handling and graceful degradation

**Integration Tests (`test_integration.py`):**
- Search telemetry (search_index.py)
- Smart recall telemetry (smart_recall.py)
- Context analysis extraction
- Error telemetry logging

## Performance

- **Overhead**: < 1ms per event (buffered)
- **Memory**: ~1KB per event in buffer
- **Disk I/O**: Batched writes minimize overhead
- **Non-blocking**: Telemetry never blocks main operations

## Troubleshooting

### Telemetry not writing

Check:
1. `telemetry.enabled` is `true` in config
2. Log directory exists: `.claude/context/sessions/`
3. Buffer may not be full - call `collector.flush()`
4. Check stderr for warnings

### Missing fields

Some fields are optional:
- `memory_usage_mb`: Requires `psutil` package
- PII redaction: Requires `redact_secrets` package
- Semantic scores: Requires embeddings

### Correlation issues

All events in same session share `session_id`:
- Set via `CLAUDE_SESSION_ID` environment variable
- Falls back to `pid_{process_id}`

Use `event_id` to correlate start/update/end cycles.

## Next Steps

Phase 1 (Telemetry) complete! Next phases:
- **Phase 2**: Context Impact Analysis
- **Phase 3**: Semantic Quality Scoring
- **Phase 4**: Dashboard & Reporting
- **Phase 5**: Automatic Quality Checks
