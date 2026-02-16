---
name: recall
description: Query past session context using RLM. Searches session transcripts to recall decisions, implementations, discussions from previous conversations. Improves continuity across sessions and after context compaction.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Task
---

# recall - Query Past Session Context

Use this skill to search and retrieve information from previous Claude Code sessions.

## Purpose

After conversation compaction or in new sessions, use `/recall` to:
- Find past implementation decisions and rationale
- Review how features were built
- Locate previous discussions on specific topics
- Recover context that was compressed out

## Usage

```bash
/recall query="How did we implement the progress bar?"
/recall query="What database schema changes were made?" scope=decisions
/recall session=2026-02-16
/recall topics="authentication, jwt"
```

## How It Works

### Phase 1: BM25 Index Search (Fast, Free)
1. Parse `$ARGUMENTS` for query, scope, session, topics
2. Search `.claude/context/sessions/index.json` using BM25 algorithm
3. Rank results by relevance (BM25 score + temporal decay)
4. If exact match found (single session, clear topic), return excerpt directly

**BM25 Features:**
- Statistical relevance ranking (better than keyword matching)
- Temporal decay with 30-day half-life (recent sessions rank higher)
- Sub-millisecond query performance
- Backward compatible with legacy index format

### Phase 2: RLM Deep Search (Slow, Costs Tokens)
1. If Phase 1 returns multiple matches or query is complex:
   - Collect relevant session files
   - Use RLM skill to analyze sessions
   - Synthesize answer with source citations

### Phase 3: Fallback
1. If no sessions found, check:
   - Auto memory (`/Users/miles/.claude/projects/.../memory/`)
   - Beads decisions (`.beads/decisions/`)
   - Git history

## Arguments

Parse from `$ARGUMENTS`:
- `query="..."` (required): Natural language question about past context
- `scope=all|decisions|code|discussions` (optional): Narrow search scope
- `session=YYYY-MM-DD` (optional): Search specific session
- `topics="tag1,tag2"` (optional): Filter by topic tags
- `limit=N` (optional): Max sessions to search (default: 5)

## Implementation Steps

### Step 1: Parse and validate arguments
```bash
# Extract query
if [ -z "$query" ]; then
  echo "Error: query parameter required"
  echo "Usage: /recall query='your question here'"
  exit 1
fi
```

### Step 2: Search session index
```bash
# Check if index exists
if [ ! -f ".claude/context/sessions/index.json" ]; then
  echo "No session history found. Start capturing with /snapshot"
  exit 0
fi

# Search index for relevant sessions (implement index_search script)
python3 .claude/skills/recall/scripts/search_index.py \
  --query="$query" \
  --scope="$scope" \
  --session="$session" \
  --topics="$topics" \
  --limit="${limit:-5}"
```

### Step 3: Decide strategy based on results

**If 0 matches:**
- Report no relevant sessions found
- Suggest checking MEMORY.md or beads decisions
- Offer to search git history

**If 1 match with high confidence:**
- Read the session file
- Extract relevant section using grep/awk
- Return with citation: "From session 2026-02-16: [excerpt]"

**If 2-5 matches or low confidence:**
- Invoke RLM skill on matched sessions
- Prompt: "User query: {query}\n\nSearch these sessions and provide a comprehensive answer with source citations."
- Return synthesized answer

**If 6+ matches:**
- Ask user to narrow scope or provide more specific query
- Show session titles/dates for user to pick

### Step 4: RLM invocation (when needed)
```bash
# Concatenate matched sessions into temp file
cat matched_session1.md matched_session2.md > /tmp/recall_context.md

# Invoke RLM
/rlm context=/tmp/recall_context.md query="$query"

# Clean up
rm /tmp/recall_context.md
```

## Session Index Format

