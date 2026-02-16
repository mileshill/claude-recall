# Phase 3: Semantic Search - Deep Analysis

## Executive Summary

Phase 3 adds true semantic search using embeddings, enabling queries like "authentication" to match sessions about "login", "security", "JWT", etc. This analysis breaks down each task, evaluates solutions, identifies conflicts, and provides a resolution strategy.

---

## Task Breakdown & Solution Analysis

### Task 3.1: Optional Dependency Management

**Objective**: Make sentence-transformers an optional dependency that doesn't break the system if unavailable.

#### Solution Options

**Option 3.1A: requirements-optional.txt (Recommended)**
```
Pros:
+ Clear separation (core vs optional)
+ User controls installation
+ No breaking changes
+ Simple documentation

Cons:
- Manual installation step
- No automatic detection
```

**Option 3.1B: Auto-install on first use**
```python
try:
    import sentence_transformers
except ImportError:
    print("Installing sentence-transformers...")
    subprocess.run(["pip", "install", "sentence-transformers"])
```
```
Pros:
+ Automatic setup
+ User doesn't think about it

Cons:
- Surprising behavior (auto-installs ~500MB)
- Requires pip in PATH
- Permission issues in some environments
- Anti-pattern (libraries shouldn't auto-install)
```

**Option 3.1C: Feature flags in settings.json**
```json
{
  "recall": {
    "features": {
      "embeddings": "auto"  // "enabled", "disabled", "auto"
    }
  }
}
```
```
Pros:
+ User control via config
+ Clear opt-in/opt-out
+ Can disable if causing issues

Cons:
- More configuration complexity
- Still requires manual installation
```

**Optimal Solution**: **3.1A (requirements-optional.txt)** + Feature detection in code

**Rationale**:
- Explicit is better than implicit
- Users should know about large dependencies
- Graceful degradation is built into code (try/except)
- Clear documentation tells users how to enable it

**Implementation**:
```python
# Feature detection
def has_embeddings_support():
    try:
        import sentence_transformers
        return True
    except ImportError:
        return False

# Graceful fallback
def search(query, mode='auto'):
    if mode == 'semantic' and not has_embeddings_support():
        print("ℹ️  Embeddings not available. Install with:")
        print("   pip install -r .claude/skills/recall/requirements-optional.txt")
        return search_bm25(query)
    # ...
```

---

### Task 3.2: Model Selection

**Objective**: Choose the best embedding model balancing quality, speed, and size.

#### Model Candidates

| Model | Size | Dims | Speed | Quality | Notes |
|-------|------|------|-------|---------|-------|
| all-MiniLM-L6-v2 | 80MB | 384 | Fast | Good | Best balance |
| all-mpnet-base-v2 | 420MB | 768 | Slow | Best | Highest quality |
| paraphrase-MiniLM-L6-v2 | 80MB | 384 | Fast | Good | Optimized for paraphrases |
| all-MiniLM-L12-v2 | 120MB | 384 | Medium | Better | Larger than L6 |
| msmarco-distilbert-base-v4 | 250MB | 768 | Medium | Better | Trained on search |

#### Evaluation Criteria

1. **Size** (30% weight)
   - Target: < 100MB for quick download
   - Reason: Users on slow connections, mobile hotspots

2. **Speed** (25% weight)
   - Target: < 100ms for encoding 5 sessions
   - Reason: Indexing shouldn't feel slow

3. **Quality** (35% weight)
   - Target: Semantic similarity detection
   - Test: "auth" should match "login", "security"

4. **Dimensions** (10% weight)
   - Lower dims = faster search, less storage
   - Higher dims = better quality
   - 384 dims sufficient for our use case

#### Testing Methodology

```python
# Test queries for quality evaluation
test_cases = [
    ("authentication system", ["login flow", "JWT tokens", "security implementation"]),
    ("database changes", ["schema migration", "SQL updates", "Postgres changes"]),
    ("UI improvements", ["frontend updates", "React components", "styling changes"]),
    ("bug fix", ["error resolution", "crash fix", "issue solved"]),
]

# For each model, measure:
# - Load time (first use)
# - Encoding speed (avg per session)
# - Semantic match quality (% of related docs found)
```

**Optimal Solution**: **all-MiniLM-L6-v2**

