# Proactive Context Recall Guide

## Overview

The recall system now supports **automatic context retrieval** during conversations to boost continuity and reduce repetition.

### How It Works

1. **You mention a topic** → Claude extracts keywords
2. **Claude searches past sessions** → Finds relevant context
3. **Claude uses insights** → Builds on previous work
4. **You get continuity** → No need to re-explain

## Activation Modes

### Mode 1: Manual (Current - Recommended)

Claude proactively searches when relevant, but you stay in control.

**When Claude Searches**:
- You mention a feature, bug, or component
- Topic seems like it might have historical context
- You reference "previously", "last time", etc.

**Example**:
```
You: "I want to update the authentication flow"

Claude: Let me search for previous work on authentication...
[Searches and finds session from 2 weeks ago]
Claude: "I found session 2026-02-01 where you implemented JWT refresh
and fixed the timeout bug. Should we build on that approach?"
```

**Status**: ✅ Already enabled via CLAUDE.md instructions

### Mode 2: Automatic at Session Start (Optional)

Automatically searches for relevant context when you start a session.

**How It Works**:
1. Session starts
2. Script checks open beads issues, recent commits, branch name
3. Searches for relevant past sessions
4. Displays findings (if any)
5. Claude can reference context immediately

**Enable**:
```bash
# Add SessionStart hook to settings
# Edit .claude/settings.json and add:
```

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/skills/recall/scripts/session_start_recall.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/skills/recall/scripts/auto_capture.py"
          }
        ]
      }
    ]
  }
}
```

**Example Output at Session Start**:
```
============================================================
🧠 Smart Recall: Relevant Context Found
============================================================

📊 Analyzed: authentication, security, jwt

🔍 Found 2 relevant session(s):

1. 2026-02-01_143022_session (Score: 0.85 HIGH)
   Summary: Implemented JWT token refresh with 7-day expiry
   Topics: authentication, security, backend
   File: .claude/context/sessions/2026-02-01_143022_session.md

2. 2026-02-05_091234_session (Score: 0.72 HIGH)
   Summary: Fixed session timeout bug in auth middleware
   Topics: authentication, bug-fix, middleware
   File: .claude/context/sessions/2026-02-05_091234_session.md

============================================================
💡 Use /rlm to analyze these sessions in depth
============================================================
```

**Status**: ⚙️ Available but not enabled by default

### Mode 3: On-Demand Manual Search (Always Available)

You explicitly ask Claude to search for context.

**Commands**:
```bash
# You say: "Search for past work on authentication"
# Claude runs:
python3 .claude/skills/recall/scripts/search_index.py \
  --query "authentication security" \
  --mode hybrid

# Or use smart recall (auto keyword extraction):
python3 .claude/skills/recall/scripts/smart_recall.py \
  --context "authentication and security work"
```

**Status**: ✅ Always available

## How Claude Uses Recall

### Proactive Search Triggers

Claude automatically searches when you mention:

**1. Features or Components**
- "the upload component"
- "authentication system"
- "payment processing"
- "user dashboard"

**2. Past Work References**
- "we implemented this before"
- "like we did last time"
- "the previous approach"
- "when we fixed this earlier"

**3. Bugs or Issues**
- "the same bug as before"
- "that issue we had"
- "the performance problem"

**4. Technical Terms**
- Specific file names
- API endpoints
- Database tables
- Library names

### Search Strategy

1. **Extract Keywords**: Pull out technical terms and key concepts
2. **Use Hybrid Mode**: Combines keyword matching + semantic understanding
3. **Filter by Relevance**: Only use HIGH/MEDIUM confidence results (> 0.4)
4. **Cite Sources**: Always reference which session provided context
5. **Build Context**: Integrate findings naturally into response

### Example Interaction

**Without Recall**:
```
You: "Fix the upload component bug"
Claude: "I'll investigate the upload component. Can you describe the bug?"
[Starting from scratch]
```

**With Proactive Recall**:
```
You: "Fix the upload component bug"

Claude: [Searches for "upload component bug"]

Claude: "I found session 2026-02-10 where you fixed a similar upload bug.
The issue was with file size validation in FileUploadZone.tsx.
Is this the same issue, or something different?"

[Building on previous context]
```

## Smart Recall Features

### Keyword Extraction

Automatically identifies:
- ✅ Technical terms (API, JWT, React, etc.)
- ✅ Acronyms (RLM, BM25, CI/CD)
- ✅ camelCase terms (useState, fetchData)
- ✅ snake_case terms (auto_capture, search_index)
- ✅ File extensions (.tsx, .py, .md)

### Context Sources

Infers context from:
- ✅ Conversation text (what you say)
- ✅ Open beads issues (bd list)
- ✅ Recent commits (git log)
- ✅ Current branch (git branch)
- ✅ File paths mentioned

### Search Modes

- **auto**: Hybrid if embeddings available, else BM25 (recommended)
- **hybrid**: 50% BM25 keywords + 50% semantic concepts
- **bm25**: Pure keyword matching (fastest)
- **semantic**: Pure conceptual similarity (requires embeddings)

## Testing

### Test Smart Recall

```bash
# Test with sample context
python3 .claude/skills/recall/scripts/smart_recall.py \
  --context "I want to work on authentication and security" \
  --verbose

# Test with context file
python3 .claude/skills/recall/scripts/smart_recall.py \
  --context-file README.md \
  --verbose