`.claude/context/sessions/index.json`:
```json
{
  "sessions": [
    {
      "id": "2026-02-16_093045",
      "file": "2026-02-16_093045_session.md",
      "timestamp": "2026-02-16",
      "captured": "2026-02-16T09:30:45Z",
      "status": "completed",
      "topics": ["rlm", "context-management", "skill-development"],
      "files_modified": [".claude/skills/rlm/SKILL.md", "..."],
      "beads_issues": ["beads-xxx"],
      "decisions": ["Use RLM for session recall"],
      "summary": "Implemented RLM context memory system for cross-session recall",
      "message_count": 42,
      "tokens_approx": 15000,
      "bm25_tokens": ["implemented", "rlm", "context", ...]
    }
  ],
  "bm25_index": {
    "doc_len": [118, 95, 87, 102],
    "avgdl": 100.5,
    "doc_freqs": {"rlm": 2, "context": 4, ...},
    "idf": {"rlm": 0.693, "context": 0.223, ...},
    "session_ids": ["2026-02-16_093045", ...]
  },
  "last_updated": "2026-02-16T17:00:00Z"
}
```

**New in BM25 Index:**
- `bm25_tokens`: Tokenized corpus for each session (weighted by importance)
- `bm25_index`: Global BM25 parameters for fast reconstruction
  - `doc_len`: Token count per document
  - `avgdl`: Average document length
  - `doc_freqs`: Document frequency per term
  - `idf`: Inverse document frequency scores
  - `session_ids`: Mapping of documents to session IDs

## Cost Management

- **Grep/index search**: Free, always try first
- **Single session read**: Free, just file I/O
- **RLM on 1 session**: ~$0.01-0.05 (Haiku chunks + Sonnet synthesis)
- **RLM on 5 sessions**: ~$0.05-0.25

Before expensive RLM queries on multiple sessions, show estimated cost and ask user to confirm.

## Privacy & Security

- Session files are gitignored by default (`.claude/context/.gitignore`)
- **Auto-redaction is enabled**: Secrets are automatically detected and redacted from session files and transcripts before writing to disk
- Redaction covers 35+ secret types: API keys, tokens, SSH keys, connection strings, credentials
- Detection uses dual approach: regex pattern matching (high confidence) + Shannon entropy analysis (medium confidence)
- Whitelist patterns prevent false positives on UUIDs, git hashes, hex colors, placeholders
- Redaction findings are logged to `.claude/context/sessions/redaction_log.jsonl`
- Index metadata (without full content) can be safely committed

### Secret Redaction Details

**Configuration**: `.claude/skills/recall/config/secret_patterns.json`
- 35+ regex patterns for common secret types (OpenAI, Anthropic, GitHub, AWS, Google, Slack, Stripe, SSH, DB connections, JWT, etc.)
- 9 whitelist patterns for false positive reduction (UUIDs, git hashes, placeholders)
- Shannon entropy threshold: 4.5 bits/char for high-randomness string detection

**Module**: `.claude/skills/recall/scripts/redact_secrets.py`
- Can be used standalone: `echo "text" | python3 redact_secrets.py`
- Or as a library: `from redact_secrets import SecretRedactor`

**Performance**: ~1ms per session (target < 500ms)
**Detection rate**: 100% on tested secret types
**False positive rate**: 0% on tested legitimate data

## Future Enhancements

- [x] BM25 search with temporal decay (completed 2026-02-16)
- [x] Auto-capture on session end via hooks (completed 2026-02-16)
- [x] Auto-redaction of secrets (completed 2026-02-16)
- [ ] Semantic search using embeddings
- [ ] Smart summarization of old sessions
- [ ] Integration with beads decisions
- [ ] Cost dashboard and budgets

## Testing

```bash
# Manual session capture (until hooks implemented)
/snapshot "Completed RLM context memory implementation"

# Query examples
/recall query="How did we structure the RLM skill?"
/recall query="What files did we modify today?" session=2026-02-16
/recall query="Show me past decisions about authentication"
```