**Rationale**:
- ✅ Small size (80MB) - fast download
- ✅ Fast encoding (~50ms for 5 sessions)
- ✅ 384 dimensions - good quality, efficient storage
- ✅ Well-tested, popular choice
- ✅ Supports sentence similarity (our use case)
- ✅ Maintained by sentence-transformers team

**Score**:
- Size: 10/10 (80MB)
- Speed: 9/10 (very fast)
- Quality: 8/10 (good, not best but sufficient)
- **Total: 8.8/10**

**Alternative**: If users report quality issues, provide config option to upgrade to `all-mpnet-base-v2`.

---

### Task 3.3: Embedding Generation Strategy

**Objective**: Generate embeddings efficiently without blocking the UI or using excessive memory.

#### Solution Options

**Option 3.3A: Synchronous batch generation**
```python
# Generate all embeddings immediately when indexing
def index_session(session):
    embeddings = model.encode(session_text)
    save_to_index(embeddings)
```
```
Pros:
+ Simple implementation
+ Embeddings available immediately
+ No background workers needed

Cons:
- Blocks during generation (5-10s delay)
- Poor UX for large backlogs
- SessionEnd hook might timeout
```

**Option 3.3B: Lazy generation (on first search)**
```python
def search_semantic(query):
    if not embeddings_exist():
        print("Generating embeddings for first time...")
        generate_all_embeddings()  # 5-10s delay
    return search_embeddings(query)
```
```
Pros:
+ No upfront cost
+ Only compute if user needs it

Cons:
- First search is very slow (bad UX)
- Unpredictable delay
- User doesn't know it's coming
```

**Option 3.3C: Background worker (async)**
```python
# Hook triggers background process
def on_session_end():
    save_session()
    spawn_background("generate_embeddings_worker.py")

# Worker runs independently
def embedding_worker():
    while True:
        sessions = find_sessions_without_embeddings()
        if sessions:
            generate_embeddings(sessions)
        time.sleep(60)  # Check every minute
```
```
Pros:
+ Non-blocking (great UX)
+ Handles backlog gradually
+ Can batch multiple sessions

Cons:
- More complex (daemon process)
- Need process management
- Resource usage even when idle
```

**Option 3.3D: On-demand with progress (Recommended)**
```python
def index_session(session):
    # Save metadata immediately
    save_metadata(session)

    # Queue for embedding (mark as pending)
    mark_for_embedding(session.id)

    # User can trigger manually
    # $ python3 embed_sessions.py
    # Or it happens on next search (with progress bar)
```
```
Pros:
+ Non-blocking save (fast SessionEnd)
+ Clear user control
+ Progress visibility
+ No daemon needed

Cons:
- Embeddings not immediately available
- Need to run manually or on first search
```

**Optimal Solution**: **3.3D (On-demand with progress)**

**Rationale**:
- SessionEnd hook must stay fast (< 2s)
- User can run embedding generation when convenient
- First semantic search auto-generates (with progress bar)
- Simpler than background daemon
- Clear, predictable behavior

**Implementation**:
```python
# 1. Fast save (no embedding)
def index_session(session):
    metadata = parse_metadata(session)
    metadata['needs_embedding'] = True
    save_to_index(metadata)

# 2. Batch embedding script (run manually or auto)
def embed_pending_sessions():
    sessions = [s for s in index if s.get('needs_embedding')]
    if not sessions:
        return

    print(f"Generating embeddings for {len(sessions)} sessions...")
    for i, session in enumerate(sessions):
        embedding = model.encode(session_text)
        save_embedding(session.id, embedding)
        session['needs_embedding'] = False
        print(f"  [{i+1}/{len(sessions)}] {session.id}")

# 3. Auto-trigger on first semantic search
def search_semantic(query):
    if any(s.get('needs_embedding') for s in index):
        print("⏳ Generating embeddings (one-time, ~10s)...")
        embed_pending_sessions()
    return semantic_search_impl(query)
```

---

### Task 3.4: Embedding Storage

**Objective**: Store embeddings efficiently with minimal disk space and fast retrieval.

#### Solution Options

**Option 3.4A: Store in index.json (inline)**
```json
{
  "sessions": [
    {
      "id": "session-123",
      "embedding": [0.123, -0.456, 0.789, ...]  // 384 floats
    }
  ]
}
```
```
Pros:
+ Single file (simple)
+ Easy to backup/restore

Cons:
- Large JSON file (384 floats × 100 sessions = ~150KB)
- Slow to parse
- Not efficient for large scale
```

