#!/usr/bin/env python3
"""
Test BM25 search implementation.
Verifies indexing, search, and relevance scoring.
"""

import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from search_index import search_sessions, tokenize_query


def test_tokenization():
    """Test query tokenization."""
    print("Testing tokenization...")
    query = "RLM implementation context-management"
    tokens = tokenize_query(query)
    expected = ['rlm', 'implementation', 'context', 'management']
    assert tokens == expected, f"Expected {expected}, got {tokens}"
    print("  ✓ Tokenization works correctly")


def test_bm25_search():
    """Test BM25 search returns results."""
    print("\nTesting BM25 search...")
    index_path = Path('.claude/context/sessions/index.json')

    if not index_path.exists():
        print("  ⚠ Index not found, skipping test")
        return

    # Test query
    results = search_sessions(
        query="RLM implementation",
        index_path=index_path,
        limit=5,
        use_bm25=True
    )

    assert len(results) > 0, "No results returned"
    assert all('relevance_score' in r for r in results), "Missing relevance scores"
    assert all('bm25_score' in r for r in results), "Missing BM25 scores"
    assert all('temporal_score' in r for r in results), "Missing temporal scores"

    # Check scores are normalized 0-1
    for r in results:
        assert 0 <= r['relevance_score'] <= 1, f"Invalid relevance: {r['relevance_score']}"
        assert 0 <= r['bm25_score'] <= 1, f"Invalid BM25: {r['bm25_score']}"
        assert 0 <= r['temporal_score'] <= 1, f"Invalid temporal: {r['temporal_score']}"

    print(f"  ✓ BM25 search returned {len(results)} results")
    print(f"  ✓ Top result: {results[0]['id']} (score: {results[0]['relevance_score']:.3f})")


def test_relevance_ranking():
    """Test that relevant results rank higher."""
    print("\nTesting relevance ranking...")
    index_path = Path('.claude/context/sessions/index.json')

    if not index_path.exists():
        print("  ⚠ Index not found, skipping test")
        return

    # Query specifically for RLM
    results = search_sessions(
        query="RLM context memory system",
        index_path=index_path,
        limit=5,
        use_bm25=True
    )

    # The RLM implementation session should rank first
    if results:
        top_result = results[0]
        assert 'rlm' in top_result.get('topics', []), \
            f"Top result should be RLM-related, got {top_result['id']}"
        print(f"  ✓ Most relevant result ranked first: {top_result['id']}")

    # Check scores are descending
    scores = [r['relevance_score'] for r in results]
    assert scores == sorted(scores, reverse=True), "Results not sorted by relevance"
    print(f"  ✓ Results properly sorted by relevance")


def test_backward_compatibility():
    """Test that legacy search still works."""
    print("\nTesting backward compatibility...")
    index_path = Path('.claude/context/sessions/index.json')

    if not index_path.exists():
        print("  ⚠ Index not found, skipping test")
        return

    # Test legacy search
    results = search_sessions(
        query="RLM",
        index_path=index_path,
        limit=5,
        use_bm25=False
    )

    assert len(results) > 0, "Legacy search returned no results"
    assert all('relevance_score' in r for r in results), "Missing relevance scores"

    print(f"  ✓ Legacy search still works ({len(results)} results)")


def test_index_structure():
    """Test that index has correct structure."""
    print("\nTesting index structure...")
    index_path = Path('.claude/context/sessions/index.json')

    if not index_path.exists():
        print("  ⚠ Index not found, skipping test")
        return

    with open(index_path, 'r') as f:
        index = json.load(f)

    # Check required fields
    assert 'sessions' in index, "Missing 'sessions' field"
    assert 'last_updated' in index, "Missing 'last_updated' field"
    assert 'bm25_index' in index, "Missing 'bm25_index' field"

    # Check BM25 index structure
    bm25 = index['bm25_index']
    if bm25:
        assert 'doc_len' in bm25, "Missing 'doc_len' in BM25 index"
        assert 'avgdl' in bm25, "Missing 'avgdl' in BM25 index"
        assert 'doc_freqs' in bm25, "Missing 'doc_freqs' in BM25 index"
        assert 'idf' in bm25, "Missing 'idf' in BM25 index"
        assert 'session_ids' in bm25, "Missing 'session_ids' in BM25 index"

    # Check sessions have BM25 tokens
    for session in index['sessions']:
        assert 'bm25_tokens' in session, f"Session {session['id']} missing bm25_tokens"
        assert isinstance(session['bm25_tokens'], list), "bm25_tokens should be a list"

    print(f"  ✓ Index structure is valid")
    print(f"  ✓ {len(index['sessions'])} sessions indexed")
    print(f"  ✓ BM25 index has {len(bm25['idf'])} unique terms")


def test_performance():
    """Test search performance."""
    print("\nTesting performance...")
    import time
    index_path = Path('.claude/context/sessions/index.json')

    if not index_path.exists():
        print("  ⚠ Index not found, skipping test")
        return

    # Warm up
    search_sessions('test', index_path, limit=5)

    # Benchmark
    queries = ['RLM', 'auto capture', 'context', 'session', 'testing']
    times = []

    for query in queries:
        start = time.time()
        search_sessions(query, index_path, limit=5)
        elapsed = (time.time() - start) * 1000  # ms
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    max_time = max(times)

    assert avg_time < 100, f"Search too slow: {avg_time:.2f}ms avg"
    assert max_time < 100, f"Search too slow: {max_time:.2f}ms max"

    print(f"  ✓ Average search time: {avg_time:.2f}ms")
    print(f"  ✓ Max search time: {max_time:.2f}ms")
    print(f"  ✓ Performance target met (< 100ms)")


def main():
    """Run all tests."""
    print("=" * 60)
    print("BM25 Search Implementation Tests")
    print("=" * 60)

    tests = [
        test_tokenization,
        test_index_structure,
        test_bm25_search,
        test_relevance_ranking,
        test_backward_compatibility,
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
