#!/usr/bin/env python3
"""
Test semantic search implementation.
Verifies embedding generation, semantic search, and hybrid search.
"""

import json
import sys
from pathlib import Path
import tempfile
import shutil

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

# Check if optional dependencies are available
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠ sentence-transformers not installed. Skipping semantic search tests.")
    print("Install with: python3 -m pip install --user -r .claude/skills/recall/requirements-optional.txt")
    sys.exit(0)

from embed_sessions import EmbeddingGenerator
from search_index import (
    search_sessions,
    semantic_search,
    hybrid_search,
    EmbeddingCache
)


def create_test_index(test_dir: Path) -> Path:
    """Create a test index with sample sessions."""
    index_path = test_dir / "index.json"

    sessions = [
        {
            "id": "2026-02-15_session1",
            "file": "2026-02-15_session1.md",
            "summary": "Implemented RLM context memory system with auto-capture",
            "topics": ["rlm", "context", "memory"],
            "files_modified": ["auto_capture.py", "index_session.py"],
            "beads_issues": ["beads-001"],
            "bm25_tokens": ["implemented", "rlm", "context", "memory", "system", "auto", "capture"],
            "captured": "2026-02-15T10:00:00Z",
            "timestamp": "2026-02-15",
            "needs_embedding": True,
            "has_embedding": False
        },
        {
            "id": "2026-02-14_session2",
            "file": "2026-02-14_session2.md",
            "summary": "Added BM25 search with temporal scoring",
            "topics": ["search", "bm25", "ranking"],
            "files_modified": ["search_index.py"],
            "beads_issues": ["beads-002"],
            "bm25_tokens": ["added", "bm25", "search", "temporal", "scoring"],
            "captured": "2026-02-14T10:00:00Z",
            "timestamp": "2026-02-14",
            "needs_embedding": True,
            "has_embedding": False
        },
        {
            "id": "2026-02-13_session3",
            "file": "2026-02-13_session3.md",
            "summary": "Fixed bug in secret redaction system",
            "topics": ["security", "redaction", "bugfix"],
            "files_modified": ["redact_secrets.py"],
            "beads_issues": [],
            "bm25_tokens": ["fixed", "bug", "secret", "redaction", "system"],
            "captured": "2026-02-13T10:00:00Z",
            "timestamp": "2026-02-13",
            "needs_embedding": True,
            "has_embedding": False
        },
    ]

    index = {
        "sessions": sessions,
        "last_updated": "2026-02-15T10:00:00Z",
        "bm25_index": {
            "doc_len": [7, 5, 5],
            "avgdl": 5.67,
            "doc_freqs": {},
            "idf": {},
            "session_ids": ["2026-02-15_session1", "2026-02-14_session2", "2026-02-13_session3"]
        }
    }

    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

    return index_path


def test_embedding_generation():
    """Test embedding generation for sessions."""
    print("Testing embedding generation...")

    sessions = [
        {
            "summary": "Implemented RLM context memory system",
            "topics": ["rlm", "context"],
            "files_modified": ["auto_capture.py"],
            "beads_issues": []
        },
        {
            "summary": "Added BM25 search",
            "topics": ["search", "bm25"],
            "files_modified": ["search_index.py"],
            "beads_issues": []
        }
    ]

    generator = EmbeddingGenerator()
    embeddings = generator.generate_embeddings(sessions, show_progress=False)

    # Check shape
    assert embeddings.shape[0] == 2, f"Expected 2 embeddings, got {embeddings.shape[0]}"
    assert embeddings.shape[1] == 384, f"Expected 384 dimensions, got {embeddings.shape[1]}"

    # Check normalization (embeddings should have unit norm)
    norms = np.linalg.norm(embeddings, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5), f"Embeddings not normalized: {norms}"

    # Check embeddings are different
    similarity = np.dot(embeddings[0], embeddings[1])
    assert similarity < 0.99, "Embeddings are too similar (might be identical)"

    print(f"  ✓ Generated {len(embeddings)} embeddings")
    print(f"  ✓ Shape: {embeddings.shape}")
    print(f"  ✓ Normalized: {np.allclose(norms, 1.0)}")
    print(f"  ✓ Similarity: {similarity:.3f}")