**Option 3.4B: Separate embeddings.pkl (binary)**
```python
# embeddings.pkl
{
  'session-123': np.array([0.123, -0.456, ...], dtype=np.float32),
  'session-456': np.array([...]),
}
```
```
Pros:
+ Binary format (smaller, faster)
+ Separate from index (cleaner)
+ NumPy-native (fast operations)

Cons:
- Two files to manage
- Pickle security concerns (trusted data only)
```

**Option 3.4C: Separate embeddings.npz (compressed numpy)**
```python
# embeddings.npz (compressed)
np.savez_compressed(
    'embeddings.npz',
    ids=['session-123', 'session-456'],
    embeddings=np.array([[...], [...]])  # 2D array
)
```
```
Pros:
+ Compressed (smallest size)
+ Fast NumPy loading
+ Efficient for large matrices

Cons:
- Two files to manage
- Need to maintain ID mapping
```

**Option 3.4D: Hybrid - metadata in JSON, embeddings in .npz (Recommended)**
```python
# index.json (lightweight metadata)
{
  "sessions": [{"id": "session-123", "summary": "...", "has_embedding": true}]
}

# embeddings.npz (binary, compressed)
{
  "ids": ["session-123", "session-456"],
  "embeddings": [[...], [...]],  # Shape: (N, 384)
  "model": "all-MiniLM-L6-v2"
}
```
```
Pros:
+ Best of both worlds
+ Small JSON (fast parsing)
+ Compressed embeddings (small disk space)
+ Fast similarity search (NumPy operations)
+ Clean separation

Cons:
- Two files (manageable)
- Need to sync between files
```

**Optimal Solution**: **3.4D (Hybrid JSON + NPZ)**

**Rationale**:
- JSON stays small and fast (< 100KB for 100 sessions)
- Embeddings compressed in binary format
- 100 sessions × 384 dims × 4 bytes = ~150KB uncompressed → ~50KB compressed
- NumPy operations are fast (< 1ms for similarity search)
- Clear separation of concerns

**Storage Calculation**:
```
100 sessions:
- index.json: ~80KB (metadata)
- embeddings.npz: ~50KB (compressed)
Total: ~130KB

1000 sessions:
- index.json: ~800KB (metadata)
- embeddings.npz: ~500KB (compressed)
Total: ~1.3MB
```

---

### Task 3.5: Semantic Query Implementation

**Objective**: Implement fast, accurate semantic similarity search.

#### Solution Options

**Option 3.5A: Brute-force cosine similarity**
```python
def search_semantic(query, top_k=5):
    query_emb = model.encode([query])[0]

    # Cosine similarity with all embeddings
    similarities = np.dot(embeddings, query_emb) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_emb)
    )

    top_indices = np.argsort(similarities)[-top_k:][::-1]
    return [(index, similarities[index]) for index in top_indices]
```
```
Pros:
+ Simple implementation
+ Exact results
+ Fast for < 1000 sessions

Cons:
- O(N) complexity
- Slower for large datasets (> 10K sessions)
```

**Option 3.5B: Approximate nearest neighbors (FAISS/Annoy)**
```python
import faiss
index = faiss.IndexFlatIP(384)  # Inner product (cosine)
index.add(embeddings)
distances, indices = index.search(query_emb, k=5)
```
```
Pros:
+ Very fast (O(log N))
+ Scales to millions of vectors

Cons:
- Heavy dependency (FAISS ~50MB)
- Overkill for < 10K sessions
- Approximate (may miss some results)
- Complexity overhead
```

**Option 3.5C: Dot product (pre-normalized, fastest)**
```python
# Pre-normalize embeddings at index time
embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

def search_semantic(query, top_k=5):
    query_norm = query_emb / np.linalg.norm(query_emb)

    # Cosine similarity = dot product (when normalized)
    similarities = np.dot(embeddings_norm, query_norm)

    top_indices = np.argsort(similarities)[-top_k:][::-1]
    return [(index, similarities[index]) for index in top_indices]
```
```
Pros:
+ Fastest (single matrix multiply)
+ Exact results
+ Simple implementation
+ No extra dependencies

Cons:
- Need to store normalized embeddings
- Still O(N) but with lower constant
```