# Test session start recall
python3 .claude/skills/recall/scripts/session_start_recall.py
```

### Test Results

```
=== Smart Recall Analysis ===
Keywords: want, authentication, security
Technical terms: authentication, security
Search query: authentication security want
==================================================

🔍 Found 2 relevant session(s):

1. Session: 2026-02-16_100458_session (Score: 0.77 HIGH)
   - Found RLM context memory implementation
   - Semantic understanding working correctly
```

## Benefits

### 1. Reduced Repetition
- Don't re-explain past decisions
- Build on previous implementations
- Reference past fixes

### 2. Better Continuity
- Pick up where you left off
- Connect related work across sessions
- Maintain project history

### 3. Faster Development
- Learn from past solutions
- Avoid repeating mistakes
- Reuse proven approaches

### 4. Improved Context
- Claude knows what was tried before
- Understands project evolution
- Can suggest improvements based on history

## Current Status

✅ **Manual Proactive Search**: Enabled in CLAUDE.md
✅ **Smart Recall Script**: Working and tested
✅ **Keyword Extraction**: Functional
✅ **Hybrid Search**: Performance validated (7-10ms)
⚙️ **SessionStart Hook**: Available but not auto-enabled

## Recommendations

### For Most Users (Recommended)

**Keep Mode 1 (Manual Proactive)** - Current setup
- Claude searches when relevant
- You stay in control
- No automatic startup delays
- Best balance of automation and control

### For Power Users

**Enable Mode 2 (SessionStart Hook)** - Optional
- Automatic context at session start
- Good if you frequently continue work across sessions
- Slight startup delay (~2 seconds)
- Best for long-running projects with deep history

### For All Users

**Use Mode 3 (On-Demand)** - Always available
- Explicitly ask Claude to search
- Full control over when to recall
- Best for specific questions about history

## Configuration

### Current Settings

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/skills/recall/scripts/auto_capture.py"
          }
        ]
      }
    ]
  }
}
```

**Enabled**:
- ✅ SessionEnd auto-capture
- ✅ BM25 + semantic search
- ✅ Secret redaction
- ✅ Proactive search (via CLAUDE.md)

**Optional** (add to settings.json):
- ⚙️ SessionStart automatic recall

### Enable SessionStart Hook

To enable automatic recall at session start:

1. Edit `.claude/settings.json`
2. Add SessionStart hook (see Mode 2 above)
3. Test: Start a new session and check for recall output

### Disable/Adjust Thresholds

Edit `session_start_recall.py`:
```python
# Line 24: Adjust minimum relevance threshold
min_relevance=0.4,  # Increase for fewer results (0.5, 0.6)
                   # Decrease for more results (0.3, 0.2)

# Line 23: Adjust number of results
limit=3,  # Show top 3 (increase/decrease as needed)
```

## Performance

### Smart Recall Speed

- **Keyword extraction**: < 1ms
- **Search (hybrid)**: ~7-10ms (cached)
- **First search**: ~1.5s (includes model loading)
- **SessionStart overhead**: ~2s (if enabled)

### Memory Usage

- **Model cached**: ~200MB (after first search)
- **Embeddings cached**: ~6KB (5 sessions)
- **Total overhead**: Minimal after warm-up

## Troubleshooting

### No results found

**Causes**:
- No relevant past sessions
- Query terms too specific
- Relevance threshold too high

**Solutions**:
- Use broader search terms
- Lower min_relevance threshold
- Check that sessions are being captured

### SessionStart hook not working

**Causes**:
- Hook not configured
- Script not executable
- Python dependencies missing

**Solutions**:
```bash
# Check hook configuration
cat .claude/settings.json | jq '.hooks.SessionStart'

# Make script executable
chmod +x .claude/skills/recall/scripts/session_start_recall.py

# Test manually
python3 .claude/skills/recall/scripts/session_start_recall.py
```

### Slow session start

**Cause**: Model loading on first search (~1.5s)

**Solutions**:
- Accept the delay (one-time per session)
- Disable SessionStart hook (use manual recall)
- Increase min_relevance to reduce searches

## Future Enhancements

Potential improvements (not yet implemented):

- [ ] Query expansion with synonyms
- [ ] Learning user preferences
- [ ] Relevance feedback (thumbs up/down)
- [ ] Multi-project federated search
- [ ] Automatic topic clustering
- [ ] Time-based smart surfacing

## Documentation

Related documentation:
- **README.md**: Complete recall system guide
- **SEMANTIC_SEARCH.md**: Search features and algorithms
- **SEMANTIC_SEARCH_TEST_REPORT.md**: Performance validation
- **CLAUDE.md**: Instructions for Claude (includes proactive recall)

## Commands Reference

```bash
# Smart recall with context
python3 .claude/skills/recall/scripts/smart_recall.py \
  --context "your context" \
  --verbose

# Direct search
python3 .claude/skills/recall/scripts/search_index.py \
  --query "your query" \
  --mode hybrid

# Test SessionStart recall
python3 .claude/skills/recall/scripts/session_start_recall.py

# Check what sessions exist
ls -lh .claude/context/sessions/*.md

# View index
jq . .claude/context/sessions/index.json
```

---

**Status**: ✅ Proactive recall enabled and working
**Recommendation**: Keep current setup (Mode 1) for best balance
**Optional**: Enable SessionStart hook (Mode 2) for automatic startup recall
