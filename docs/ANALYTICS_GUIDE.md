## Analytics Guide

# Claude Recall Analytics System

Comprehensive monitoring, quality scoring, and reporting for your recall system.

## Overview

The recall analytics system provides four integrated layers:

1. **Telemetry** - Automatic tracking of all recall operations
2. **Impact Analysis** - Measures how recalled context affects conversation quality
3. **Quality Scoring** - LLM-based evaluation of search results
4. **Quality Checks** - Automated health monitoring

Together, these provide complete visibility into your recall system's performance.

## Quick Start

### 1. Enable Analytics

Analytics are controlled via `config/analytics_config.json`. All features are enabled by default:

```bash
# Check configuration
cat config/analytics_config.json
```

### 2. Use Recall Normally

Analytics run automatically in the background. Just use recall as normal:

```bash
# Search operations are automatically tracked
python3 scripts/smart_recall.py "how do I authenticate users?"
```

### 3. Generate Reports

View analytics anytime:

```bash
# Quick summary (last 7 days)
python3 scripts/generate_recall_report.py --summary

# Full report (last 30 days)
python3 scripts/generate_recall_report.py --period 30

# Export to file
python3 scripts/generate_recall_report.py --output report.md
```

### 4. Run Quality Checks

Monitor system health:

```bash
# Run all checks
python3 scripts/run_quality_checks.py

# Quick check (skips expensive tests)
python3 scripts/run_quality_checks.py --quick
```

## Features

### Telemetry Collection

**What it tracks:**
- Every search query and its parameters
- Search results (count, scores, sessions found)
- Performance metrics (latency breakdown, cache hits)
- System state (index size, memory usage)

**Log file:** `~/.claude/context/sessions/recall_analytics.jsonl`

**Configuration:**
```json
{
  "telemetry": {
    "enabled": true,
    "log_path": ".claude/context/sessions/recall_analytics.jsonl",
    "sampling_rate": 1.0,
    "batch_size": 10,
    "pii_redaction": true
  }
}
```

### Impact Analysis

**What it measures:**
- Explicit citations (direct references to recalled context)
- Implicit usage (conceptual reuse without citation)
- Continuity score (how well context flows between sessions)
- Efficiency gains (time saved by not repeating work)

**Log file:** `~/.claude/context/sessions/context_impact.jsonl`

**Runs automatically:** After each session ends (via auto_capture.py)

**Configuration:**
```json
{
  "impact_analysis": {
    "enabled": true,
    "log_path": ".claude/context/sessions/context_impact.jsonl",
    "auto_analyze_on_session_end": true,
    "min_recall_events": 1
  }
}
```

### Quality Scoring

**What it evaluates:**
- Relevance: How well results match the query
- Coverage: Completeness of information
- Specificity: Level of detail provided

**Methods:**
- LLM-based (Claude Haiku - most accurate)
- Heuristic fallback (zero-cost backup)

**Log file:** `~/.claude/context/sessions/quality_scores.jsonl`

**Configuration:**
```json
{
  "quality_scoring": {
    "enabled": false,
    "log_path": ".claude/context/sessions/quality_scores.jsonl",
    "api_key_env_var": "ANTHROPIC_API_KEY",
    "model": "claude-haiku-4.5-20251001",
    "sampling_rate": 0.1,
    "monthly_budget_usd": 5.0,
    "fallback_to_heuristic": true
  }
}
```

**Enable quality scoring:**
```bash
# Set API key
export ANTHROPIC_API_KEY="your-api-key"

# Enable in config
# Set quality_scoring.enabled to true in analytics_config.json
```

**Cost:** ~$0.0004 per evaluation with 10% sampling

### Quality Checks

**7 automated checks:**
1. **LowRelevanceCheck** - Detects poor quality scores
2. **NoResultsCheck** - Monitors empty search results
3. **HighLatencyCheck** - Identifies performance degradation
4. **IndexHealthCheck** - Validates index integrity
5. **EmbeddingDriftCheck** - Detects model changes
6. **FalsePositiveCheck** - Finds irrelevant results
7. **UsageAnomalyCheck** - Detects unusual patterns