**Optimal Solution**: **3.5C (Pre-normalized dot product)**

**Rationale**:
- Target: < 1000 sessions (< 500ms for semantic search)
- Dot product is fastest operation (~0.1ms for 100 sessions)
- No need for approximate methods at this scale
- Simple, no extra dependencies
- Can always upgrade to FAISS later if needed

**Performance**:
```
100 sessions:   0.1ms
1,000 sessions: 1ms
10,000 sessions: 10ms  (still acceptable)
```

---

### Task 3.6: Hybrid Search (BM25 + Embeddings)

**Objective**: Combine BM25 (keyword) and embeddings (semantic) for best of both worlds.

#### Solution Options

**Option 3.6A: Simple weighted average**
```python
final_score = alpha * bm25_score + (1 - alpha) * semantic_score
# alpha = 0.5 (equal weight)
```
```
Pros:
+ Simple
+ One parameter to tune

Cons:
- Assumes scores are comparable
- May need normalization
- Doesn't handle different score ranges
```

**Option 3.6B: Normalized weighted average (Recommended)**
```python
# Normalize scores to [0, 1]
bm25_norm = (bm25_scores - min(bm25_scores)) / (max(bm25_scores) - min(bm25_scores))
semantic_norm = semantic_scores  # Already [0, 1] from cosine

final_score = 0.5 * bm25_norm + 0.5 * semantic_norm
```
```
Pros:
+ Fair comparison (same scale)
+ Interpretable scores
+ Configurable weights

Cons:
- Need min/max from results
- May not work well with few results
```

**Option 3.6C: Reciprocal Rank Fusion (RRF)**
```python
# Rank-based fusion (used by search engines)
def rrf(bm25_ranks, semantic_ranks, k=60):
    scores = {}
    for doc_id, rank in bm25_ranks.items():
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    for doc_id, rank in semantic_ranks.items():
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```
```
Pros:
+ Rank-based (no score normalization needed)
+ Used by production search systems
+ Handles different score ranges naturally

Cons:
- More complex
- k parameter needs tuning
- Less intuitive than weighted average
```

**Option 3.6D: Query-dependent routing**
```python
# Route to best method based on query type
if looks_like_keyword_query(query):  # "session-123", "2024-02-16"
    return search_bm25(query)
elif looks_like_semantic_query(query):  # "how did I implement auth?"
    return search_semantic(query)
else:
    return hybrid_search(query)
```
```
Pros:
+ Uses best method for query type
+ Can be more accurate

Cons:
- Need query classification
- More complex
- May guess wrong
```

**Optimal Solution**: **3.6B (Normalized weighted average)** with configurable weights

**Rationale**:
- Simple and interpretable
- Users can adjust weights (default 0.5/0.5)
- Normalization ensures fair comparison
- Can tune based on feedback

**Implementation**:
```python
def hybrid_search(query, bm25_weight=0.5, semantic_weight=0.5, top_k=5):
    # Get results from both methods
    bm25_results = search_bm25(query, top_k=top_k*2)  # Get more for fusion
    semantic_results = search_semantic(query, top_k=top_k*2)

    # Normalize BM25 scores to [0, 1]
    if bm25_results:
        bm25_scores = [r['score'] for r in bm25_results]
        bm25_min, bm25_max = min(bm25_scores), max(bm25_scores)
        if bm25_max > bm25_min:
            for r in bm25_results:
                r['score_norm'] = (r['score'] - bm25_min) / (bm25_max - bm25_min)
        else:
            for r in bm25_results:
                r['score_norm'] = 1.0

    # Semantic scores already normalized (cosine similarity in [0, 1])
    for r in semantic_results:
        r['score_norm'] = r['score']

    # Combine scores
    combined = {}
    for r in bm25_results:
        combined[r['id']] = combined.get(r['id'], 0) + bm25_weight * r['score_norm']
    for r in semantic_results:
        combined[r['id']] = combined.get(r['id'], 0) + semantic_weight * r['score_norm']

    # Sort and return top_k
    sorted_results = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [{'id': id, 'score': score, 'method': 'hybrid'} for id, score in sorted_results]
```

---

### Task 3.7: Lazy Loading & Caching

**Objective**: Load embedding model only when needed, cache for performance.

#### Solution Options

