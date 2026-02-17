# Quality Checks Guide

Complete guide to understanding, interpreting, and tuning the 7 automated quality checks.

## Overview

Quality checks monitor your recall system's health automatically, detecting:
- Poor search quality
- Performance degradation
- Index problems
- Usage anomalies

## The 7 Quality Checks

### 1. LowRelevanceCheck

**What it does:** Detects searches with low quality scores.

**When it alerts:**
- When >20% of searches score below 0.4

**What it means:**
- Search results aren't matching queries well
- Index content may be stale or irrelevant
- Query formulation needs improvement

**Example Alert:**
```
⚠️ LowRelevanceCheck
5 of 20 searches (25.0%) have low quality scores (<0.4)
```

**Thresholds:**
```json
{
  "LowRelevanceCheck": {
    "low_score_threshold": 0.4,
    "warning_percent": 0.2
  }
}
```

**Tuning:**
- **Increase `low_score_threshold`** (0.5) for stricter standards
- **Decrease `warning_percent`** (0.1) to alert on fewer failures
- **Decrease `low_score_threshold`** (0.3) if getting false positives

**Action Items:**
1. Review sample low-scoring queries
2. Check if index needs updating: `python3 scripts/build_index.py`
3. Improve query formulation
4. Add more relevant sessions to index

---

### 2. NoResultsCheck

**What it does:** Monitors searches returning no results.

**When it alerts:**
- When >30% of searches return empty

**What it means:**
- Queries don't match indexed content
- Index may be too small
- Search is too restrictive

**Example Alert:**
```
⚠️ NoResultsCheck
8 of 25 searches (32.0%) returned no results
```

**Thresholds:**
```json
{
  "NoResultsCheck": {
    "no_results_threshold_percent": 0.3
  }
}
```

**Tuning:**
- **Increase threshold** (0.4) if empty results are often valid
- **Decrease threshold** (0.2) for stricter monitoring

**Action Items:**
1. Review queries with no results
2. Expand indexed session content
3. Use broader search terms
4. Check if top_k is too low

---

### 3. HighLatencyCheck

**What it does:** Identifies performance degradation.

**When it alerts:**
- When >10% of searches exceed 1000ms latency

**What it means:**
- Index too large
- System under load
- Disk I/O bottleneck

**Example Alert:**
```
⚠️ HighLatencyCheck
5 searches (12.5%) exceeded 1000ms latency
Avg: 850ms, P95: 1450ms
```

**Thresholds:**
```json
{
  "HighLatencyCheck": {
    "high_latency_ms": 1000,
    "warning_percent": 0.1
  }
}
```

**Tuning:**
- **Increase latency threshold** (1500) for slower systems
- **Decrease threshold** (500) for strict performance requirements
- **Increase warning_percent** (0.2) to tolerate occasional slowness

**Action Items:**
1. Enable index caching
2. Reduce index size (archive old sessions)
3. Optimize search parameters
4. Check system resources (CPU, memory, disk)

---

### 4. IndexHealthCheck

**What it does:** Validates index integrity.

**When it alerts:**
- Index file missing
- Index corrupted
- >10% sessions lack embeddings

**What it means:**
- Index needs rebuilding
- Embedding generation failed
- File corruption

**Example Alert:**
```
⚠️ IndexHealthCheck
15 of 100 sessions (15.0%) lack embeddings
```

**Thresholds:**
```json
{
  "IndexHealthCheck": {
    "index_path": "~/.claude/context/sessions/index.json"
  }
}
```

**Tuning:**
- **Set custom index_path** if using non-default location
- **Use `--sessions-dir` flag** to check project-specific indexes

**Checking Project-Specific Sessions:**
```bash
# Check a specific project's sessions
python3 scripts/run_quality_checks.py \
  --sessions-dir ~/PycharmProjects/myproject/.claude/context/sessions

# This automatically sets the correct index path for IndexHealthCheck
```

