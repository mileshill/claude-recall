# Transcript Excerpt Feature - Evaluation Plan

## Overview

Evaluating the impact of automatically showing transcript excerpts in recall output.

**Commit**: bf16c4f
**Date**: 2026-02-17
**Change**: Recall now includes actual conversation excerpts from .jsonl transcripts, not just metadata summaries

---

## Hypothesis

**Before**: Agents only saw metadata (summaries, topics) and often failed to access actual conversation content.

**After**: Agents see query-relevant conversation excerpts automatically, improving context recall quality.

**Expected Outcomes**:
1. ✅ Higher conversation continuity scores
2. ✅ Better quality ratings from LLM evaluator
3. ✅ Reduced "empty recall" patterns (agent can't find relevant info)
4. ⚠️ Slightly increased latency (excerpt extraction overhead)
5. ✅ More effective recall usage

---

## Metrics to Track

### A. Excerpt-Specific Metrics (NEW)

These need to be added to telemetry:

```json
{
  "event_type": "smart_recall_completed",
  "excerpts": {
    "enabled": true,
    "sessions_with_excerpts": 2,
    "total_sessions": 3,
    "excerpt_extraction_ms": 145,
    "total_excerpt_chars": 1500,
    "avg_excerpt_chars_per_session": 750,
    "excerpts_found": [
      {
        "session_id": "2026-02-17_031626",
        "excerpt_count": 2,
        "message_indices": [1, 22],
        "char_count": 800
      }
    ]
  }
}
```

### B. Existing Metrics to Monitor

1. **Quality Scores** (quality_scores.jsonl)
   - `scores.relevance` - Are excerpts more relevant?
   - `scores.completeness` - Do excerpts provide better completeness?
   - `scores.overall` - Overall quality improvement?

2. **Impact Analysis** (context_impact.jsonl)
   - `continuity_score` - Better conversation continuity?
   - `context_value` - Higher value from recalled context?
   - `time_saved_estimated` - More time saved?

3. **Performance** (recall_analytics.jsonl)
   - `performance.total_latency_ms` - Latency increase?
   - `performance.breakdown.excerpt_extraction_ms` - New timing
   - `results.count` - Same number of results?

4. **Usage Patterns**
   - Recall frequency (more useful = more usage?)
   - Session reuse (are old sessions more valuable now?)
   - False positive rate (excerpts reduce irrelevant results?)

---

## Evaluation Methodology

### Phase 1: Baseline Collection (DONE)

✅ Existing data without excerpts:
- 26 recall searches performed
- 15 sessions in corpus
- Average relevance: varies by query
- Quality scoring: enabled but limited data

### Phase 2: Feature Deployment (DONE)

✅ Commit bf16c4f deployed with:
- Automatic excerpt extraction
- Query-based message matching
- Smart truncation (800 chars per excerpt)

### Phase 3: Data Collection (IN PROGRESS)

**Duration**: 1 week (2026-02-17 to 2026-02-24)

**Actions**:
1. Use recall naturally in different projects
2. Capture sessions with SessionEnd hook
3. Quality scoring will evaluate results
4. Impact analysis will track continuity

**Expected Data Volume**:
- ~10-20 recall operations
- ~5-10 new sessions captured
- ~10-20 quality evaluations

### Phase 4: Analysis (PENDING)

**Compare**:

```bash
# Before excerpts (baseline)
python3 scripts/generate_recall_report.py --period 7 --before 2026-02-17

# After excerpts (treatment)
python3 scripts/generate_recall_report.py --period 7 --after 2026-02-17

# Side-by-side comparison
python3 scripts/compare_recall_periods.py \
  --before 2026-02-10:2026-02-17 \
  --after 2026-02-17:2026-02-24 \
  --output excerpt_impact_report.md
```

---

## Success Criteria

### Must Have (P0)
- ✅ Excerpts successfully extracted and shown
- ✅ No performance degradation >200ms
- ✅ No crashes or errors in excerpt extraction

### Should Have (P1)
- 📊 Quality scores improve by ≥10%
- 📊 Continuity scores improve by ≥15%
- 📊 Overall recall satisfaction increases

### Nice to Have (P2)
- 📊 Recall usage increases (feature is more useful)
- 📊 Time saved estimate increases
- 📊 False positive rate decreases

---

## Implementation TODOs

### 1. Add Excerpt Telemetry

Modify `smart_recall.py` to track excerpt extraction:

```python
# After formatting output, track excerpt stats
excerpt_stats = {
    "enabled": include_excerpts,
    "sessions_with_excerpts": 0,
    "total_sessions": len(final_results),
    "excerpt_extraction_ms": 0,
    # ... more stats
}

collector.update_event(event_id, {"excerpts": excerpt_stats})
```

### 2. Add Comparison Report Script

Create `scripts/compare_recall_periods.py` to generate before/after reports:

```bash
python3 scripts/compare_recall_periods.py \
  --before 2026-02-10:2026-02-17 \
  --after 2026-02-17:2026-02-24
```

### 3. Update Quality Checks

Add new check: `ExcerptQualityCheck`
- Monitors excerpt relevance
- Detects if excerpts are too long/short
- Validates extraction performance

### 4. Dashboard Visualization

Add to report:
- Excerpt usage chart (how often shown)
- Excerpt length distribution
- Performance impact graph
- Quality score comparison (before/after)

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Excerpt extraction too slow | High latency | Cache transcripts, optimize search |
| Excerpts not relevant | Poor quality | Improve query term matching |
| Too much output | Agent overwhelm | Tune max_chars, max_excerpts |
| Missing transcripts | Feature breaks | Graceful fallback to metadata only |

---

## Next Steps

1. **Immediate (Today)**:
   - ✅ Feature deployed
   - ✅ Basic testing completed
   - ⏳ Add excerpt telemetry
   - ⏳ Create comparison script

2. **This Week**:
   - Use recall naturally in daily work
   - Collect quality/impact data
   - Monitor for errors/issues

3. **Next Week**:
   - Run analysis reports
   - Compare before/after metrics
   - Decide: keep, tune, or rollback

---

## Questions to Answer

1. **Does showing excerpts improve quality scores?**
   - Metric: `quality_scores.overall` before vs. after

2. **Do excerpts improve conversation continuity?**
   - Metric: `context_impact.continuity_score` before vs. after

3. **What's the performance cost?**
   - Metric: `performance.total_latency_ms` increase

4. **Are excerpts actually used by agents?**
   - Qualitative: review session transcripts to see if agents reference excerpt content

5. **Do excerpts reduce false positives?**
   - Metric: `FalsePositiveCheck` rate before vs. after

6. **What's the optimal excerpt length?**
   - Experiment: 400 vs 800 vs 1200 chars
   - Measure: quality scores vs. latency

---

## Conclusion

This evaluation plan provides a systematic approach to measuring the impact of
the transcript excerpt feature. The key is collecting enough data over 1 week,
then comparing metrics before/after deployment.

**Status**: Phase 3 (Data Collection) - In Progress