def test_semantic_search():
    """Test semantic search returns relevant results."""
    print("\nTesting semantic search...")

    # Create temp directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        # Create test index
        index_path = create_test_index(test_dir)

        # Load index
        with open(index_path, 'r') as f:
            index = json.load(f)

        # Generate embeddings
        generator = EmbeddingGenerator()
        sessions = index['sessions']
        embeddings = generator.generate_embeddings(sessions, show_progress=False)

        # Save embeddings
        embedding_path = test_dir / "embeddings.npz"
        np.savez_compressed(embedding_path, embeddings=embeddings)

        # Add embedding metadata to index
        index['embedding_index'] = {
            'model': 'all-MiniLM-L6-v2',
            'embedding_dim': 384,
            'embedding_file': 'embeddings.npz'
        }
        index['_index_path'] = str(index_path)

        # Test semantic search
        cache = EmbeddingCache()
        scores = semantic_search("RLM memory context system", index, cache)

        assert scores is not None, "Semantic search returned None"
        assert len(scores) == 3, f"Expected 3 scores, got {len(scores)}"
        assert all(0 <= s <= 1 for s in scores), "Scores not in 0-1 range"

        # Check that RLM session has highest score
        assert scores[0] > scores[1], "RLM session should score highest"
        assert scores[0] > scores[2], "RLM session should score highest"

        print(f"  ✓ Semantic search returned {len(scores)} scores")
        print(f"  ✓ Top score: {scores[0]:.3f} (RLM session)")
        print(f"  ✓ Scores: {[f'{s:.3f}' for s in scores]}")


def test_hybrid_search():
    """Test hybrid search combines BM25 and semantic."""
    print("\nTesting hybrid search...")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        index_path = create_test_index(test_dir)

        # Load index
        with open(index_path, 'r') as f:
            index = json.load(f)

        # Generate embeddings
        generator = EmbeddingGenerator()
        sessions = index['sessions']
        embeddings = generator.generate_embeddings(sessions, show_progress=False)

        # Save embeddings
        embedding_path = test_dir / "embeddings.npz"
        np.savez_compressed(embedding_path, embeddings=embeddings)

        # Add embedding metadata
        index['embedding_index'] = {
            'model': 'all-MiniLM-L6-v2',
            'embedding_dim': 384,
            'embedding_file': 'embeddings.npz'
        }
        index['_index_path'] = str(index_path)

        # Test hybrid search
        results = hybrid_search("context memory system", index)

        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        assert all('relevance_score' in r for r in results), "Missing relevance scores"
        assert all('bm25_score' in r for r in results), "Missing BM25 scores"
        assert all('semantic_score' in r for r in results), "Missing semantic scores"
        assert all('search_mode' in r for r in results), "Missing search mode"
        assert results[0]['search_mode'] == 'hybrid', "Search mode should be hybrid"

        print(f"  ✓ Hybrid search returned {len(results)} results")
        print(f"  ✓ Top result: {results[0]['id']}")
        print(f"  ✓ Relevance: {results[0]['relevance_score']:.3f}")
        print(f"  ✓ BM25: {results[0]['bm25_score']:.3f} | Semantic: {results[0]['semantic_score']:.3f}")