**Action Items:**
1. Rebuild index: `python3 scripts/build_index.py`
2. Check embedding API availability
3. Verify index file permissions
4. Review embedding generation logs

---

### 5. EmbeddingDriftCheck

**What it does:** Detects embedding model changes.

**When it alerts:**
- Multiple different embedding dimensions detected

**What it means:**
- Embedding model was changed
- Inconsistent embeddings in index
- Semantic search may be degraded

**Example Alert:**
```
⚠️ EmbeddingDriftCheck
Detected 2 different embedding dimensions: {384, 768}
```

**Thresholds:**
- None (structural check)

**Tuning:**
- Not tunable (detects incompatible embeddings)

**Action Items:**
1. Decide on embedding model to use
2. Rebuild entire index with chosen model
3. Don't mix different embedding dimensions

---

### 6. FalsePositiveCheck

**What it does:** Finds searches with high quality but low actual usage.

**When it alerts:**
- >3 instances of high quality score but low continuity

**What it means:**
- Quality scorer and actual usage disagree
- Results look good but aren't useful
- Need to tune quality scoring

**Example Alert:**
```
⚠️ FalsePositiveCheck
Detected 5 potential false positives
(high quality: 0.8+, low continuity: <0.3)
```

**Thresholds:**
```json
{
  "FalsePositiveCheck": {
    "high_quality_threshold": 0.7,
    "low_continuity_threshold": 0.3
  }
}
```

**Tuning:**
- **Increase quality_threshold** (0.8) for stricter detection
- **Increase continuity_threshold** (0.4) if too sensitive

**Action Items:**
1. Review sample false positive queries
2. Adjust quality scoring prompts
3. Tune search ranking algorithm
4. Consider impact analysis methodology

---

### 7. UsageAnomalyCheck

**What it does:** Detects unusual usage patterns.

**When it alerts:**
- Usage spike >3x average

**What it means:**
- Sudden increase in search volume
- Possible automated/bot traffic
- Or legitimate increased usage

**Example Alert:**
```
⚠️ UsageAnomalyCheck
Usage spike detected: 45 searches in one hour (avg: 12)
Spike ratio: 3.8x
```

**Thresholds:**
```json
{
  "UsageAnomalyCheck": {
    "spike_threshold": 3.0
  }
}
```

**Tuning:**
- **Increase threshold** (5.0) if usage varies naturally
- **Decrease threshold** (2.0) for stricter anomaly detection

**Action Items:**
1. Verify spike is legitimate
2. Check for automation/scripts
3. Review what triggered increased usage
4. Scale resources if needed

---

## Running Checks

### Basic Usage

```bash
# Run all checks
python3 scripts/run_quality_checks.py

# Quick mode (skip expensive checks)
python3 scripts/run_quality_checks.py --quick

# Verbose output
python3 scripts/run_quality_checks.py --verbose

# Check specific hours
python3 scripts/run_quality_checks.py --hours 48

# Check project-specific sessions (not global)
python3 scripts/run_quality_checks.py --sessions-dir ~/path/to/project/.claude/context/sessions
```

### Check Specific Issues

```bash
# Run single check
python3 scripts/run_quality_checks.py --check HighLatencyCheck

# Run multiple checks
python3 scripts/run_quality_checks.py \
  --check HighLatencyCheck \
  --check NoResultsCheck
```

### With Alerts

```bash
# Email alerts
python3 scripts/run_quality_checks.py --email admin@company.com

# Suppress alerts (log only)
python3 scripts/run_quality_checks.py --no-alerts
```

## Interpreting Results

### Status Codes

- ✓ **pass** - No issues detected
- ⚠️ **warning** - Minor issues, review recommended
- ✗ **error** - Critical issues, immediate action needed

### Summary Metrics

```
Total checks: 7
Passed: 5
Warnings: 2
Errors: 0
Pass rate: 71.4%
```

**Pass rate interpretation:**
- **100%** - Excellent, system healthy
- **80-99%** - Good, minor tuning recommended
- **60-79%** - Fair, review and address warnings
- **<60%** - Poor, immediate attention needed

