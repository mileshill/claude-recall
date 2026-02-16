# Recall Analytics System - Epic Guide

**Epic ID**: `recall-1`
**Status**: Open
**Total Duration**: 8 weeks
**Total Tasks**: 41 (29 implementation + 12 phase/epic markers)

## Quick Start for Agents

```bash
# View available work
bd ready

# View epic structure
bd show recall-1

# View specific phase
bd show recall-1.1  # Phase 0: Foundation
bd show recall-1.2  # Phase 1: Telemetry
# etc.

# Claim a task
bd update <task-id> --status in_progress --assignee <your-name>

# Complete a task
bd close <task-id>

# View dependencies
bd show <task-id>
```

## Epic Structure

```
recall-1 (Epic) - Implement Recall Analytics System
├─ recall-1.1 (Phase 0) - Foundation & Shared Infrastructure [P0, Week 1]
│  ├─ recall-1.1.1 - Create shared utilities module (metrics/)
│  ├─ recall-1.1.2 - Create analytics_config.json with defaults
│  ├─ recall-1.1.3 - Fix existing bugs (timezone, numpy, division by zero)
│  └─ recall-1.1.4 - Create foundation documentation
│
├─ recall-1.2 (Phase 1) - Telemetry System [P0, Week 2] ← depends on recall-1.1
│  ├─ recall-2 - Create telemetry module structure
│  ├─ recall-3 - Integrate telemetry into search_index.py
│  ├─ recall-4 - Integrate telemetry into smart_recall.py
│  └─ recall-5 - Create telemetry tests and validation
│
├─ recall-1.3 (Phase 2) - Context Impact Analysis [P0, Week 3] ← depends on recall-1.2
│  ├─ recall-6 - Create impact analysis module structure
│  ├─ recall-7 - Integrate impact analysis with auto_capture.py
│  └─ recall-8 - Create impact analysis tests
│
├─ recall-1.4 (Phase 3) - Semantic Quality Scoring [P1, Week 4] ← depends on recall-1.2
│  ├─ recall-9 - Create quality scoring module structure
│  ├─ recall-10 - Integrate quality scoring with search
│  ├─ recall-11 - Implement cost management and validation
│  └─ recall-12 - Create quality scoring tests
│
├─ recall-1.5 (Phase 4) - Dashboard & Reporting [P1, Week 5] ← depends on recall-1.3
│  ├─ recall-13 - Create reporting module structure
│  ├─ recall-14 - Create report templates
│  ├─ recall-15 - Create CLI report generator
│  └─ recall-16 - Create reporting tests
│
├─ recall-1.6 (Phase 5) - Automatic Quality Checks [P1, Week 6] ← depends on recall-1.5
│  ├─ recall-17 - Create quality checks module
│  ├─ recall-18 - Create CLI quality check runner
│  ├─ recall-19 - Set up scheduled execution
│  ├─ recall-20 - Implement alert integration
│  └─ recall-21 - Create quality check tests
│
├─ recall-1.7 (Phase 6) - Integration & Polish [P1, Week 7] ← depends on recall-1.6
│  ├─ recall-22 - Conduct end-to-end integration testing
│  ├─ recall-23 - Create comprehensive documentation
│  ├─ recall-24 - Create configuration wizard
│  └─ recall-25 - Handle migration and upgrade
│
└─ recall-1.8 (Phase 7) - Optimization & Monitoring [P2, Week 8] ← depends on recall-1.7
   ├─ recall-26 - Implement performance optimizations
   ├─ recall-27 - Create monitoring dashboard
   ├─ recall-28 - Implement log rotation and cleanup
   └─ recall-29 - Complete production readiness checklist
```

## Phase Dependencies

```
Phase 0 (Foundation) → Phase 1 (Telemetry)
                       ↓
                       Phase 2 (Impact) ← Phase 3 (Quality Scoring)
                       ↓
                       Phase 4 (Reporting)
                       ↓
                       Phase 5 (Quality Checks)
                       ↓
                       Phase 6 (Integration)
                       ↓
                       Phase 7 (Optimization)
```

**Parallelization Opportunities**:
- Phase 2 and Phase 3 can run in parallel after Phase 1
- Within each phase, many tasks can be parallelized (see task details)

## Task Estimates by Phase

