# Analytics Configuration Reference

Complete reference for `analytics_config.json` - the unified configuration for all analytics features.

## Location

```
config/analytics_config.json
```

## Configuration Structure

### Top-Level Fields

```json
{
  "version": "1.0.0",
  "telemetry": { ... },
  "impact_analysis": { ... },
  "quality_scoring": { ... },
  "quality_checks": { ... },
  "reporting": { ... },
  "retention": { ... }
}
```

## Telemetry Configuration

Controls event tracking for all recall operations.

```json
"telemetry": {
  "enabled": true,
  "log_path": ".claude/context/sessions/recall_analytics.jsonl",
  "sampling_rate": 1.0,
  "batch_size": 10,
  "batch_flush_interval_sec": 5.0,
  "pii_redaction": true,
  "buffer_writes": true
}
```

**Fields**:
- `enabled` (boolean): Enable/disable telemetry. Default: `true`
- `log_path` (string): Path to telemetry log file (JSONL format)
- `sampling_rate` (float): Sample rate 0.0-1.0. 1.0 = log all events. Default: `1.0`
- `batch_size` (int): Flush buffer after N events. Default: `10`
- `batch_flush_interval_sec` (float): Flush after N seconds. Default: `5.0`
- `pii_redaction` (boolean): Redact queries containing secrets. Default: `true`
- `buffer_writes` (boolean): Use buffered writes for performance. Default: `true`

**Use Cases**:
- Production: `sampling_rate: 1.0` (log everything)
- Testing: `sampling_rate: 0.1` (10% sampling to reduce volume)
- Debugging: `batch_size: 1, batch_flush_interval_sec: 0` (immediate writes)

## Impact Analysis Configuration

Controls analysis of how recalled context affects conversations.

```json
"impact_analysis": {
  "enabled": true,
  "log_path": ".claude/context/sessions/context_impact.jsonl",
  "auto_analyze_on_session_end": true,
  "min_recall_events": 1
}
```

**Fields**:
- `enabled` (boolean): Enable/disable impact analysis. Default: `true`
- `log_path` (string): Path to impact analysis log file
- `auto_analyze_on_session_end` (boolean): Run analysis when session ends. Default: `true`
- `min_recall_events` (int): Minimum recall events to trigger analysis. Default: `1`

**Use Cases**:
- Skip short sessions: `min_recall_events: 2` (only analyze if 2+ recalls)
- Manual analysis: `auto_analyze_on_session_end: false` (run manually)

## Quality Scoring Configuration

Controls LLM-based evaluation of recall quality.

```json
"quality_scoring": {
  "enabled": false,
  "mode": "llm",
  "api_key_env": "ANTHROPIC_API_KEY",
  "model": "claude-3-haiku-20240307",
  "sampling_rate": 0.1,
  "log_path": ".claude/context/sessions/quality_scores.jsonl",
  "fallback_to_heuristic": true,
  "async_evaluation": true,
  "timeout_sec": 30,
  "monthly_budget_usd": 5.0
}
```

**Fields**:
- `enabled` (boolean): Enable/disable quality scoring. Default: `false` (costs money)
- `mode` (string): Scoring mode: `"llm"` or `"heuristic"`. Default: `"llm"`
- `api_key_env` (string): Environment variable containing API key. Default: `"ANTHROPIC_API_KEY"`
- `model` (string): Claude model to use. Default: `"claude-3-haiku-20240307"`
- `sampling_rate` (float): Sample rate 0.0-1.0 for cost control. Default: `0.1` (10%)
- `log_path` (string): Path to quality scores log file
- `fallback_to_heuristic` (boolean): Use heuristic scoring if API fails. Default: `true`
- `async_evaluation` (boolean): Run evaluation in background. Default: `true`
- `timeout_sec` (int): API timeout in seconds. Default: `30`
- `monthly_budget_usd` (float): Monthly spending limit. Default: `5.0`

**Cost Estimates** (with defaults):
- 100 searches/day × 10% sampling × 30 days = 300 evaluations/month
- 300 × $0.0004/eval = **$0.12/month**

**Use Cases**:
- Production: `enabled: false` (use telemetry + impact only)
- Research: `enabled: true, sampling_rate: 0.2` (20% for richer data)
- Cost-conscious: `mode: "heuristic"` (zero-cost rule-based scoring)

## Quality Checks Configuration

Controls automated monitoring and alerting.

```json
"quality_checks": {
  "enabled": true,
  "schedule": "daily",
  "log_path": ".claude/context/sessions/quality_check_log.jsonl",
  "checks": {
    "low_relevance": { ... },
    "high_latency": { ... },
    "no_results": { ... },
    "embedding_drift": { ... },
    "false_positive": { ... },
    "usage_anomaly": { ... },
    "index_health": { ... }
  },
  "alert_methods": ["log", "stderr"]
}
```

**Top-Level Fields**:
- `enabled` (boolean): Enable/disable quality checks. Default: `true`
- `schedule` (string): When to run: `"hourly"`, `"daily"`, `"manual"`. Default: `"daily"`
- `log_path` (string): Path to quality check log file
- `alert_methods` (array): Alert destinations. Options: `"log"`, `"stderr"`, `"email"`, `"slack"`

### Individual Check Configuration

#### low_relevance

