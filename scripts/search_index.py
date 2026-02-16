#!/usr/bin/env python3
"""
Search session index for relevant sessions.
Returns matching session files for recall skill to process.
Uses BM25 for relevance ranking and optional semantic search.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime, timezone
from rank_bm25 import BM25Okapi
import numpy as np
import time

# Telemetry imports
sys.path.insert(0, str(Path(__file__).parent))
from telemetry import (
    get_collector,
    get_current_session_id,
    get_system_state
)
from metrics.config import config as analytics_config
import threading
import asyncio

# Feature detection for optional semantic search
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None  # Type hint compatibility

def tokenize_query(query: str) -> list:
    """Tokenize query for BM25 search."""
    return re.findall(r'\w+', query.lower())

def calculate_temporal_score(session: dict, decay_days: float = 30.0) -> float:
    """
    Calculate temporal decay score (0-1) based on session age.
    More recent sessions get higher scores.

    Args:
        session: Session metadata
        decay_days: Half-life for temporal decay (default: 30 days)

    Returns:
        Float between 0 and 1, where 1 is most recent
    """
    try:
        # Parse timestamp from session id or captured field
        timestamp_str = session.get("captured") or session.get("timestamp", "")
        if not timestamp_str:
            return 0.5  # Default for unknown dates

        # Parse ISO format or date string
        if 'T' in timestamp_str:
            # ISO format: 2026-02-16T16:04:58Z
            session_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            # Date only: 2026-02-16
            session_date = datetime.strptime(timestamp_str, '%Y-%m-%d')

        # Calculate age in days
        now = datetime.now(timezone.utc if session_date.tzinfo else None)
        age_days = (now - session_date).total_seconds() / 86400

        # Exponential decay: score = e^(-age/decay_days)
        # This gives ~0.5 at decay_days, ~0.37 at 2*decay_days
        temporal_score = np.exp(-age_days / decay_days)

        return float(temporal_score)

    except Exception:
        # If parsing fails, return neutral score
        return 0.5

def bm25_search(query: str, index: dict) -> List[Dict]:
    """
    Search using BM25 algorithm with temporal boosting.

    Args:
        query: Search query string
        index: Index dictionary with sessions and bm25_index

    Returns:
        List of sessions with relevance scores
    """
    sessions = index.get('sessions', [])
    bm25_data = index.get('bm25_index')

    # Tokenize query
    query_tokens = tokenize_query(query)

    if not bm25_data or not sessions:
        # Fallback to simple scoring if BM25 not available
        return [
            {**session, "relevance_score": 0.0, "bm25_score": 0.0, "temporal_score": 0.5, "search_mode": "bm25"}
            for session in sessions
        ]

    # Handle empty query
    if not query_tokens:
        # No query terms, return all sessions with temporal scores only
        temporal_scores = [calculate_temporal_score(session) for session in sessions]
        return [
            {**session, "relevance_score": temporal_scores[i], "bm25_score": 0.0, "temporal_score": temporal_scores[i], "search_mode": "bm25"}
            for i, session in enumerate(sessions)
        ]

    # Reconstruct BM25 index from stored data
    corpus = [session.get("bm25_tokens", []) for session in sessions]

    # Check for empty corpus
    if not any(corpus):
        # No tokens in any session, use temporal scores only
        temporal_scores = [calculate_temporal_score(session) for session in sessions]
        return [
            {**session, "relevance_score": temporal_scores[i], "bm25_score": 0.0, "temporal_score": temporal_scores[i], "search_mode": "bm25"}
            for i, session in enumerate(sessions)
        ]

    bm25 = BM25Okapi(corpus)

    # Override with stored parameters for consistency
    if "doc_len" in bm25_data:
        bm25.doc_len = bm25_data["doc_len"]
    if "avgdl" in bm25_data:
        bm25.avgdl = bm25_data["avgdl"]
    if "doc_freqs" in bm25_data:
        bm25.doc_freqs = bm25_data["doc_freqs"]
    if "idf" in bm25_data:
        bm25.idf = bm25_data["idf"]

    # Get BM25 scores (wrap in try/except for edge cases)
    try:
        bm25_scores = bm25.get_scores(query_tokens)
    except (ValueError, IndexError) as e:
        # BM25 failed (e.g., query tokens not in corpus), use temporal scores only
        temporal_scores = [calculate_temporal_score(session) for session in sessions]
        return [
            {**session, "relevance_score": temporal_scores[i], "bm25_score": 0.0, "temporal_score": temporal_scores[i], "search_mode": "bm25"}
            for i, session in enumerate(sessions)
        ]

    # Normalize BM25 scores to 0-1 range
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    normalized_bm25 = bm25_scores / max_bm25

    # Calculate temporal scores
    temporal_scores = [calculate_temporal_score(session) for session in sessions]

    # Combine scores: 70% BM25, 30% temporal
    # This balances relevance with recency
    combined_scores = 0.7 * normalized_bm25 + 0.3 * np.array(temporal_scores)

    # Attach scores to sessions
    results = []
    for i, session in enumerate(sessions):
        results.append({
            **session,
            "relevance_score": float(combined_scores[i]),
            "bm25_score": float(normalized_bm25[i]),
            "temporal_score": float(temporal_scores[i]),
            "search_mode": "bm25"
        })

    return results

class EmbeddingCache:
    """Singleton cache for embeddings and model (lazy loading)."""

    _instance = None
    _embeddings = None
    _model = None
    _model_name = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_embeddings(self, embedding_path: Path) -> Optional[np.ndarray]:
        """
        Load embeddings from NPZ file (cached).

        Args:
            embedding_path: Path to embeddings.npz

        Returns:
            numpy array of embeddings or None if not available
        """
        if self._embeddings is not None:
            return self._embeddings

        if not embedding_path.exists():
            return None

        try:
            data = np.load(embedding_path, allow_pickle=False)
            if 'embeddings' not in data:
                print(f"Warning: No 'embeddings' key found in {embedding_path}", file=sys.stderr)
                return None
            self._embeddings = data['embeddings']
            # Validate embeddings shape
            if len(self._embeddings.shape) != 2:
                print(f"Warning: Invalid embeddings shape {self._embeddings.shape}, expected 2D array", file=sys.stderr)
                self._embeddings = None
                return None
            return self._embeddings
        except Exception as e:
            print(f"Warning: Failed to load embeddings from {embedding_path}: {e}", file=sys.stderr)
            return None

    def load_model(self, model_name: str = "all-MiniLM-L6-v2") -> Optional[SentenceTransformer]:
        """
        Load sentence transformer model (cached).

        Args:
            model_name: Name of model to load

        Returns:
            SentenceTransformer instance or None if not available
        """
        if not EMBEDDINGS_AVAILABLE:
            return None

        if self._model is not None and self._model_name == model_name:
            return self._model

        try:
            # Suppress FutureWarning from transformers about clean_up_tokenization_spaces
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
                self._model = SentenceTransformer(model_name)
            self._model_name = model_name
            return self._model
        except Exception as e:
            print(f"Warning: Failed to load model {model_name}: {e}", file=sys.stderr)
            return None

    def clear(self):
        """Clear cache (for testing)."""
        self._embeddings = None
        self._model = None
        self._model_name = None


def semantic_search(
    query: str,
    index: dict,
    embedding_cache: Optional[EmbeddingCache] = None
) -> Optional[List[float]]:
    """
    Search using semantic embeddings (cosine similarity).

    Args:
        query: Search query string
        index: Index dictionary with embedding metadata
        embedding_cache: Optional cache instance (uses singleton if not provided)

    Returns:
        List of normalized semantic scores (0-1) or None if embeddings unavailable
    """
    if not EMBEDDINGS_AVAILABLE:
        return None

    embedding_meta = index.get('embedding_index')
    if not embedding_meta:
        return None

    # Get cache
    if embedding_cache is None:
        embedding_cache = EmbeddingCache()

    # Load embeddings
    embedding_file = embedding_meta.get('embedding_file', 'embeddings.npz')
    # Assume embeddings are in same directory as index
    embedding_path = Path(index.get('_index_path', '.claude/context/sessions')).parent / embedding_file

    embeddings = embedding_cache.load_embeddings(embedding_path)
    if embeddings is None:
        return None

    # Validate embeddings match sessions count
    num_sessions = len(index.get('sessions', []))
    num_embeddings = len(embeddings)
    if num_embeddings != num_sessions:
        print(f"Warning: Embedding count mismatch (embeddings: {num_embeddings}, sessions: {num_sessions}). Regenerate embeddings with embed_sessions.py", file=sys.stderr)
        return None

    # Load model
    model_name = embedding_meta.get('model', 'all-MiniLM-L6-v2')
    model = embedding_cache.load_model(model_name)
    if model is None:
        return None

    # Generate query embedding
    try:
        query_embedding = model.encode([query], convert_to_numpy=True, show_progress_bar=False)
        # Normalize query embedding
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        # Compute cosine similarity via dot product (embeddings are pre-normalized)
        similarities = np.dot(embeddings, query_embedding.T).flatten()

        # Normalize to 0-1 range
        # Cosine similarity is already -1 to 1, shift to 0-1
        normalized_scores = (similarities + 1) / 2

        return normalized_scores.tolist()

    except Exception as e:
        print(f"Warning: Semantic search failed: {e}", file=sys.stderr)
        return None


def hybrid_search(query: str, index: dict) -> List[Dict]:
    """
    Hybrid search combining BM25 and semantic embeddings.

    Strategy:
    - If embeddings available: 50% BM25 + 50% semantic
    - Otherwise: Fall back to BM25 only
    - Temporal boosting applied to final score

    Args:
        query: Search query string
        index: Index dictionary with sessions and indices

    Returns:
        List of sessions with relevance scores
    """
    sessions = index.get('sessions', [])

    # Get BM25 scores
    bm25_results = bm25_search(query, index)

    # Try to get semantic scores
    semantic_scores = semantic_search(query, index)

    # Validate semantic scores length matches sessions
    if semantic_scores is not None and len(semantic_scores) != len(sessions):
        print(f"Warning: Semantic scores length mismatch ({len(semantic_scores)} vs {len(sessions)}). Falling back to BM25.", file=sys.stderr)
        semantic_scores = None

    # Calculate final scores
    results = []
    for i, session in enumerate(sessions):
        # Safely get BM25 scores with bounds checking
        if i < len(bm25_results):
            bm25_score = bm25_results[i].get('bm25_score', 0.0)
            temporal_score = bm25_results[i].get('temporal_score', 0.5)
            relevance_score = bm25_results[i].get('relevance_score', 0.0)
        else:
            # Fallback if bm25_results is shorter than expected
            bm25_score = 0.0
            temporal_score = 0.5
            relevance_score = 0.0

        if semantic_scores is not None:
            # Hybrid: 50% BM25 + 50% semantic
            try:
                semantic_score = semantic_scores[i]
                relevance_score = 0.5 * bm25_score + 0.5 * semantic_score

                results.append({
                    **session,
                    "relevance_score": float(relevance_score),
                    "bm25_score": float(bm25_score),
                    "semantic_score": float(semantic_score),
                    "temporal_score": float(temporal_score),
                    "search_mode": "hybrid"
                })
            except (IndexError, TypeError) as e:
                # Fall back to BM25 for this session if semantic score unavailable
                print(f"Warning: Failed to get semantic score for session {i}: {e}", file=sys.stderr)
                results.append({
                    **session,
                    "relevance_score": float(relevance_score),
                    "bm25_score": float(bm25_score),
                    "temporal_score": float(temporal_score),
                    "search_mode": "bm25"
                })
        else:
            # Fall back to BM25 + temporal (70/30 mix from bm25_search)
            results.append({
                **session,
                "relevance_score": float(relevance_score),
                "bm25_score": float(bm25_score),
                "temporal_score": float(temporal_score),
                "search_mode": "bm25"
            })

    return results


def simple_relevance_score(query: str, session: dict) -> float:
    """
    DEPRECATED: Legacy simple relevance score (kept for backward compatibility).
    Use bm25_search() instead.
    """
    query_lower = query.lower()
    query_terms = set(re.findall(r'\w+', query_lower))

    score = 0.0
    max_score = 0.0

    # Check summary (weight: 3)
    summary = session.get('summary', '').lower()
    max_score += 3
    if any(term in summary for term in query_terms):
        matching_terms = sum(1 for term in query_terms if term in summary)
        score += (matching_terms / len(query_terms)) * 3

    # Check topics (weight: 2)
    topics = [t.lower() for t in session.get('topics', [])]
    max_score += 2
    if any(term in topic for topic in topics for term in query_terms):
        matching_terms = sum(1 for term in query_terms if any(term in topic for topic in topics))
        score += (matching_terms / len(query_terms)) * 2

    # Check files modified (weight: 1)
    files = [f.lower() for f in session.get('files_modified', [])]
    max_score += 1
    if any(term in file for file in files for term in query_terms):
        matching_terms = sum(1 for term in query_terms if any(term in file for file in files))
        score += (matching_terms / len(query_terms)) * 1

    # Check beads issues (weight: 1)
    beads = [b.lower() for b in session.get('beads_issues', [])]
    max_score += 1
    if any(term in bead for bead in beads for term in query_terms):
        score += 1

    # Normalize to 0-1
    return score / max_score if max_score > 0 else 0

def run_quality_evaluation(event_id: str, query: str, results: list, search_config: dict):
    """
    Run quality evaluation in background thread.

    Args:
        event_id: Recall event ID
        query: Search query
        results: Search results
        search_config: Search configuration
    """
    try:
        # Import quality scorer
        from quality_scoring import QualityScorer

        # Initialize scorer
        scorer = QualityScorer()

        # Run async evaluation in new event loop
        asyncio.run(scorer.evaluate_async(
            event_id=event_id,
            query=query,
            results=results,
            config_dict=search_config
        ))

    except Exception as e:
        # Silently fail - don't crash on quality evaluation errors
        pass


def search_sessions(
    query: str,
    index_path: Path,
    scope: str = "all",
    session_filter: str = None,
    topics_filter: List[str] = None,
    limit: int = 5,
    use_bm25: bool = True,
    search_mode: str = "auto"
) -> List[Dict]:
    """
    Search session index and return ranked results.

    Args:
        query: Search query string
        index_path: Path to index.json
        scope: Search scope (all, decisions, code, discussions)
        session_filter: Filter by session date/id
        topics_filter: Filter by topics
        limit: Maximum number of results
        use_bm25: Use BM25 scoring (True) or legacy simple scoring (False)
        search_mode: Search mode ("auto", "hybrid", "bm25", "semantic", "simple")
            - "auto": Use hybrid if embeddings available, else BM25
            - "hybrid": Force hybrid BM25 + semantic (falls back to BM25 if unavailable)
            - "bm25": Use BM25 only
            - "semantic": Use semantic only (fails if unavailable)
            - "simple": Use legacy simple scoring

    Returns:
        List of sessions with relevance scores
    """
    # Initialize telemetry
    collector = get_collector()
    start_time = time.time()

    # Start telemetry event
    event_id = collector.start_event(
        event_type="recall_triggered",
        context={
            "trigger_source": "search_index",
            "trigger_mode": "manual",
            "session_id": get_current_session_id(),
            "query": {
                "raw_query": query,
                "query_length": len(query)
            },
            "search_config": {
                "mode": search_mode,
                "limit": limit,
                "filters": {
                    "scope": scope,
                    "session_filter": session_filter,
                    "topics_filter": topics_filter
                }
            }
        }
    )

    try:
        # Time: index load
        load_start = time.time()

        if not index_path.exists():
            collector.end_event(event_id, outcome={"success": False, "error": "index_not_found"})
            return []

        with open(index_path, 'r') as f:
            index = json.load(f)

        load_time_ms = (time.time() - load_start) * 1000

        # Store index path for embedding loading
        index['_index_path'] = str(index_path)

        sessions = index.get('sessions', [])

    # Apply filters first
        filter_start = time.time()
        filtered_sessions = sessions

        if session_filter:
            # Filter by session date/id
            filtered_sessions = [s for s in filtered_sessions if session_filter in s['id']]

        if topics_filter:
            # Filter by topics
            topics_lower = [t.lower() for t in topics_filter]
            filtered_sessions = [
                s for s in filtered_sessions
                if any(
                    topic.lower() in [t.lower() for t in s.get('topics', [])]
                    for topic in topics_lower
                )
            ]

        if scope != "all":
            # Scope-specific filtering (future enhancement)
            pass

        filter_time_ms = (time.time() - filter_start) * 1000

        # Create filtered index for search
        filtered_index = {
            'sessions': filtered_sessions,
            'bm25_index': index.get('bm25_index'),
            'embedding_index': index.get('embedding_index'),
            '_index_path': index.get('_index_path')
        }

        # Time: search computation
        search_start = time.time()

        # Determine mode_resolved for telemetry
        mode_resolved = search_mode

        # Choose search method based on mode
        if search_mode == "simple":
            # Legacy simple scoring
            mode_resolved = "simple"
            scored = [
                {**session, "relevance_score": simple_relevance_score(query, session), "search_mode": "simple"}
                for session in filtered_sessions
            ]
        elif search_mode == "semantic":
            # Semantic only (will fail if unavailable)
            mode_resolved = "semantic"
            semantic_scores = semantic_search(query, filtered_index)
            if semantic_scores is None:
                collector.end_event(event_id, outcome={
                    "success": False,
                    "error": "semantic_search_unavailable",
                    "error_type": "DependencyError"
                })
                print("ERROR: Semantic search unavailable. Install dependencies:", file=sys.stderr)
                print("  python3 -m pip install --user -r .claude/skills/recall/requirements-optional.txt", file=sys.stderr)
                print("  python3 .claude/skills/recall/scripts/embed_sessions.py", file=sys.stderr)
                return []

            scored = [
                {**session, "relevance_score": semantic_scores[i], "semantic_score": semantic_scores[i], "search_mode": "semantic"}
                for i, session in enumerate(filtered_sessions)
            ]
        elif search_mode in ("hybrid", "auto"):
            # Hybrid or auto mode
            has_embeddings = filtered_index.get('embedding_index') is not None and EMBEDDINGS_AVAILABLE

            if has_embeddings or search_mode == "hybrid":
                # Try hybrid search
                mode_resolved = "hybrid"
                scored = hybrid_search(query, filtered_index)
            else:
                # Fall back to BM25
                mode_resolved = "bm25"
                scored = bm25_search(query, filtered_index)
        elif search_mode == "bm25":
            # BM25 only
            mode_resolved = "bm25"
            if use_bm25 and filtered_index.get('bm25_index'):
                scored = bm25_search(query, filtered_index)
            else:
                # Fallback to simple scoring
                mode_resolved = "simple"
                scored = [
                    {**session, "relevance_score": simple_relevance_score(query, session), "search_mode": "simple"}
                    for session in filtered_sessions
                ]
        else:
            # Default: use BM25 if available
            if use_bm25 and filtered_index.get('bm25_index'):
                mode_resolved = "bm25"
                scored = bm25_search(query, filtered_index)
            else:
                mode_resolved = "simple"
                scored = [
                    {**session, "relevance_score": simple_relevance_score(query, session), "search_mode": "simple"}
                    for session in filtered_sessions
                ]

        search_time_ms = (time.time() - search_start) * 1000

        # Sort by relevance
        scored.sort(key=lambda s: s['relevance_score'], reverse=True)

        # Apply limit
        results = scored[:limit]

        # Collect result statistics
        if results:
            scores = [r['relevance_score'] for r in results]
            top_score = max(scores)
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)

            # Score distribution
            score_dist = {
                "high_0.7+": sum(1 for s in scores if s >= 0.7),
                "medium_0.4-0.7": sum(1 for s in scores if 0.4 <= s < 0.7),
                "low_<0.4": sum(1 for s in scores if s < 0.4)
            }
        else:
            top_score = avg_score = min_score = 0.0
            score_dist = {"high_0.7+": 0, "medium_0.4-0.7": 0, "low_<0.4": 0}

        # Get system state
        system_state = get_system_state(index_path)
        system_state['model_cached'] = EmbeddingCache()._model is not None

        # Calculate total latency
        total_time_ms = (time.time() - start_time) * 1000

        # Update telemetry with results and performance
        collector.update_event(event_id, {
            "search_config": {
                "mode_resolved": mode_resolved
            },
            "results": {
                "count": len(results),
                "retrieved_sessions": [r['id'] for r in results],
                "scores": {
                    "top_score": top_score,
                    "avg_score": avg_score,
                    "min_score": min_score,
                    "score_distribution": score_dist
                }
            },
            "performance": {
                "total_latency_ms": total_time_ms,
                "breakdown": {
                    "index_load_ms": load_time_ms,
                    "filter_ms": filter_time_ms,
                    "search_ms": search_time_ms
                },
                "cache_hit": False,  # No caching yet
                "model_loaded": system_state.get('model_cached', False)
            },
            "system_state": system_state
        })

        # End telemetry event
        collector.end_event(event_id, outcome={"success": True})

        # Trigger quality evaluation in background (non-blocking)
        if analytics_config.get('quality_scoring.enabled', False):
            # Fire background thread for async evaluation
            eval_thread = threading.Thread(
                target=run_quality_evaluation,
                args=(event_id, query, results, {
                    'mode': search_mode,
                    'mode_resolved': mode_resolved,
                    'limit': limit
                }),
                daemon=True  # Don't block program exit
            )
            eval_thread.start()
            # Don't wait for thread - return results immediately

        return results

    except Exception as e:
        # Handle errors
        collector.update_event(event_id, {
            "error": str(e),
            "error_type": type(e).__name__
        })
        collector.end_event(event_id, outcome={"success": False})
        raise  # Re-raise the exception

def main():
    parser = argparse.ArgumentParser(description='Search session index')
    parser.add_argument('--query', required=True, help='Search query')
    parser.add_argument('--index', default='.claude/context/sessions/index.json', help='Index file path')
    parser.add_argument('--scope', default='all', choices=['all', 'decisions', 'code', 'discussions'])
    parser.add_argument('--session', help='Filter by session date/id')
    parser.add_argument('--topics', help='Filter by topics (comma-separated)')
    parser.add_argument('--limit', type=int, default=5, help='Max results')
    parser.add_argument('--format', default='summary', choices=['summary', 'files', 'json'])
    parser.add_argument('--mode', default='auto', choices=['auto', 'hybrid', 'bm25', 'semantic', 'simple'],
                       help='Search mode (auto=hybrid if available, else BM25)')

    args = parser.parse_args()

    # Get collector for flush at end
    collector = get_collector()

    # Parse topics
    topics_filter = args.topics.split(',') if args.topics else None

    # Search
    index_path = Path(args.index)
    if not index_path.is_absolute():
        # Assume relative to project root
        index_path = Path.cwd() / index_path

    results = search_sessions(
        query=args.query,
        index_path=index_path,
        scope=args.scope,
        session_filter=args.session,
        topics_filter=topics_filter,
        limit=args.limit,
        search_mode=args.mode
    )

    # Output
    if args.format == 'json':
        print(json.dumps(results, indent=2, default=str))
    elif args.format == 'files':
        # Just output file paths for easy piping
        session_dir = index_path.parent
        for result in results:
            print(session_dir / result['file'])
    else:  # summary
        if not results:
            print("No matching sessions found.")
            sys.exit(0)

        print(f"Found {len(results)} matching session(s):\n")

        # Show search mode if available
        if results and 'search_mode' in results[0]:
            mode = results[0]['search_mode']
            mode_display = {
                'hybrid': 'Hybrid (BM25 + Semantic)',
                'bm25': 'BM25 + Temporal',
                'semantic': 'Semantic Only',
                'simple': 'Simple (Legacy)'
            }.get(mode, mode)
            print(f"Search mode: {mode_display}\n")

        for i, result in enumerate(results, 1):
            score = result['relevance_score']
            confidence = "HIGH" if score > 0.7 else "MEDIUM" if score > 0.4 else "LOW"

            print(f"{i}. Session: {result['id']}")
            print(f"   Relevance: {score:.2f} ({confidence})")

            # Show score breakdown if available
            if result.get('search_mode') == 'hybrid':
                print(f"   BM25: {result.get('bm25_score', 0):.2f} | "
                      f"Semantic: {result.get('semantic_score', 0):.2f} | "
                      f"Temporal: {result.get('temporal_score', 0.5):.2f}")
            elif 'bm25_score' in result:
                print(f"   BM25: {result['bm25_score']:.2f} | Temporal: {result.get('temporal_score', 0.5):.2f}")
            elif 'semantic_score' in result:
                print(f"   Semantic: {result['semantic_score']:.2f}")

            print(f"   Summary: {result['summary']}")
            print(f"   Topics: {', '.join(result['topics'])}")
            print(f"   File: {result['file']}")
            print()

    # Flush telemetry before exit
    collector.flush()

if __name__ == "__main__":
    main()