| Phase | Tasks | Total Estimate | Critical Path |
|-------|-------|----------------|---------------|
| Phase 0 | 4 | 850 min (14h) | Yes |
| Phase 1 | 4 | 840 min (14h) | Yes |
| Phase 2 | 3 | 780 min (13h) | Yes |
| Phase 3 | 4 | 750 min (12.5h) | No (parallel with Phase 2) |
| Phase 4 | 4 | 870 min (14.5h) | Yes |
| Phase 5 | 5 | 1020 min (17h) | Yes |
| Phase 6 | 4 | 1140 min (19h) | Yes |
| Phase 7 | 4 | 690 min (11.5h) | No (optimization) |
| **Total** | **32** | **~115 hours** | **~100 hours** |

## References for Each Phase

### Phase 0: Foundation
**Key Documents**:
- This directory's implementation plan (in analysis notes)
- `scripts/metrics/` - will contain all shared utilities
- `config/analytics_config.json` - configuration schema

**External References**:
- Existing `scripts/redact_secrets.py` - for PII redaction patterns
- Existing `scripts/search_index.py` - to understand current architecture
- Python fcntl documentation - for file locking

### Phase 1: Telemetry
**Key Documents**:
- Implementation plan Phase 1 section
- `scripts/telemetry/schema.py` - event schemas (to be created)
- Existing `scripts/search_index.py` - integration target
- Existing `scripts/smart_recall.py` - integration target

**Log Output**: `.claude/context/sessions/recall_analytics.jsonl`

### Phase 2: Impact Analysis
**Key Documents**:
- Implementation plan Phase 2 section and Option 3 detailed analysis
- `scripts/impact_analysis/` - module to create
- Existing `scripts/auto_capture.py` - integration target
- Existing transcript format (`.claude/context/sessions/*_transcript.jsonl`)

**Log Output**: `.claude/context/sessions/context_impact.jsonl`

### Phase 3: Quality Scoring
**Key Documents**:
- Implementation plan Phase 3 section and Option 5 detailed analysis
- Anthropic API documentation (claude-3-haiku pricing)
- `scripts/quality_scoring/` - module to create

**Cost Target**: ~$0.12/month with 10% sampling

**Log Output**: `.claude/context/sessions/quality_scores.jsonl`

### Phase 4: Reporting
**Key Documents**:
- Implementation plan Phase 4 section and Option 6 report structure
- Jinja2 template documentation
- All log files from Phases 1-3 (data sources)

**Deliverable**: `scripts/generate_recall_report.py` CLI tool

### Phase 5: Quality Checks
**Key Documents**:
- Implementation plan Phase 5 section and Option 7 detailed checks
- `scripts/quality_checks/checks.py` - 7 check implementations
- All log files (data sources for checks)

**Checks**:
1. LowRelevanceCheck - avg score < 0.4
2. NoResultsCheck - no-results rate > 15%
3. HighLatencyCheck - P95 > 100ms
4. IndexHealthCheck - missing embeddings, stale sessions
5. EmbeddingDriftCheck - semantic quality degrading
6. FalsePositiveCheck - quality scores < 2.5
7. UsageAnomalyCheck - unusual activity (>3 std dev)

**Log Output**: `.claude/context/sessions/quality_check_log.jsonl`

### Phase 6: Integration
**Key Documents**:
- Implementation plan Phase 6 section
- All previous phases (integration testing)
- Create `docs/ANALYTICS_GUIDE.md` - comprehensive guide
- Create `docs/TELEMETRY_SCHEMA.md` - event schemas
- Create `docs/QUALITY_CHECKS_GUIDE.md` - check reference

### Phase 7: Optimization
**Key Documents**:
- Implementation plan Phase 7 section
- Performance benchmarks from Phase 6 testing
- `scripts/analytics_status.py` - monitoring dashboard
- `docs/PRODUCTION_READINESS.md` - checklist

## Critical Paths

**Must Complete in Order**:
1. Phase 0 (Foundation) - everything depends on this
2. Phase 1 (Telemetry) - data collection foundation
3. Phase 2 (Impact) OR Phase 3 (Quality) - can be parallel
4. Phase 4 (Reporting) - needs data from 1-3
5. Phase 5 (Quality Checks) - needs all data sources
6. Phase 6 (Integration) - ties everything together
7. Phase 7 (Optimization) - final polish

**Can Be Parallelized**:
- Phase 2 and Phase 3 (both depend only on Phase 1)
- Within phases, many tasks are independent (check task descriptions)