### Sample Output

```
============================================================
Quality Check Results
============================================================

Total checks: 7
Passed: 5
Warnings: 2
Errors: 0
Pass rate: 71.4%

✓ LowRelevanceCheck: Quality scores within acceptable range
✓ NoResultsCheck: Empty result rate acceptable (15.0%)
⚠ HighLatencyCheck: 5 searches (10.2%) exceeded 1000ms latency
✓ IndexHealthCheck: Index healthy: 100 sessions indexed
✓ EmbeddingDriftCheck: Embedding dimensions consistent: 384
✓ FalsePositiveCheck: False positive rate acceptable (2 detected)
⚠ UsageAnomalyCheck: Usage spike detected: 45 searches/hour (avg: 12)
```

## Tuning Thresholds

### Start Conservative

Begin with loose thresholds to understand baseline:

```json
{
  "LowRelevanceCheck": {
    "low_score_threshold": 0.3,
    "warning_percent": 0.3
  },
  "HighLatencyCheck": {
    "high_latency_ms": 2000,
    "warning_percent": 0.2
  }
}
```

### Tighten Gradually

After a week, review data and tighten:

```json
{
  "LowRelevanceCheck": {
    "low_score_threshold": 0.4,
    "warning_percent": 0.2
  },
  "HighLatencyCheck": {
    "high_latency_ms": 1000,
    "warning_percent": 0.1
  }
}
```

### Environment-Specific

Different environments need different thresholds:

**Development:**
```json
{
  "HighLatencyCheck": {
    "high_latency_ms": 2000,
    "warning_percent": 0.3
  }
}
```

**Production:**
```json
{
  "HighLatencyCheck": {
    "high_latency_ms": 500,
    "warning_percent": 0.05
  }
}
```

## Responding to Alerts

### Warning Response Time

- **Low Relevance** - Review within 1 day
- **No Results** - Review within 1 day
- **High Latency** - Review within 4 hours
- **Index Health** - Review within 1 hour
- **Embedding Drift** - Review within 1 day
- **False Positives** - Review within 1 week
- **Usage Anomaly** - Review within 1 hour

### Error Response Time

All errors should be addressed immediately (within 1 hour).

### Escalation

Configure alerts to escalate:

```json
{
  "alerts": {
    "email_enabled": true,
    "slack_webhook_url": "https://hooks.slack.com/...",
    "escalation": {
      "errors_notify_immediately": true,
      "warnings_batch": true,
      "warnings_batch_hours": 24
    }
  }
}
```

## Automated Remediation

Some issues can be automatically fixed:

### High Latency
```bash
# Clear cache and rebuild
rm ~/.claude/context/sessions/index_cache.json
python3 scripts/build_index.py --optimize
```

### Index Health
```bash
# Rebuild index
python3 scripts/build_index.py --force
```

### No Results
```bash
# Expand index
python3 scripts/build_index.py --include-archived
```

## Best Practices

1. **Run checks regularly** - At least daily
2. **Review trends** - Don't just look at latest check
3. **Tune thresholds** - Adjust for your environment
4. **Act on alerts** - Don't ignore warnings
5. **Document changes** - Track threshold adjustments

## FAQ

**Q: How often should checks run?**
A: Daily for development, hourly for production.

**Q: What's an acceptable pass rate?**
A: 80%+ is good. 100% is ideal but not always realistic.

**Q: Should I fix every warning?**
A: Review all warnings. Fix critical path issues first.

**Q: Can I disable specific checks?**
A: Yes, don't include them in --check parameter.

**Q: How do I reduce false positives?**
A: Tune thresholds based on your baseline metrics.

## See Also

- [Analytics Guide](ANALYTICS_GUIDE.md)
- [Quality Checks Scheduling](QUALITY_CHECKS_SCHEDULING.md)
- [Configuration Reference](ANALYTICS_CONFIG.md)
