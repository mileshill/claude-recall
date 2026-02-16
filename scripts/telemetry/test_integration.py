#!/usr/bin/env python3
"""
Integration tests for telemetry in search_index.py and smart_recall.py.

Verifies that telemetry events are logged correctly during real searches.
"""

import sys
import json
import tempfile
from pathlib import Path
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from search_index import search_sessions
from smart_recall import smart_recall, analyze_context
from telemetry.collector import get_collector
from metrics.config import config


def create_test_index(index_path: Path):
    """Create a minimal test index for testing."""
    index_data = {
        "version": "1.0.0",
        "generated_at": "2026-02-16T00:00:00Z",
        "sessions": [
            {
                "id": "test-session-1",
                "file": "test-1.md",
                "captured": "2026-02-16T00:00:00Z",
                "summary": "Authentication bug fix",
                "topics": ["auth", "bug-fix"],
                "files_modified": ["auth.py"],
                "beads_issues": [],
                "bm25_tokens": ["authentication", "bug", "fix"]
            }
        ],
        "bm25_index": {
            "doc_len": [3],
            "avgdl": 3.0,
            "doc_freqs": [{"authentication": 1, "bug": 1, "fix": 1}],
            "idf": {"authentication": 0.5, "bug": 0.5, "fix": 0.5}
        }
    }

    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, 'w') as f:
        json.dump(index_data, f)