## Work Distribution Strategies

### Strategy 1: Sequential Team (1-2 agents)
- Complete Phase 0 → Phase 1 → Phase 2 → etc.
- Ensures coherence and understanding
- Total time: ~8 weeks

### Strategy 2: Parallel Team (3-4 agents)
- Agent 1: Phase 0 → Phase 1 → Phase 2 → Phase 4
- Agent 2: Wait for Phase 1 → Phase 3 (parallel with Phase 2)
- Agent 3: Wait for Phase 4 → Phase 5 → Phase 6
- Agent 4: Phase 7 (optimization can be delayed)
- Total time: ~6 weeks

### Strategy 3: Swarm (5+ agents)
- Multiple agents on Phase 0 tasks (can parallelize)
- Split Phase 1 tasks by module
- After Phase 1, full parallelization
- Total time: ~4-5 weeks (with coordination overhead)

## Key Integration Points

**Files Modified Across Phases**:
1. `scripts/search_index.py` - Phases 1, 3 (add telemetry, quality scoring)
2. `scripts/smart_recall.py` - Phase 1 (add telemetry)
3. `scripts/auto_capture.py` - Phase 2 (add impact analysis)
4. `config/analytics_config.json` - All phases (configuration)

**Coordination Required**:
- Ensure import statements don't conflict
- Coordinate on configuration schema updates
- Share metric calculation functions (use Phase 0 shared utilities)

## Testing Strategy

**Per Phase**:
- Unit tests for each module
- Integration tests for cross-module interactions
- Validation with actual data (manual testing)

**Phase 6 Comprehensive Testing**:
- End-to-end pipeline test
- Error handling test
- Performance test
- Usability test

**Success Criteria**:
- All unit tests pass (>90% coverage)
- E2E test completes without errors
- Performance: telemetry overhead <5%, report <5s, checks <10s
- Documentation complete and accurate

## Common Pitfalls

1. **File Locking Issues**: Use fcntl properly (Phase 0)
2. **Circular Imports**: Follow dependency hierarchy strictly
3. **API Key Exposure**: Use SecretRedactor on all logged data
4. **Timezone Confusion**: Always use `datetime.now(timezone.utc)`
5. **Numpy JSON Serialization**: Use `default=str` or NumpyEncoder
6. **Cost Overruns**: Monitor quality scoring budget limits
7. **Performance Degradation**: Benchmark continuously

## Quick Reference: Key Files

**Configuration**:
- `config/analytics_config.json` - all feature settings
- `config/secret_patterns.json` - existing secret patterns

**Shared Utilities** (Phase 0):
- `scripts/metrics/jsonl_utils.py` - log reading/writing
- `scripts/metrics/calculator.py` - metric calculations
- `scripts/metrics/config.py` - configuration manager
- `scripts/metrics/event_correlation.py` - event linking
- `scripts/metrics/session_loader.py` - session content loading

**Log Files**:
- `.claude/context/sessions/recall_analytics.jsonl` - telemetry
- `.claude/context/sessions/context_impact.jsonl` - impact analysis
- `.claude/context/sessions/quality_scores.jsonl` - quality scoring
- `.claude/context/sessions/quality_check_log.jsonl` - check results

**CLI Tools** (created in later phases):
- `scripts/generate_recall_report.py` - reporting
- `scripts/run_quality_checks.py` - quality checks
- `scripts/setup_analytics.py` - configuration wizard
- `scripts/analytics_status.py` - monitoring

## Support

**Questions?**
- Review the detailed implementation plan in analysis notes
- Check specific phase documentation (listed above)
- Review existing recall system code in `scripts/`
- Consult with other agents working on related phases

**Blocked?**
- Check dependencies: `bd show <task-id>`
- Coordinate with agents on blocking tasks
- Ask clarifying questions before proceeding
- Document assumptions in task notes

## Progress Tracking

```bash
# View overall progress
bd list | grep "recall-1\." | grep -E "(completed|in_progress)"

# View phase progress
bd list | grep "recall-1.1" | grep -E "(completed|in_progress)"

# Find available work (nothing blocking you)
bd ready --filter "parent:recall-1"

# View your assigned tasks
bd list --assignee <your-name>
```

---

**Last Updated**: 2026-02-16
**Epic Owner**: <to be assigned>
**Target Completion**: 8 weeks from start