**Option 3.7A: Module-level singleton**
```python
_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading model (5-10s)...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model
```
```
Pros:
+ Simple
+ Automatic caching
+ Works across function calls

Cons:
- Global state (not ideal)
- Can't unload model
- No control over lifecycle
```

**Option 3.7B: Class-based with __init__**
```python
class EmbeddingSearch:
    def __init__(self):
        self.model = None

    def _ensure_model(self):
        if self.model is None:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def search(self, query):
        self._ensure_model()
        # ...
```
```
Pros:
+ Clean OOP design
+ Testable
+ Can have multiple instances

Cons:
- More boilerplate
- Need to manage instance
```

**Option 3.7C: Functools lru_cache (function attribute)**
```python
@functools.lru_cache(maxsize=1)
def get_model():
    print("Loading model...")
    return SentenceTransformer('all-MiniLM-L6-v2')

def search(query):
    model = get_model()  # Cached after first call
    # ...
```
```
Pros:
+ Pythonic
+ Automatic caching
+ No global state
+ Can clear cache if needed

Cons:
- Function-level caching (less obvious)
```

**Option 3.7D: Lazy property (Recommended for CLI)**
```python
class SearchIndex:
    @property
    def model(self):
        if not hasattr(self, '_model'):
            print("Loading embedding model (5-10s)...")
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model
```
```
Pros:
+ Clean interface
+ Lazy loading
+ Testable
+ Can unload (del instance._model)

Cons:
- Requires class structure
```

**Optimal Solution**: **3.7A (Module-level singleton)** for CLI simplicity

**Rationale**:
- Scripts are stateless (run and exit)
- Model loads once per script execution
- Simple, works well for CLI tools
- Can upgrade to class-based later if needed

**With unload support**:
```python
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def unload_model():
    global _model
    _model = None
    import gc
    gc.collect()  # Free memory
```

---

### Task 3.8: Background Indexing

**Objective**: Generate embeddings for new sessions without blocking.

#### Solution Options

**Option 3.8A: Cron job**
```bash
# Run every hour
0 * * * * cd /path/to/project && python3 .claude/skills/recall/scripts/embed_sessions.py
```
```
Pros:
+ Simple, standard approach
+ No process management
+ Reliable

Cons:
- User must set up cron
- Not cross-platform (Windows different)
- Fixed schedule (may run when not needed)
```

**Option 3.8B: Systemd service/daemon**
```
Pros:
+ Always running
+ Auto-restart on failure
+ Integrated with OS

Cons:
- Complex setup
- Not cross-platform
- Overkill for our use case
```

**Option 3.8C: On-demand (manual or auto-trigger)**
```python
# User runs manually
$ python3 .claude/skills/recall/scripts/embed_sessions.py

# Or auto-trigger on first semantic search
def search_semantic(query):
    if has_pending_embeddings():
        print("Generating embeddings first...")
        embed_pending_sessions()
    # ...
```
```
Pros:
+ No background process
+ User control
+ Simple, cross-platform

Cons:
- Not automatic
- First search may be slow
```

**Option 3.8D: SessionEnd hook triggers async process (Recommended)**
```bash
# In .claude/hooks/session-end
python3 .claude/skills/recall/scripts/auto_capture.py
python3 .claude/skills/recall/scripts/embed_new_sessions.py --async &
# Run in background, non-blocking
```
```
Pros:
+ Automatic
+ Non-blocking (async)
+ Happens at right time (after session)
+ No cron needed

Cons:
- Background process per session
- Need process management (PID files)
```

**Optimal Solution**: **3.8C (On-demand)** with optional hook integration

**Rationale**:
- Simplest, most reliable
- Works everywhere (cross-platform)
- No background processes to manage
- User can run manually when convenient
- Auto-runs on first semantic search (transparent)

**Enhancement**: Add hook for power users:
```python
# Optional: Add to SessionEnd hook for automatic embedding
# .claude/settings.json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {"command": "python3 ... auto_capture.py"},
          {"command": "python3 ... embed_new_sessions.py --async", "optional": true}
        ]
      }
    ]
  }
}
```

---

## Conflict Analysis

### Conflict 1: Storage Format vs. Performance

**Issue**: JSON is easy but slow for large embeddings; binary is fast but complex.

**Components in conflict**:
- Task 3.4A: Store in JSON (simple)
- Task 3.4D: Store in NPZ (fast)