Alert when average relevance scores drop below threshold.

```json
"low_relevance": {
  "enabled": true,
  "threshold": 0.4,
  "window_size": 100
}
```

- `threshold` (float): Minimum acceptable average score. Default: `0.4`
- `window_size` (int): Number of recent searches to check. Default: `100`

#### high_latency

Alert when search latency exceeds target.

```json
"high_latency": {
  "enabled": true,
  "threshold_ms": 100.0,
  "p95_threshold_ms": 200.0
}
```

- `threshold_ms` (float): Average latency threshold. Default: `100.0`
- `p95_threshold_ms` (float): P95 latency threshold. Default: `200.0`

#### no_results

Alert when too many searches return no results.

```json
"no_results": {
  "enabled": true,
  "max_rate": 0.15
}
```

- `max_rate` (float): Maximum acceptable no-results rate (0-1). Default: `0.15` (15%)

#### embedding_drift

Detect if semantic search quality is degrading over time.

```json
"embedding_drift": {
  "enabled": true,
  "threshold": 0.2,
  "min_samples": 20
}
```

- `threshold` (float): Max acceptable score drop. Default: `0.2`
- `min_samples` (int): Minimum semantic searches needed. Default: `20`

#### false_positive

Detect high rate of low-quality recall results.

```json
"false_positive": {
  "enabled": true,
  "low_score_threshold": 2.5,
  "max_rate": 0.1
}
```

- `low_score_threshold` (float): Quality scores below this are false positives. Default: `2.5`
- `max_rate` (float): Maximum acceptable false positive rate. Default: `0.1` (10%)

#### usage_anomaly

Detect unusual usage patterns.

```json
"usage_anomaly": {
  "enabled": true,
  "std_dev_threshold": 3.0
}
```

- `std_dev_threshold` (float): Standard deviations for anomaly. Default: `3.0`

#### index_health

Check index health (missing embeddings, stale sessions).

```json
"index_health": {
  "enabled": true
}
```

- No additional configuration needed

## Reporting Configuration

Controls report generation.

```json
"reporting": {
  "enabled": true,
  "default_period_days": 30,
  "default_format": "markdown",
  "output_dir": ".claude/context/reports",
  "include_charts": false
}
```

**Fields**:
- `enabled` (boolean): Enable/disable reporting. Default: `true`
- `default_period_days` (int): Default report period. Default: `30`
- `default_format` (string): Output format: `"markdown"`, `"json"`, `"html"`. Default: `"markdown"`
- `output_dir` (string): Directory for generated reports
- `include_charts` (boolean): Include ASCII charts in reports. Default: `false`

## Retention Configuration

Controls automatic log cleanup.

```json
"retention": {
  "log_retention_days": 90,
  "auto_cleanup": false
}
```

**Fields**:
- `log_retention_days` (int): Keep logs for N days. Default: `90`
- `auto_cleanup` (boolean): Automatically delete old logs. Default: `false`

**Warning**: `auto_cleanup: true` permanently deletes old log entries.

## Environment Variable Overrides

Configuration can be overridden via environment variables:

**API Key**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Feature Toggles**:
```bash
export RECALL_ANALYTICS_TELEMETRY_ENABLED=false
export RECALL_ANALYTICS_QUALITY_SCORING_ENABLED=true
```

## Usage in Code

```python
from metrics.config import config

# Check if enabled
if config.is_enabled('telemetry'):
    # ... telemetry code

# Get value with dot notation
log_path = config.get('telemetry.log_path')
sampling = config.get('quality_scoring.sampling_rate', 0.1)

# Set value (runtime only, not persisted)
config.set('telemetry.enabled', False)
```

## Configuration Presets

### Minimal (Free)
```json
{
  "telemetry": {"enabled": true},
  "impact_analysis": {"enabled": true},
  "quality_scoring": {"enabled": false},
  "quality_checks": {"enabled": false},
  "reporting": {"enabled": true}
}
```

### Standard (Recommended)
```json
{
  "telemetry": {"enabled": true, "sampling_rate": 1.0},
  "impact_analysis": {"enabled": true},
  "quality_scoring": {"enabled": false},
  "quality_checks": {"enabled": true},
  "reporting": {"enabled": true}
}
```

### Full (With Quality Scoring)
```json
{
  "telemetry": {"enabled": true, "sampling_rate": 1.0},
  "impact_analysis": {"enabled": true},
  "quality_scoring": {"enabled": true, "sampling_rate": 0.1},
  "quality_checks": {"enabled": true},
  "reporting": {"enabled": true}
}
```

### Testing/Development
```json
{
  "telemetry": {
    "enabled": true,
    "sampling_rate": 0.1,
    "batch_size": 1,
    "buffer_writes": false
  },
  "impact_analysis": {"enabled": true},
  "quality_scoring": {"enabled": false},
  "quality_checks": {"enabled": false},
  "reporting": {"enabled": true}
}
```

## Validation

To validate your configuration:

```bash
python3 -c "from metrics.config import config; import json; print(json.dumps(config.get_all(), indent=2))"
```

## See Also

- `scripts/metrics/README.md` - Shared utilities documentation
- `docs/ANALYTICS_EPIC_GUIDE.md` - Implementation guide
- `scripts/setup_analytics.py` - Interactive configuration wizard (Phase 6)