**Run checks:**
```bash
# All checks
python3 scripts/run_quality_checks.py

# Specific check
python3 scripts/run_quality_checks.py --check HighLatencyCheck

# Quick mode (skip expensive checks)
python3 scripts/run_quality_checks.py --quick
```

**Schedule checks:** See [Quality Checks Scheduling Guide](QUALITY_CHECKS_SCHEDULING.md)

## Usage Examples

### Generate Reports

```bash
# Quick summary
python3 scripts/generate_recall_report.py --summary

# Full 30-day report
python3 scripts/generate_recall_report.py --period 30

# JSON export
python3 scripts/generate_recall_report.py --format json --output metrics.json

# HTML report
python3 scripts/generate_recall_report.py --format html --output report.html

# Email-friendly format
python3 scripts/generate_recall_report.py --format email --output email.md

# Specific sections only
python3 scripts/generate_recall_report.py --sections usage,quality,performance
```

### Run Quality Checks

```bash
# All checks
python3 scripts/run_quality_checks.py

# Specific check
python3 scripts/run_quality_checks.py --check HighLatencyCheck

# Multiple checks
python3 scripts/run_quality_checks.py --check Check1 --check Check2

# Quick mode
python3 scripts/run_quality_checks.py --quick

# Check last 48 hours
python3 scripts/run_quality_checks.py --hours 48

# Verbose output
python3 scripts/run_quality_checks.py --verbose

# With email alerts
python3 scripts/run_quality_checks.py --email admin@company.com

# Monitor mode (continuous)
python3 scripts/run_quality_checks.py --monitor --interval 3600
```

### Query Logs

```bash
# View recent telemetry
tail -20 ~/.claude/context/sessions/recall_analytics.jsonl | jq .

# Count searches by mode
cat ~/.claude/context/sessions/recall_analytics.jsonl | \
  jq -r 'select(.event_type=="search_completed") | .search_config.mode_resolved' | \
  sort | uniq -c

# Average latency
cat ~/.claude/context/sessions/recall_analytics.jsonl | \
  jq -r 'select(.event_type=="search_completed") | .performance.total_latency_ms' | \
  awk '{sum+=$1; count++} END {print sum/count "ms"}'

# View quality scores
cat ~/.claude/context/sessions/quality_scores.jsonl | \
  jq -r '.scores.overall'

# View impact analysis
cat ~/.claude/context/sessions/context_impact.jsonl | \
  jq -r '"\(.session_id): \(.continuity_score) continuity, \(.efficiency_metrics.estimated_time_saved_minutes)min saved"'
```

## Configuration

### Complete Configuration Example

```json
{
  "telemetry": {
    "enabled": true,
    "log_path": ".claude/context/sessions/recall_analytics.jsonl",
    "sampling_rate": 1.0,
    "batch_size": 10,
    "pii_redaction": true
  },
  "impact_analysis": {
    "enabled": true,
    "log_path": ".claude/context/sessions/context_impact.jsonl",
    "auto_analyze_on_session_end": true,
    "min_recall_events": 1
  },
  "quality_scoring": {
    "enabled": false,
    "log_path": ".claude/context/sessions/quality_scores.jsonl",
    "api_key_env_var": "ANTHROPIC_API_KEY",
    "model": "claude-haiku-4.5-20251001",
    "sampling_rate": 0.1,
    "monthly_budget_usd": 5.0,
    "fallback_to_heuristic": true
  },
  "quality_checks": {
    "enabled": true,
    "schedule": "0 8 * * *",
    "LowRelevanceCheck": {
      "low_score_threshold": 0.4,
      "warning_percent": 0.2
    },
    "NoResultsCheck": {
      "no_results_threshold_percent": 0.3
    },
    "HighLatencyCheck": {
      "high_latency_ms": 1000,
      "warning_percent": 0.1
    },
    "UsageAnomalyCheck": {
      "spike_threshold": 3.0
    },
    "alerts": {
      "email_enabled": false,
      "slack_webhook_url": "",
      "smtp": {
        "server": "",
        "port": 587,
        "use_tls": true,
        "username": "",
        "password": "",
        "from_address": ""
      }
    }
  },
  "reporting": {
    "enabled": true,
    "period_days": 30,
    "format": "markdown"
  }
}
```