def test_search_telemetry():
    """Test that search_sessions logs telemetry correctly."""
    print("Testing search_sessions telemetry...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        log_path = tmpdir_path / "analytics.jsonl"
        index_path = tmpdir_path / "index.json"

        # Setup
        create_test_index(index_path)
        config.set('telemetry.log_path', str(log_path))
        config.set('telemetry.batch_size', 1)  # Immediate flush

        # Reset collector
        collector = get_collector()
        collector._initialized = False
        collector.__init__()

        # Run search
        results = search_sessions(
            query="authentication",
            index_path=index_path,
            search_mode="bm25",
            limit=5
        )

        # Flush telemetry
        collector.flush()
        time.sleep(0.1)

        # Verify results
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"

        # Verify telemetry logged
        assert log_path.exists(), "Telemetry log should exist"

        with open(log_path) as f:
            events = [json.loads(line) for line in f]

        assert len(events) >= 1, f"Expected at least 1 event, got {len(events)}"

        # Find recall_triggered event
        recall_events = [e for e in events if e.get('event_type') == 'recall_triggered']
        assert len(recall_events) >= 1, "Should have recall_triggered event"

        event = recall_events[0]

        # Check required fields
        assert 'event_id' in event
        assert 'timestamp' in event
        assert event['event_type'] == 'recall_triggered'
        assert event['trigger_source'] == 'search_index'

        # Check query data
        assert 'query' in event
        assert event['query']['raw_query'] == 'authentication'
        assert event['query']['query_length'] == 14

        # Check search config
        assert 'search_config' in event
        assert event['search_config']['mode'] == 'bm25'
        assert event['search_config']['mode_resolved'] == 'bm25'
        assert event['search_config']['limit'] == 5

        # Check results
        assert 'results' in event
        assert event['results']['count'] == 1
        assert event['results']['retrieved_sessions'] == ['test-session-1']
        assert 'scores' in event['results']
        assert 'top_score' in event['results']['scores']

        # Check performance
        assert 'performance' in event
        assert 'total_latency_ms' in event['performance']
        assert 'breakdown' in event['performance']
        assert 'index_load_ms' in event['performance']['breakdown']
        assert 'search_ms' in event['performance']['breakdown']

        # Check system state
        assert 'system_state' in event
        assert event['system_state']['index_size'] == 1

        # Check outcome
        assert 'outcome' in event
        assert event['outcome']['success'] is True

    print("✓ Search telemetry test passed")


def test_smart_recall_telemetry():
    """Test that smart_recall logs telemetry correctly."""
    print("Testing smart_recall telemetry...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        log_path = tmpdir_path / "analytics.jsonl"
        index_path = tmpdir_path / "index.json"

        # Setup
        create_test_index(index_path)
        config.set('telemetry.log_path', str(log_path))
        config.set('telemetry.batch_size', 1)

        # Reset collector
        collector = get_collector()
        collector._initialized = False
        collector.__init__()

        # Run smart recall
        results = smart_recall(
            context_text="Working on authentication bug fix",
            index_path=index_path,
            search_mode="bm25",
            limit=3,
            verbose=False
        )

        # Flush telemetry
        collector.flush()
        time.sleep(0.1)

        # Verify telemetry logged
        assert log_path.exists(), "Telemetry log should exist"

        with open(log_path) as f:
            events = [json.loads(line) for line in f]

        # Should have: context_analyzed, recall_triggered, smart_recall_completed
        assert len(events) >= 2, f"Expected at least 2 events, got {len(events)}"

        # Check context_analyzed event
        context_events = [e for e in events if e.get('event_type') == 'context_analyzed']
        assert len(context_events) >= 1, "Should have context_analyzed event"

        ctx_event = context_events[0]
        assert ctx_event['trigger_source'] == 'smart_recall'
        assert 'context' in ctx_event
        assert 'keywords' in ctx_event['context']
        assert 'technical_terms' in ctx_event['context']
        assert 'search_query' in ctx_event['context']

        # Check smart_recall_completed event
        completion_events = [e for e in events if e.get('event_type') == 'smart_recall_completed']
        assert len(completion_events) >= 1, "Should have smart_recall_completed event"

        comp_event = completion_events[0]
        assert 'query' in comp_event
        assert 'extracted_keywords' in comp_event['query']
        assert 'technical_terms' in comp_event['query']
        assert 'results' in comp_event
        assert 'count' in comp_event['results']
        assert 'performance' in comp_event
        assert 'breakdown' in comp_event['performance']

    print("✓ Smart recall telemetry test passed")


def test_context_analysis():
    """Test context analysis extracts correct data."""
    print("Testing context analysis...")

    context = "Working on JWT authentication bug fix for the login system"

    analysis = analyze_context(context)

    # Check structure
    assert 'keywords' in analysis
    assert 'tech_terms' in analysis
    assert 'search_query' in analysis

    # Check content
    assert len(analysis['keywords']) > 0
    assert len(analysis['tech_terms']) > 0
    assert len(analysis['search_query']) > 0

    # JWT should be detected as technical term
    assert 'jwt' in [t.lower() for t in analysis['tech_terms']]

    # Authentication should be in keywords or tech terms
    all_terms = set(analysis['keywords']) | set(analysis['tech_terms'])
    assert 'authentication' in [t.lower() for t in all_terms]

    print("✓ Context analysis test passed")


def test_error_telemetry():
    """Test that errors are logged in telemetry."""
    print("Testing error telemetry...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        log_path = tmpdir_path / "analytics.jsonl"
        index_path = tmpdir_path / "nonexistent.json"  # Doesn't exist

        # Setup
        config.set('telemetry.log_path', str(log_path))
        config.set('telemetry.batch_size', 1)

        # Reset collector
        collector = get_collector()
        collector._initialized = False
        collector.__init__()

        # Run search with missing index
        results = search_sessions(
            query="test",
            index_path=index_path,
            search_mode="bm25",
            limit=5
        )

        # Should return empty results
        assert len(results) == 0

        # Flush telemetry
        collector.flush()
        time.sleep(0.1)

        # Verify error logged
        assert log_path.exists(), "Telemetry log should exist"

        with open(log_path) as f:
            events = [json.loads(line) for line in f]

        assert len(events) >= 1, "Should have at least one event"

        event = events[0]
        assert event['outcome']['success'] is False
        assert 'error' in event['outcome']

    print("✓ Error telemetry test passed")


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Telemetry Integration Tests")
    print("=" * 60 + "\n")

    tests = [
        test_context_analysis,
        test_search_telemetry,
        test_smart_recall_telemetry,
        test_error_telemetry
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
            print()
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    print("=" * 60)
    print(f"Tests: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
