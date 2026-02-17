# Telemetry Schema Reference

Complete reference for all telemetry event types and fields in Claude Recall Analytics.

## Overview

All telemetry events are stored in JSONL format (one JSON object per line) in:
```
~/.claude/context/sessions/recall_analytics.jsonl
```

## Common Fields

All events share these base fields:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Unique event identifier (UUID-like) |
| `timestamp` | string | ISO 8601 timestamp with timezone |
| `event_type` | string | Type of event (see below) |
| `session_id` | string | Current Claude session ID |

## Event Types

### search_started

Logged when a search operation begins.

**Event Type:** `search_started`

**Fields:**
```json
{
  "event_id": "evt_123abc",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "event_type": "search_started",
  "session_id": "session_abc123",
  "query": "how to implement authentication",
  "search_config": {
    "mode": "auto",
    "bm25_weight": 0.5,
    "semantic_weight": 0.5,
    "top_k": 5
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | User's search query |
| `search_config.mode` | string | Search mode: "auto", "hybrid", "bm25", "semantic" |
| `search_config.bm25_weight` | number | BM25 weight (0.0-1.0) |
| `search_config.semantic_weight` | number | Semantic weight (0.0-1.0) |
| `search_config.top_k` | number | Number of results to return |

### search_completed

Logged when a search operation completes successfully.

**Event Type:** `search_completed`

**Fields:**
```json
{
  "event_id": "evt_123abc",
  "timestamp": "2024-01-15T10:30:00.500Z",
  "event_type": "search_completed",
  "session_id": "session_abc123",
  "query": "how to implement authentication",
  "search_config": {
    "mode": "auto",
    "mode_resolved": "hybrid",
    "bm25_weight": 0.5,
    "semantic_weight": 0.5,
    "top_k": 5
  },
  "results": {
    "session_ids": ["session_1", "session_2", "session_3"],
    "count": 3,
    "scores": {
      "session_1": 0.85,
      "session_2": 0.72,
      "session_3": 0.68
    },
    "embedding_dim": 384
  },
  "performance": {
    "total_latency_ms": 245.3,
    "index_load_ms": 50.2,
    "bm25_search_ms": 75.1,
    "semantic_search_ms": 95.0,
    "merge_ms": 15.0,
    "formatting_ms": 10.0,
    "cache_hit": false
  },
  "system": {
    "index_size": 1250,
    "memory_usage_mb": 156.7,
    "index_version": "1.0.0"
  }
}
```

**Results Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `results.session_ids` | array | List of matching session IDs |
| `results.count` | number | Number of results returned |
| `results.scores` | object | Score for each session (0.0-1.0) |
| `results.embedding_dim` | number | Dimension of embeddings used |

**Performance Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `performance.total_latency_ms` | number | Total search latency in milliseconds |
| `performance.index_load_ms` | number | Time to load index |
| `performance.bm25_search_ms` | number | BM25 search time |
| `performance.semantic_search_ms` | number | Semantic search time |
| `performance.merge_ms` | number | Time to merge results |
| `performance.formatting_ms` | number | Time to format output |
| `performance.cache_hit` | boolean | Whether index was cached |

**System Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `system.index_size` | number | Number of sessions in index |
| `system.memory_usage_mb` | number | Current memory usage |
| `system.index_version` | string | Index schema version |

### search_failed

Logged when a search operation fails.

**Event Type:** `search_failed`

**Fields:**
```json
{
  "event_id": "evt_123abc",
  "timestamp": "2024-01-15T10:30:00.100Z",
  "event_type": "search_failed",
  "session_id": "session_abc123",
  "query": "test query",
  "error": {
    "type": "IndexNotFoundError",
    "message": "Index file not found",
    "stack_trace": "..."
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error.type` | string | Error type/class |
| `error.message` | string | Error message |
| `error.stack_trace` | string | Full stack trace (optional) |

### context_analyzed

Logged when smart_recall analyzes conversation context.

**Event Type:** `context_analyzed`

**Fields:**
```json
{
  "event_id": "evt_456def",
  "timestamp": "2024-01-15T10:29:45.000Z",
  "event_type": "context_analyzed",
  "session_id": "session_abc123",
  "analysis": {
    "keywords": ["authentication", "JWT", "OAuth", "security"],
    "technical_terms": ["token", "bearer", "refresh"],
    "entities": ["JWT", "OAuth2"],
    "search_query": "JWT authentication implementation"
  },
  "context": {
    "length": 1500,
    "turns": 10,
    "has_code": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `analysis.keywords` | array | Extracted keywords |
| `analysis.technical_terms` | array | Technical terminology found |
| `analysis.entities` | array | Named entities |
| `analysis.search_query` | string | Generated search query |
| `context.length` | number | Context length in characters |
| `context.turns` | number | Number of conversation turns |
| `context.has_code` | boolean | Whether context contains code |

### smart_recall_completed

Logged when smart recall completes.

**Event Type:** `smart_recall_completed`

**Fields:**
```json
{
  "event_id": "evt_789ghi",
  "timestamp": "2024-01-15T10:30:01.000Z",
  "event_type": "smart_recall_completed",
  "session_id": "session_abc123",
  "search_event_id": "evt_123abc",
  "results_formatted": true,
  "output_length": 2500
}
```

| Field | Type | Description |
|-------|------|-------------|
| `search_event_id` | string | ID of associated search event |
| `results_formatted` | boolean | Whether results were formatted |
| `output_length` | number | Length of formatted output |

### excerpt_extraction_completed

Logged when transcript excerpts are extracted and displayed.

**Event Type:** `excerpt_extraction_completed`

**Fields:**
```json
{
  "event_id": null,
  "timestamp": "2026-02-17T22:27:19.746257+00:00",
  "event_type": "excerpt_extraction_completed",
  "session_id": "pid_84379",
  "recall_event_id": "7acddd02-abad-4812-a845-6921540dae71",
  "excerpts": {
    "enabled": true,
    "sessions_with_excerpts": 1,
    "total_sessions": 1,
    "total_excerpt_chars": 1785,
    "total_extraction_time_ms": 15.59,
    "excerpts_by_session": [
      {
        "session_id": "2026-02-17_031626_session",
        "char_count": 1785,
        "extraction_ms": 15.59
      }
    ],
    "avg_chars_per_session": 1785,
    "avg_extraction_ms": 15.59
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `recall_event_id` | string | ID of the parent smart_recall_completed event |
| `excerpts.enabled` | boolean | Whether excerpt extraction was enabled |
| `excerpts.sessions_with_excerpts` | number | Number of sessions with excerpts found |
| `excerpts.total_sessions` | number | Total sessions searched |
| `excerpts.total_excerpt_chars` | number | Total characters in all excerpts |
| `excerpts.total_extraction_time_ms` | number | Total time spent extracting excerpts |
| `excerpts.excerpts_by_session` | array | Per-session excerpt statistics |
| `excerpts.avg_chars_per_session` | number | Average characters per session |
| `excerpts.avg_extraction_ms` | number | Average extraction time per session |

**Purpose:**
Tracks the performance and usage of the transcript excerpt feature, which automatically shows relevant conversation snippets from session transcripts instead of just metadata summaries.

**Use Cases:**
- Measure excerpt extraction performance overhead
- Evaluate feature adoption (hit rate)
- Optimize excerpt length and count
- Compare recall quality with vs. without excerpts

## Quality Scoring Events

Quality scoring events are logged separately to:
```
~/.claude/context/sessions/quality_scores.jsonl
```

### quality_evaluation

**Fields:**
```json
{
  "event_id": "evt_123abc",
  "timestamp": "2024-01-15T10:30:05.000Z",
  "query": "how to implement authentication",
  "results_count": 3,
  "scores": {
    "relevance": 0.85,
    "coverage": 0.78,
    "specificity": 0.92,
    "overall": 0.85,
    "explanation": "Results provide comprehensive authentication implementation details..."
  },
  "method": "llm",
  "model": "claude-haiku-4.5-20251001",
  "cost_usd": 0.00042,
  "usage": {
    "input_tokens": 523,
    "output_tokens": 98
  },
  "latency_ms": 850
}
```

| Field | Type | Description |
|-------|------|-------------|
| `scores.relevance` | number | Relevance score (0.0-1.0) |
| `scores.coverage` | number | Coverage score (0.0-1.0) |
| `scores.specificity` | number | Specificity score (0.0-1.0) |
| `scores.overall` | number | Overall quality score (0.0-1.0) |
| `scores.explanation` | string | LLM's explanation of scores |
| `method` | string | "llm" or "heuristic" |
| `model` | string | Model used for evaluation |
| `cost_usd` | number | Cost in USD |
| `usage.input_tokens` | number | Input tokens consumed |
| `usage.output_tokens` | number | Output tokens consumed |

## Impact Analysis Events

Impact analysis events are logged to:
```
~/.claude/context/sessions/context_impact.jsonl
```

### context_impact

**Fields:**
```json
{
  "event_id": "evt_123abc",
  "timestamp": "2024-01-15T11:00:00.000Z",
  "session_id": "session_abc123",
  "recall_event_id": "evt_123abc",
  "recalled_sessions": ["session_1", "session_2"],
  "context_usage": {
    "explicit_citations": 3,
    "implicit_usage_score": 0.72,
    "topics_reused": 5,
    "code_reused": true,
    "files_referenced": 2
  },
  "continuity_score": 0.85,
  "terminology_alignment": {
    "shared_terms": 12,
    "alignment_score": 0.78
  },
  "efficiency_metrics": {
    "estimated_time_saved_minutes": 15.5,
    "repetition_avoided": true,
    "context_efficiency": 0.82
  },
  "user_behavior": {
    "quick_acknowledgment": true,
    "deep_follow_up": true,
    "productivity_indicator": "high"
  }
}
```

**Context Usage Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `context_usage.explicit_citations` | number | Direct references to recalled content |
| `context_usage.implicit_usage_score` | number | Implicit reuse score (0.0-1.0) |
| `context_usage.topics_reused` | number | Number of topics from recalled sessions |
| `context_usage.code_reused` | boolean | Whether code was reused |
| `context_usage.files_referenced` | number | Files from recalled sessions referenced |

**Efficiency Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `efficiency_metrics.estimated_time_saved_minutes` | number | Estimated time saved |
| `efficiency_metrics.repetition_avoided` | boolean | Whether repetition was avoided |
| `efficiency_metrics.context_efficiency` | number | Context efficiency score (0.0-1.0) |

## Querying Events

### Using jq

```bash
# Get all search events
jq 'select(.event_type == "search_completed")' recall_analytics.jsonl

# Get average latency
jq -r 'select(.event_type == "search_completed") | .performance.total_latency_ms' \
  recall_analytics.jsonl | \
  awk '{sum+=$1; count++} END {print sum/count}'

# Count by search mode
jq -r 'select(.event_type == "search_completed") | .search_config.mode_resolved' \
  recall_analytics.jsonl | \
  sort | uniq -c

# Get high-latency searches
jq 'select(.event_type == "search_completed" and .performance.total_latency_ms > 1000)' \
  recall_analytics.jsonl

# Get all errors
jq 'select(.event_type == "search_failed")' recall_analytics.jsonl
```

### Using Python

```python
import json
from pathlib import Path

# Load events
log_path = Path.home() / ".claude" / "context" / "sessions" / "recall_analytics.jsonl"

events = []
with open(log_path, 'r') as f:
    for line in f:
        events.append(json.loads(line.strip()))

# Filter to search completions
searches = [e for e in events if e['event_type'] == 'search_completed']

# Average latency
latencies = [e['performance']['total_latency_ms'] for e in searches]
avg_latency = sum(latencies) / len(latencies)
print(f"Average latency: {avg_latency:.2f}ms")

# Mode distribution
from collections import Counter
modes = [e['search_config']['mode_resolved'] for e in searches]
print("Mode distribution:", Counter(modes))
```

## Event Lifecycle

Typical search event sequence:

1. `search_started` - Search begins
2. `search_completed` - Search finishes (or `search_failed` on error)
3. `quality_evaluation` - Quality scoring (if enabled, sampled)
4. `context_impact` - Impact analysis (later, after session ends)

## Data Retention

- Events are append-only JSONL
- No automatic cleanup by default
- Recommend periodic cleanup (90+ days old)
- Use `scripts/cleanup_old_logs.py` (Phase 7)

## Privacy

- PII redaction enabled by default
- API keys automatically redacted
- Session IDs are pseudonymous
- No user names or emails logged

## See Also

- [Analytics Guide](ANALYTICS_GUIDE.md)
- [Configuration Reference](ANALYTICS_CONFIG.md)
