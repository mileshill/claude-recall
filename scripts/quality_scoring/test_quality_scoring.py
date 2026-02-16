#!/usr/bin/env python3
"""
Tests for quality scoring system.

Tests cost tracking, heuristic scoring, LLM evaluation, and integration.
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quality_scoring import (
    CostTracker,
    HeuristicScorer,
    QualityScorer,
    QualityEvaluationPrompts
)


def test_cost_calculation():
    """Test cost calculation for API calls."""
    print("Testing cost calculation...")

    tracker = CostTracker()

    # Test Haiku pricing
    cost = tracker.calculate_cost(
        'claude-3-haiku-20240307',
        input_tokens=1000,
        output_tokens=500
    )

    # Expected: (1000/1M * 0.25) + (500/1M * 1.25)
    # = 0.00025 + 0.000625 = 0.000875
    expected = 0.000875
    assert abs(cost - expected) < 0.000001, f"Expected {expected}, got {cost}"

    print("✓ Cost calculation test passed")


def test_budget_checking():
    """Test budget enforcement."""
    print("Testing budget checking...")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "scores.jsonl"

        # Write some test costs
        with open(log_path, 'w') as f:
            current_month = datetime.now(timezone.utc).strftime('%Y-%m')
            # Write 3 entries with $2 each
            for i in range(3):
                entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'cost_usd': 2.0
                }
                f.write(json.dumps(entry) + '\n')

        tracker = CostTracker(log_path)

        # Check against $5 budget (should be exceeded - $6 spent)
        within, current, remaining = tracker.check_budget(5.0)
        assert not within, "Should exceed $5 budget"
        assert abs(current - 6.0) < 0.01, f"Expected $6, got ${current}"
        assert remaining < 0, f"Should have negative remaining"

        # Check against $10 budget (should be within)
        within, current, remaining = tracker.check_budget(10.0)
        assert within, "Should be within $10 budget"
        assert remaining > 0, "Should have budget remaining"

    print("✓ Budget checking test passed")


def test_monthly_cost_loading():
    """Test loading monthly costs from log."""
    print("Testing monthly cost loading...")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "scores.jsonl"

        # Write costs for different months
        with open(log_path, 'w') as f:
            entries = [
                {'timestamp': '2026-01-15T12:00:00Z', 'cost_usd': 1.5},
                {'timestamp': '2026-01-20T12:00:00Z', 'cost_usd': 2.0},
                {'timestamp': '2026-02-05T12:00:00Z', 'cost_usd': 3.0},
            ]
            for entry in entries:
                f.write(json.dumps(entry) + '\n')

        tracker = CostTracker(log_path)
        monthly = tracker.load_monthly_costs()

        assert '2026-01' in monthly
        assert abs(monthly['2026-01'] - 3.5) < 0.01
        assert '2026-02' in monthly
        assert abs(monthly['2026-02'] - 3.0) < 0.01

    print("✓ Monthly cost loading test passed")


def test_sampling_rate_suggestion():
    """Test sampling rate suggestions."""
    print("Testing sampling rate suggestions...")

    tracker = CostTracker()

    # Suggest rate for 100 searches/day, $5/month budget
    suggestion = tracker.suggest_sampling_rate(
        monthly_budget=5.0,
        searches_per_day=100
    )

    assert 'suggested_sampling_rate' in suggestion
    assert 0 <= suggestion['suggested_sampling_rate'] <= 1.0
    assert suggestion['estimated_monthly_cost_usd'] <= 5.0

    print("✓ Sampling rate suggestion test passed")


def test_heuristic_scoring():
    """Test heuristic scoring."""
    print("Testing heuristic scoring...")

    scorer = HeuristicScorer()

    query = "authentication bug fix"
    results = [
        {
            'id': 'session-1',
            'summary': 'Fixed authentication bug in login system',
            'topics': ['authentication', 'bug-fix', 'security'],
            'files_modified': ['auth.py', 'test_auth.py'],
            'relevance_score': 0.9
        },
        {
            'id': 'session-2',
            'summary': 'Added user profiles feature',
            'topics': ['user-profiles', 'feature'],
            'files_modified': ['profiles.py'],
            'relevance_score': 0.4
        }
    ]

    config = {'limit': 5, 'mode': 'hybrid'}

    score = scorer.score_quality(query, results, config)

    # Verify structure
    assert 'overall_quality' in score
    assert 'relevance' in score
    assert 'accuracy' in score
    assert 'helpfulness' in score
    assert 'coverage' in score
    assert 'quality_rating' in score
    assert score['scoring_method'] == 'heuristic'

    # Verify ranges
    assert 0 <= score['overall_quality'] <= 1
    assert score['quality_rating'] in ['excellent', 'good', 'acceptable', 'poor']

    # First result should have high relevance
    assert score['relevance'] > 0.5, "Should have good relevance"

    print("✓ Heuristic scoring test passed")


def test_heuristic_empty_results():
    """Test heuristic scoring with no results."""
    print("Testing heuristic with empty results...")

    scorer = HeuristicScorer()

    score = scorer.score_quality("test query", [], {'limit': 5})

    assert score['overall_quality'] == 0.0
    assert score['quality_rating'] == 'poor'
    assert len(score['weaknesses']) > 0
    assert any('No results' in w for w in score['weaknesses'])

    print("✓ Heuristic empty results test passed")


def test_prompt_generation():
    """Test prompt generation."""
    print("Testing prompt generation...")

    prompts = QualityEvaluationPrompts()

    query = "authentication"
    results = [
        {
            'id': 'session-1',
            'summary': 'Fixed auth bug',
            'topics': ['auth'],
            'relevance_score': 0.8
        }
    ]
    config = {'mode': 'hybrid', 'limit': 5}

    prompt = prompts.get_comprehensive_prompt(query, results, config)

    assert 'authentication' in prompt
    assert 'session-1' in prompt
    assert 'JSON' in prompt
    assert 'overall_quality' in prompt

    print("✓ Prompt generation test passed")


def test_quality_scorer_sampling():
    """Test sampling rate control."""
    print("Testing sampling rate control...")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "scores.jsonl"

        # Create scorer with 0% sampling
        with patch('metrics.config.config') as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                'quality_scoring.enabled': True,
                'quality_scoring.mode': 'heuristic',
                'quality_scoring.sampling_rate': 0.0,
                'quality_scoring.monthly_budget_usd': 100.0,
                'quality_scoring.log_path': str(log_path),
                'quality_scoring.fallback_to_heuristic': True
            }.get(key, default)

            scorer = QualityScorer(log_path)

            # Should never evaluate with 0% rate
            should_eval_count = sum(1 for _ in range(10) if scorer.should_evaluate())
            assert should_eval_count == 0, f"Should evaluate none with 0% sampling, got {should_eval_count}"

    print("✓ Sampling rate control test passed")


def test_quality_scorer_budget_enforcement():
    """Test budget enforcement."""
    print("Testing budget enforcement...")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "scores.jsonl"

        # Write costs exceeding budget
        with open(log_path, 'w') as f:
            for i in range(10):
                entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'cost_usd': 1.0
                }
                f.write(json.dumps(entry) + '\n')

        # Create scorer with $5 budget (already exceeded)
        with patch('metrics.config.config') as mock_config:
            mock_config.get.side_effect = lambda key, default=None: {
                'quality_scoring.enabled': True,
                'quality_scoring.sampling_rate': 1.0,
                'quality_scoring.monthly_budget_usd': 5.0,
                'quality_scoring.log_path': str(log_path)
            }.get(key, default)

            scorer = QualityScorer(log_path)

            # Should not evaluate (budget exceeded)
            assert not scorer.should_evaluate(), "Should not evaluate when budget exceeded"

    print("✓ Budget enforcement test passed")


def test_quality_scorer_heuristic_evaluation():
    """Test heuristic evaluation directly."""
    print("Testing heuristic evaluation...")

    # Test heuristic scorer directly (no QualityScorer wrapper)
    scorer = HeuristicScorer()

    results = [
        {
            'id': 'session-1',
            'summary': 'Test session about authentication',
            'topics': ['test', 'authentication'],
            'files_modified': ['test.py'],
            'relevance_score': 0.7
        }
    ]

    evaluation = scorer.score_quality(
        query='test query authentication',
        results=results,
        config={'mode': 'bm25', 'limit': 5}
    )

    assert evaluation is not None, "Evaluation should not be None"
    assert evaluation['scoring_method'] == 'heuristic'
    assert 'overall_quality' in evaluation
    assert 'relevance' in evaluation
    assert 'accuracy' in evaluation
    assert 'helpfulness' in evaluation
    assert 'coverage' in evaluation
    assert evaluation['quality_rating'] in ['excellent', 'good', 'acceptable', 'poor']

    print("✓ Heuristic evaluation test passed")


def test_cost_summary():
    """Test cost summary generation."""
    print("Testing cost summary...")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "scores.jsonl"

        # Write some costs
        with open(log_path, 'w') as f:
            for i in range(5):
                entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'cost_usd': 0.5
                }
                f.write(json.dumps(entry) + '\n')

        tracker = CostTracker(log_path)
        summary = tracker.get_cost_summary(10.0)

        assert 'current_month' in summary
        assert 'monthly_budget_usd' in summary
        assert 'current_spend_usd' in summary
        assert 'remaining_budget_usd' in summary
        assert 'within_budget' in summary
        assert summary['within_budget'] is True
        assert abs(summary['current_spend_usd'] - 2.5) < 0.01

    print("✓ Cost summary test passed")


def run_all_tests():
    """Run all quality scoring tests."""
    print("=" * 60)
    print("Running Quality Scoring Tests")
    print("=" * 60 + "\n")

    tests = [
        test_cost_calculation,
        test_budget_checking,
        test_monthly_cost_loading,
        test_sampling_rate_suggestion,
        test_heuristic_scoring,
        test_heuristic_empty_results,
        test_prompt_generation,
        test_quality_scorer_sampling,
        test_quality_scorer_budget_enforcement,
        test_quality_scorer_heuristic_evaluation,
        test_cost_summary
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