### Environment Variables

```bash
# API key for quality scoring
export ANTHROPIC_API_KEY="your-api-key-here"

# Override log paths (optional)
export RECALL_ANALYTICS_LOG="custom/path/analytics.jsonl"
export RECALL_QUALITY_LOG="custom/path/quality.jsonl"
export RECALL_IMPACT_LOG="custom/path/impact.jsonl"
```

## Troubleshooting

### No Data in Reports

**Problem:** Reports show "No search activity"

**Solutions:**
1. Check if telemetry is enabled: `grep "enabled.*true" config/analytics_config.json`
2. Verify log files exist: `ls -l ~/.claude/context/sessions/*.jsonl`
3. Check if searches are being performed: `python3 scripts/search_index.py --query "test"`
4. Look for errors in logs: `grep -i error ~/.claude/context/sessions/*.jsonl`

### Quality Scoring Not Working

**Problem:** Quality scores log is empty

**Solutions:**
1. Check if enabled: `jq '.quality_scoring.enabled' config/analytics_config.json`
2. Verify API key is set: `echo $ANTHROPIC_API_KEY`
3. Check sampling rate: `jq '.quality_scoring.sampling_rate' config/analytics_config.json`
4. Review budget: Quality scoring stops if monthly budget exceeded

### High Costs

**Problem:** Quality scoring costs too high

**Solutions:**
1. Reduce sampling rate: Set `quality_scoring.sampling_rate` to 0.05 (5%)
2. Lower monthly budget: Set `quality_scoring.monthly_budget_usd` to 2.0
3. Use heuristic fallback: Set `quality_scoring.fallback_to_heuristic` to true
4. Disable quality scoring: Set `quality_scoring.enabled` to false

### Quality Checks Failing

**Problem:** Many checks show warnings/errors

**Solutions:**
1. Review specific check details: Run with `--verbose`
2. Adjust thresholds in config if too strict
3. Check if index needs updating: `python3 scripts/build_index.py`
4. Verify sufficient data exists: Check log files have recent entries

### Performance Issues

**Problem:** Analytics causing slowdowns

**Solutions:**
1. Reduce telemetry sampling: Set `telemetry.sampling_rate` to 0.5
2. Disable quality scoring: Most expensive feature
3. Reduce batch size: Set `telemetry.batch_size` to 5
4. Disable impact analysis if not needed

## Best Practices

### 1. Start Simple

Enable features incrementally:
1. Start with telemetry only
2. Add impact analysis after a week
3. Enable quality scoring at 10% sampling
4. Set up quality checks last

### 2. Monitor Costs

Quality scoring is the only feature with API costs:
- Default: ~$0.50/month (10% sampling)
- Check monthly spend: `jq '.costs.total_cost_usd' report.json`
- Adjust sampling rate to control costs

### 3. Tune Thresholds

Default thresholds may not fit your usage:
- Run system for a week
- Review baseline metrics in reports
- Adjust check thresholds in config
- Reduce false positives

### 4. Regular Reviews

Set up regular reporting:
- Daily: Quick summary via cron
- Weekly: Full report review
- Monthly: Comprehensive analysis

### 5. Act on Insights

Analytics are only useful if you act on them:
- Low quality scores? Review query patterns
- High latency? Consider index optimization
- Low continuity? Improve recall queries
- No results? Expand indexed content

## See Also

- [Telemetry Schema Reference](TELEMETRY_SCHEMA.md)
- [Quality Checks Scheduling](QUALITY_CHECKS_SCHEDULING.md)
- [Configuration Reference](ANALYTICS_CONFIG.md)
- [Main README](../README.md)