**Resolution**: **Use hybrid (3.4D)**
- Metadata in JSON (human-readable, small)
- Embeddings in NPZ (binary, compressed)
- Best of both worlds

**Trade-off**: Two files instead of one, but manageable.

---

### Conflict 2: Lazy Loading vs. First-Time UX

**Issue**: Lazy loading saves memory but causes slow first search.

**Components in conflict**:
- Task 3.7: Lazy load model (memory efficient)
- Task 3.5: Fast search (requires model loaded)

**Resolution**: **Lazy load with clear messaging**
```python
def first_semantic_search():
    print("⏳ Loading embedding model (one-time, ~10s)...")
    print("   Downloading all-MiniLM-L6-v2 (80MB)...")
    # Load model
    print("✓ Model loaded. Subsequent searches will be instant.")
```

**Trade-off**: First search is slow (~10s), but user is informed.

---

### Conflict 3: Automatic vs. Manual Embedding Generation

**Issue**: Automatic is convenient but may run at bad times; manual is flexible but requires user action.

**Components in conflict**:
- Task 3.8D: Auto-generate via hook (convenient)
- Task 3.8C: Manual generation (user control)

**Resolution**: **Default to manual, provide hook for power users**
- Ship with on-demand generation (Task 3.8C)
- Document optional hook setup for automatic (Task 3.8D)
- User chooses based on preference

**Trade-off**: Not automatic by default, but safer and simpler.

---

### Conflict 4: BM25 vs. Embeddings - Which to prioritize?

**Issue**: BM25 is fast but keyword-based; embeddings are slow but semantic. Which should be default?

**Components in conflict**:
- Task 2.1: BM25 search (fast, keyword)
- Task 3.5: Semantic search (slow, semantic)

**Resolution**: **Intelligent routing based on query**
```python
def search(query, mode='auto'):
    if mode == 'auto':
        # Use BM25 by default (fast)
        # User can explicitly request semantic
        return search_bm25(query)
    elif mode == 'semantic':
        return search_semantic(query)
    elif mode == 'hybrid':
        return hybrid_search(query)
```

**User control**:
```bash
# Default: BM25 (fast)
python3 search_index.py --query="authentication"

# Semantic (slower but semantic matching)
python3 search_index.py --query="authentication" --mode=semantic

# Hybrid (best of both)
python3 search_index.py --query="authentication" --mode=hybrid
```

**Trade-off**: Semantic not used by default, but available when needed.

---

### Conflict 5: Dependency Size vs. Quality

**Issue**: Better models are larger; smaller models sacrifice quality.

**Components in conflict**:
- Task 3.2: all-MiniLM-L6-v2 (80MB, good quality)
- Task 3.2: all-mpnet-base-v2 (420MB, best quality)

**Resolution**: **Default to small, allow upgrade**
```python
# Default
MODEL = 'all-MiniLM-L6-v2'  # 80MB

# Advanced users can upgrade
# .claude/settings.json
{
  "recall": {
    "embedding_model": "all-mpnet-base-v2"  # 420MB
  }
}
```

**Trade-off**: Not the absolute best quality out-of-box, but good enough for 95% of use cases.

---

## Resolved Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                      Search Flow                             │
└─────────────────────────────────────────────────────────────┘

User Query
    ↓
┌───────────────┐
│ search_index  │ ──→ mode=bm25 ──→ BM25 Search (fast, keyword)
│   CLI         │
└───────────────┘ ──→ mode=semantic ──→ Semantic Search (slow, semantic)
                                              ↓
                                        [Check embeddings]
                                              ↓
                                        ┌──────────────┐
                                        │ Missing?     │
                                        └──────────────┘
                                              ↓ Yes
                                        ┌──────────────────┐
                                        │ Generate now     │
                                        │ (with progress)  │
                                        └──────────────────┘
                                              ↓
                                        [Load model]
                                        [Encode query]
                                        [Dot product]
                                        [Rank results]
                                              ↓
                ──→ mode=hybrid ──→ Hybrid Search (balanced)
                                              ↓
                                        [Run both BM25 + Semantic]
                                        [Normalize scores]
                                        [Weighted average]
                                        [Merge & rank]
