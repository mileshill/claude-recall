#!/usr/bin/env python3
"""
Tests for impact analysis system.

Tests detection, scoring, metrics, and integration.
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from impact_analysis import (
    ContextUsageDetector,
    ContinuityScorer,
    EfficiencyMetrics,
    ImpactAnalyzer
)


def test_explicit_citation_detection():
    """Test explicit citation detection."""
    print("Testing explicit citation detection...")

    detector = ContextUsageDetector()

    # Test transcript with explicit citations
    transcript = """
    As we discussed in the previous session, we need to fix the authentication bug.
    Like last time, we'll use JWT tokens for this.
    Continuing from our earlier work on the login flow.
    """

    citations = detector.detect_explicit_citations(transcript)

    assert len(citations) > 0, "Should detect citations"
    assert any('previous session' in c['text'].lower() for c in citations)

    print("✓ Explicit citation detection test passed")


def test_implicit_usage_detection():
    """Test implicit usage detection via term overlap."""
    print("Testing implicit usage detection...")

    detector = ContextUsageDetector()

    current_transcript = "Working on JWT authentication and OAuth integration"

    recalled_sessions = [
        {
            'id': 'session-1',
            'summary': 'Implemented JWT token authentication',
            'topics': ['authentication', 'jwt', 'security']
        }
    ]

    implicit = detector.detect_implicit_usage(current_transcript, recalled_sessions)

    assert 'term_overlap' in implicit
    assert 'jwt' in [t.lower() for t in implicit['term_overlap']]
    assert 'authentication' in [t.lower() for t in implicit['keyword_overlap']]
    assert implicit['total_similarity'] > 0

    print("✓ Implicit usage detection test passed")


def test_reused_topics():
    """Test reused topic detection."""
    print("Testing reused topics detection...")

    detector = ContextUsageDetector()

    current_transcript = "Working on authentication and adding security features"

    recalled_sessions = [
        {
            'id': 'session-1',
            'topics': ['authentication', 'security']
        }
    ]

    reused = detector.detect_reused_topics(current_transcript, recalled_sessions)

    assert len(reused) >= 2, "Should detect both topics"
    topic_names = [r['topic'] for r in reused]
    assert 'authentication' in topic_names
    assert 'security' in topic_names

    print("✓ Reused topics detection test passed")


def test_file_references():
    """Test file reference detection."""
    print("Testing file reference detection...")

    detector = ContextUsageDetector()

    current_transcript = "Modified auth.py and added tests in test_auth.py"

    recalled_sessions = [
        {
            'id': 'session-1',
            'files_modified': ['src/auth.py', 'tests/test_auth.py']
        }
    ]

    file_refs = detector.detect_file_references(current_transcript, recalled_sessions)

    assert len(file_refs) >= 2, "Should detect both files"
    filenames = [r['filename'] for r in file_refs]
    assert 'auth.py' in filenames
    assert 'test_auth.py' in filenames

    print("✓ File reference detection test passed")


def test_usage_score_calculation():
    """Test usage score calculation."""
    print("Testing usage score calculation...")

    detector = ContextUsageDetector()

    # Create test data
    explicit_citations = [{'text': 'as discussed previously'}]
    implicit_usage = {
        'total_similarity': 0.6,
        'term_overlap_count': 5,
        'keyword_overlap_count': 3
    }
    reused_topics = [
        {'topic': 'auth'},
        {'topic': 'security'}
    ]
    file_references = [
        {'file': 'auth.py'}
    ]

    score = detector.calculate_usage_score(
        explicit_citations,
        implicit_usage,
        reused_topics,
        file_references
    )

    assert 'total_score' in score
    assert 0 <= score['total_score'] <= 1
    assert score['component_scores']['explicit'] > 0
    assert score['component_scores']['implicit'] > 0
    assert score['component_scores']['topics'] > 0
    assert score['component_scores']['files'] > 0

    print("✓ Usage score calculation test passed")


def test_continuity_scoring():
    """Test continuity scoring."""
    print("Testing continuity scoring...")

    scorer = ContinuityScorer()

    current_transcript = "Working on JWT authentication bug fix"

    recalled_sessions = [
        {
            'id': 'session-1',
            'captured': '2026-02-15T00:00:00Z',
            'summary': 'Fixed authentication issues with JWT tokens',
            'topics': ['authentication', 'jwt', 'bug-fix']
        }
    ]

    current_time = datetime(2026, 2, 16, tzinfo=timezone.utc)

    scores = scorer.score_continuity(
        current_transcript,
        recalled_sessions,
        current_time
    )

    assert 'total_score' in scores
    assert 'temporal_score' in scores
    assert 'terminology_score' in scores
    assert 'approach_score' in scores
    assert 0 <= scores['total_score'] <= 1
    assert scores['terminology_score'] > 0  # Should have term overlap

    print("✓ Continuity scoring test passed")


def test_efficiency_metrics():
    """Test efficiency metrics calculation."""
    print("Testing efficiency metrics...")

    metrics = EfficiencyMetrics()

    session_data = {
        'summary': 'Fixed authentication bug',
        'topics': ['authentication', 'bug-fix']
    }

    recalled_sessions = [
        {
            'id': 'session-1',
            'summary': 'Working on authentication',
            'topics': ['authentication'],
            'relevance_score': 0.8
        }
    ]

    efficiency = metrics.calculate_efficiency_gain(session_data, recalled_sessions)

    assert 'efficiency_score' in efficiency
    assert 'estimated_time_saved_minutes' in efficiency
    assert 'repetition_avoided' in efficiency
    assert 'context_switching_score' in efficiency
    assert efficiency['estimated_time_saved_minutes'] > 0
    assert 0 <= efficiency['efficiency_score'] <= 1

    print("✓ Efficiency metrics test passed")


def test_productivity_metrics():
    """Test productivity metrics calculation."""
    print("Testing productivity metrics...")

    metrics = EfficiencyMetrics()

    session_sequence = [
        {
            'summary': 'Started authentication feature',
            'topics': ['authentication'],
            'files_modified': ['auth.py']
        },
        {
            'summary': 'Completed authentication feature',
            'topics': ['authentication', 'testing'],
            'files_modified': ['auth.py', 'test_auth.py']
        },
        {
            'summary': 'Fixed authentication bugs',
            'topics': ['authentication', 'bug-fix'],
            'files_modified': ['auth.py']
        }
    ]

    productivity = metrics.calculate_productivity_metrics(session_sequence)

    assert 'files_modified_per_session' in productivity
    assert 'completion_rate' in productivity
    assert 'productivity_trend' in productivity
    assert productivity['total_sessions'] == 3
    assert productivity['files_modified_per_session'] > 0

    print("✓ Productivity metrics test passed")


def test_learning_curve():
    """Test learning curve calculation."""
    print("Testing learning curve...")

    metrics = EfficiencyMetrics()

    session_sequence = [
        {
            'topics': ['authentication', 'jwt']
        },
        {
            'topics': ['authentication', 'oauth']
        },
        {
            'topics': ['authentication', 'jwt', 'oauth']
        }
    ]

    learning = metrics.calculate_learning_curve(session_sequence)

    assert 'learning_rate' in learning
    assert 'mastery_indicators' in learning
    assert 'knowledge_retention' in learning
    assert learning['total_unique_topics'] == 3
    assert 'authentication' in learning['mastery_indicators']  # Appears in all 3

    print("✓ Learning curve test passed")


def test_impact_analyzer():
    """Test complete impact analysis."""
    print("Testing impact analyzer...")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "impact.jsonl"

        analyzer = ImpactAnalyzer(log_path=log_path)

        # Test data
        current_transcript = """
        As we discussed in the previous session, I need to fix the authentication bug.
        I'll use JWT tokens like we did last time. The auth.py file needs updating.
        """

        recalled_sessions = [
            {
                'id': 'session-1',
                'captured': '2026-02-15T00:00:00Z',
                'summary': 'Implemented JWT authentication',
                'topics': ['authentication', 'jwt', 'security'],
                'files_modified': ['src/auth.py'],
                'relevance_score': 0.9
            }
        ]

        session_data = {
            'timestamp': '2026-02-16T00:00:00Z',
            'summary': 'Fixed authentication bug',
            'topics': ['authentication', 'bug-fix']
        }

        # Run analysis
        result = analyzer.analyze_recall_event(
            recall_event_id='test-event-1',
            current_transcript=current_transcript,
            recalled_sessions=recalled_sessions,
            session_data=session_data
        )

        # Verify result structure
        assert 'recall_event_id' in result
        assert result['recall_event_id'] == 'test-event-1'
        assert result['recall_used'] is True
        assert 'impact_score' in result
        assert 0 <= result['impact_score'] <= 1
        assert 'usage_analysis' in result
        assert 'continuity_scores' in result
        assert 'efficiency_metrics' in result

        # Verify log was written
        assert log_path.exists()
        with open(log_path) as f:
            lines = f.readlines()
            assert len(lines) == 1
            logged = json.loads(lines[0])
            assert logged['recall_event_id'] == 'test-event-1'

    print("✓ Impact analyzer test passed")


def test_summary_report():
    """Test summary report generation."""
    print("Testing summary report generation...")

    analyzer = ImpactAnalyzer()

    impact_analyses = [
        {
            'recall_used': True,
            'impact_score': 0.8,
            'efficiency_metrics': {'estimated_time_saved_minutes': 5.0}
        },
        {
            'recall_used': True,
            'impact_score': 0.6,
            'efficiency_metrics': {'estimated_time_saved_minutes': 3.0}
        },
        {
            'recall_used': False,
            'impact_score': 0.2,
            'efficiency_metrics': {'estimated_time_saved_minutes': 0.0}
        }
    ]

    report = analyzer.generate_summary_report(impact_analyses)

    assert 'Total Analyses: 3' in report
    assert 'Usage Rate' in report
    assert 'Impact Score' in report
    assert 'Time Saved' in report

    print("✓ Summary report test passed")


def test_no_recalls():
    """Test handling of no recalled sessions."""
    print("Testing no recalls scenario...")

    analyzer = ImpactAnalyzer()

    result = analyzer.analyze_recall_event(
        recall_event_id='test-no-recall',
        current_transcript='Some work',
        recalled_sessions=[],
        session_data={}
    )

    assert result['recall_used'] is False
    assert result['impact_score'] == 0.0

    print("✓ No recalls test passed")


def run_all_tests():
    """Run all impact analysis tests."""
    print("=" * 60)
    print("Running Impact Analysis Tests")
    print("=" * 60 + "\n")

    tests = [
        test_explicit_citation_detection,
        test_implicit_usage_detection,
        test_reused_topics,
        test_file_references,
        test_usage_score_calculation,
        test_continuity_scoring,
        test_efficiency_metrics,
        test_productivity_metrics,
        test_learning_curve,
        test_impact_analyzer,
        test_summary_report,
        test_no_recalls
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