def test_search_modes():
    """Test different search modes."""
    print("\nTesting search modes...")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        index_path = create_test_index(test_dir)

        # Load index
        with open(index_path, 'r') as f:
            index = json.load(f)

        # Generate embeddings
        generator = EmbeddingGenerator()
        sessions = index['sessions']
        embeddings = generator.generate_embeddings(sessions, show_progress=False)

        # Save embeddings
        embedding_path = test_dir / "embeddings.npz"
        np.savez_compressed(embedding_path, embeddings=embeddings)

        # Save index with embedding metadata
        index['embedding_index'] = {
            'model': 'all-MiniLM-L6-v2',
            'embedding_dim': 384,
            'embedding_file': 'embeddings.npz'
        }
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)

        # Test auto mode (should use hybrid)
        results_auto = search_sessions("context memory", index_path, search_mode="auto", limit=3)
        assert len(results_auto) > 0, "Auto mode returned no results"
        assert results_auto[0].get('search_mode') == 'hybrid', f"Auto mode should use hybrid, got {results_auto[0].get('search_mode')}"

        # Test BM25 mode
        results_bm25 = search_sessions("context memory", index_path, search_mode="bm25", limit=3)
        assert len(results_bm25) > 0, "BM25 mode returned no results"
        assert results_bm25[0].get('search_mode') == 'bm25', "BM25 mode incorrect"

        # Test hybrid mode
        results_hybrid = search_sessions("context memory", index_path, search_mode="hybrid", limit=3)
        assert len(results_hybrid) > 0, "Hybrid mode returned no results"
        assert results_hybrid[0].get('search_mode') == 'hybrid', "Hybrid mode incorrect"

        print(f"  ✓ Auto mode: {results_auto[0]['search_mode']}")
        print(f"  ✓ BM25 mode: {results_bm25[0]['search_mode']}")
        print(f"  ✓ Hybrid mode: {results_hybrid[0]['search_mode']}")


def test_graceful_fallback():
    """Test graceful fallback when embeddings unavailable."""
    print("\nTesting graceful fallback...")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        index_path = create_test_index(test_dir)

        # Don't create embeddings - test fallback

        # Test auto mode (should fall back to BM25)
        results = search_sessions("context memory", index_path, search_mode="auto", limit=3)
        assert len(results) > 0, "Auto mode with no embeddings returned no results"
        assert results[0].get('search_mode') != 'hybrid', "Should fall back from hybrid"

        # Test semantic mode (should fail gracefully)
        results_semantic = search_sessions("context memory", index_path, search_mode="semantic", limit=3)
        assert len(results_semantic) == 0, "Semantic mode should return empty when unavailable"

        print(f"  ✓ Auto mode fell back to: {results[0].get('search_mode', 'unknown')}")
        print(f"  ✓ Semantic mode returned: {len(results_semantic)} results (expected 0)")


def test_performance():
    """Test search performance with embeddings."""
    print("\nTesting performance...")
    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        index_path = create_test_index(test_dir)

        # Load and generate embeddings
        with open(index_path, 'r') as f:
            index = json.load(f)

        generator = EmbeddingGenerator()
        sessions = index['sessions']
        embeddings = generator.generate_embeddings(sessions, show_progress=False)

        embedding_path = test_dir / "embeddings.npz"
        np.savez_compressed(embedding_path, embeddings=embeddings)

        index['embedding_index'] = {
            'model': 'all-MiniLM-L6-v2',
            'embedding_dim': 384,
            'embedding_file': 'embeddings.npz'
        }
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)

        # Warm up
        search_sessions("test", index_path, search_mode="hybrid", limit=3)

        # Benchmark
        queries = ['context memory', 'search ranking', 'security bug']
        times = []

        for query in queries:
            start = time.time()
            search_sessions(query, index_path, search_mode="hybrid", limit=3)
            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # More lenient for first run (model loading)
        assert avg_time < 200, f"Search too slow: {avg_time:.2f}ms avg"
        assert max_time < 300, f"Search too slow: {max_time:.2f}ms max"

        print(f"  ✓ Average search time: {avg_time:.2f}ms")
        print(f"  ✓ Max search time: {max_time:.2f}ms")
        print(f"  ✓ Performance acceptable (< 200ms avg)")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Semantic Search Implementation Tests")
    print("=" * 60)

    if not EMBEDDINGS_AVAILABLE:
        return

    tests = [
        test_embedding_generation,
        test_semantic_search,
        test_hybrid_search,
        test_search_modes,
        test_graceful_fallback,
        test_performance,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