```

### File Structure

```
.claude/skills/recall/
├── requirements-core.txt          (rank-bm25)
├── requirements-optional.txt      (sentence-transformers) ← NEW
├── config/
│   ├── secret_patterns.json
│   └── embedding_config.json     ← NEW (model, weights, etc.)
├── scripts/
│   ├── index_session.py          (modified: mark needs_embedding)
│   ├── search_index.py           (modified: add semantic + hybrid)
│   ├── embed_sessions.py         ← NEW (batch embedding generation)
│   ├── semantic_search.py        ← NEW (semantic search logic)
│   └── test_semantic.py          ← NEW (test suite)
└── data/
    ├── index.json                (session metadata)
    └── embeddings.npz            ← NEW (compressed embeddings)
```

### Data Flow

```
Session Capture → index_session.py → metadata saved (needs_embedding=True)
                                                    ↓
User runs embed_sessions.py OR first semantic search
                                                    ↓
                                        Load model (lazy, cached)
                                                    ↓
                                        Encode sessions (batch)
                                                    ↓
                                        Save embeddings.npz
                                                    ↓
                                        Update metadata (needs_embedding=False)
                                                    ↓
Semantic search → Load embeddings.npz → Dot product → Rank → Results
```

---

## Implementation Plan

### Phase 3.1: Optional Dependencies (30 min)

**Goal**: Set up dependency management with graceful fallback.

**Tasks**:
1. Create `requirements-optional.txt`
2. Add feature detection to `search_index.py`
3. Implement graceful fallback messaging
4. Test with and without sentence-transformers

**Deliverables**:
- requirements-optional.txt
- Feature detection code
- Fallback messaging

**Testing**:
```bash
# Test without embeddings
pip uninstall sentence-transformers
python3 search_index.py --query="test" --mode=semantic
# Should: Show install instructions, fallback to BM25

# Test with embeddings
pip install -r requirements-optional.txt
python3 search_index.py --query="test" --mode=semantic
# Should: Use semantic search
```

---

### Phase 3.2: Embedding Generation (2 hours)

**Goal**: Implement batch embedding generation with progress.

**Tasks**:
1. Create `embed_sessions.py`
   - Load model (lazy, with caching)
   - Find sessions without embeddings
   - Batch encode (progress bar)
   - Save to embeddings.npz
   - Update index metadata

2. Modify `index_session.py`
   - Mark new sessions with `needs_embedding=True`
   - Don't block on embedding generation

3. Create embedding config
   - Model name
   - Batch size
   - Dimension

**Deliverables**:
- scripts/embed_sessions.py
- config/embedding_config.json
- Modified index_session.py

**Testing**:
```bash
# Create test sessions (already exists)
# Mark them as needing embeddings
python3 embed_sessions.py
# Should: Generate embeddings with progress bar
ls .claude/context/sessions/embeddings.npz
# Should: Exist with embeddings for all sessions
```

---

### Phase 3.3: Semantic Search (2 hours)

**Goal**: Implement semantic similarity search.

**Tasks**:
1. Create `semantic_search.py`
   - Load embeddings.npz
   - Encode query
   - Dot product similarity
   - Rank and return results

2. Modify `search_index.py`
   - Add `--mode=semantic` option
   - Integrate semantic_search module
   - Auto-generate embeddings if missing

3. Add normalization and scoring
   - Normalize embeddings at save time
   - Dot product for fast similarity
   - Score breakdown in output

**Deliverables**:
- scripts/semantic_search.py
- Modified search_index.py
- Score breakdown output

**Testing**:
```bash
# Test semantic query
python3 search_index.py --query="authentication system" --mode=semantic

# Expected: Should find sessions about "login", "JWT", "security"
# even if they don't contain word "authentication"

# Compare with BM25
python3 search_index.py --query="authentication system" --mode=bm25

# Expected: Different results (keyword-based)
```

---

### Phase 3.4: Hybrid Search (1.5 hours)

**Goal**: Combine BM25 and semantic search.

**Tasks**:
1. Implement hybrid_search() in search_index.py
   - Run both BM25 and semantic
   - Normalize scores to [0, 1]
   - Weighted average (configurable)
   - Merge and rank

2. Add configuration
   - bm25_weight (default 0.5)
   - semantic_weight (default 0.5)
   - Configurable via CLI or config file

3. Add score breakdown
   - Show BM25 score, semantic score, final score
   - Help users understand why results ranked

**Deliverables**:
- Hybrid search implementation
- Configurable weights
- Score breakdown output

**Testing**:
```bash
# Test hybrid search
python3 search_index.py --query="auth implementation" --mode=hybrid

# Should combine keyword + semantic signals
# Show score breakdown

# Test weight adjustment
python3 search_index.py --query="auth" --mode=hybrid --bm25-weight=0.7 --semantic-weight=0.3

# Should favor BM25 more (keyword matching)
```

---

### Phase 3.5: Testing & Validation (1 hour)

**Goal**: Comprehensive test suite for semantic search.

**Tasks**:
1. Create `test_semantic.py`
   - Test model loading
   - Test embedding generation
   - Test semantic similarity
   - Test hybrid search
   - Test edge cases (no embeddings, missing model)

2. Performance benchmarking
   - Measure query time
   - Measure embedding generation time
   - Verify < 100ms target (for 100 sessions)

3. Quality validation
   - Test semantic queries
   - Verify synonym matching
   - Compare BM25 vs semantic vs hybrid

**Deliverables**:
- tests/test_semantic.py
- Performance benchmarks
- Quality validation results

**Testing**:
```bash
python3 tests/test_semantic.py
# Should: All tests pass
# Should: Report performance metrics
# Should: Validate quality
```

---

### Phase 3.6: Documentation & Polish (30 min)

**Goal**: Document semantic search features and usage.

**Tasks**:
1. Update SKILL.md
   - Document semantic search
   - Installation instructions
   - Usage examples
   - Configuration options

2. Update BM25_IMPLEMENTATION.md or create SEMANTIC_SEARCH.md
   - Technical details
   - Model information
   - Architecture diagrams
   - Performance benchmarks

3. Add README to requirements-optional.txt
   - What it includes
   - When to install
   - How to install

**Deliverables**:
- Updated documentation
- Installation guide
- Usage examples

---

## Timeline

| Phase | Task | Duration | Dependencies |
|-------|------|----------|--------------|
| 3.1 | Optional Dependencies | 30 min | None |
| 3.2 | Embedding Generation | 2 hours | 3.1 |
| 3.3 | Semantic Search | 2 hours | 3.2 |
| 3.4 | Hybrid Search | 1.5 hours | 3.3 |
| 3.5 | Testing & Validation | 1 hour | 3.4 |
| 3.6 | Documentation | 30 min | 3.5 |

**Total: ~7.5 hours**

Can be parallelized:
- 3.1 (dependencies) + 3.2 (embedding) can run together (2 hours)
- 3.3 (semantic) + 3.4 (hybrid) sequential (3.5 hours)
- 3.5 (testing) + 3.6 (docs) can run together (1 hour)

**Optimized: ~6.5 hours with parallelization**

---

## Success Criteria

### Must Have
- [ ] sentence-transformers as optional dependency (graceful fallback)
- [ ] Embedding generation with progress bar
- [ ] Semantic search working (<100ms for 100 sessions)
- [ ] Hybrid search combining BM25 + semantic
- [ ] All tests pass (>= 95% pass rate)
- [ ] Documentation complete

### Nice to Have
- [ ] Background embedding generation via hook
- [ ] Model selection via config
- [ ] Embedding caching/incremental updates
- [ ] Visual score breakdown

### Performance Targets
- [ ] Model load: < 10s first time
- [ ] Embedding generation: < 50ms per session
- [ ] Semantic query: < 100ms for 100 sessions
- [ ] Hybrid query: < 150ms for 100 sessions
- [ ] Storage: < 1KB per session (compressed)

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| sentence-transformers install fails | Medium | High | Comprehensive install docs + fallback to BM25 |
| Model too large for some users | Low | Medium | Default to smallest model (80MB) |
| Semantic search quality poor | Low | Medium | Hybrid mode balances both |
| First search slow (model load) | High | Low | Clear messaging + progress bar |
| Embedding storage grows large | Low | Low | Compression (NPZ) keeps it small |

---

## Next Steps

Ready to implement? Recommended order:
1. Start with Phase 3.1 (dependencies) - foundational
2. Move to Phase 3.2 (embedding generation) - core functionality
3. Implement Phase 3.3 (semantic search) - delivers value
4. Add Phase 3.4 (hybrid) - best quality
5. Complete Phase 3.5 (testing) - validate everything works
6. Finish with Phase 3.6 (docs) - make it usable

**Alternatively**: Use Task agents to parallelize 3.1+3.2, then 3.3+3.4.
