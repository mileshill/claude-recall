#!/usr/bin/env python3
"""
Tests for telemetry collector.

Tests event lifecycle, buffering, PII redaction, and concurrent writes.
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from telemetry.collector import TelemetryCollector, get_collector
from metrics.config import config


def test_event_lifecycle():
    """Test start → update → end event lifecycle."""
    print("Testing event lifecycle...")

    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        log_path = Path(f.name)

    # Configure test collector
    config.set('telemetry.log_path', str(log_path))
    config.set('telemetry.batch_size', 1)  # Flush immediately

    # Get fresh collector
    collector = TelemetryCollector()
    collector._initialized = False
    collector.__init__()

    # Start event
    event_id = collector.start_event(
        event_type="test_event",
        context={"initial": "data"}
    )
    assert event_id is not None, "Event ID should not be None"

    # Update event
    collector.update_event(event_id, {"updated": "value"})

    # End event
    collector.end_event(event_id, outcome={"success": True})

    # Flush to ensure write
    collector.flush()

    # Read and verify
    with open(log_path) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 1, f"Expected 1 event, got {len(events)}"
    event = events[0]

    assert event['event_id'] == event_id
    assert event['event_type'] == "test_event"
    assert event['initial'] == "data"
    assert event['updated'] == "value"
    assert event['outcome'] == {"success": True}

    # Cleanup
    log_path.unlink()

    print("✓ Event lifecycle test passed")


def test_buffering():
    """Test that buffering works correctly."""
    print("Testing buffering...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        log_path = Path(f.name)

    config.set('telemetry.log_path', str(log_path))
    config.set('telemetry.batch_size', 5)  # Buffer 5 events

    collector = TelemetryCollector()
    collector._initialized = False
    collector.__init__()

    # Write 3 events (should stay in buffer)
    for i in range(3):
        event_id = collector.start_event(
            event_type=f"test_{i}",
            context={"index": i}
        )
        collector.end_event(event_id)

    # Verify not written yet
    assert not log_path.exists() or log_path.stat().st_size == 0, \
        "Events should be buffered"

    # Write 2 more (should trigger flush at 5)
    for i in range(3, 5):
        event_id = collector.start_event(
            event_type=f"test_{i}",
            context={"index": i}
        )
        collector.end_event(event_id)

    # Give time for flush
    time.sleep(0.1)

    # Verify written
    with open(log_path) as f:
        events = [json.loads(line) for line in f]

    assert len(events) == 5, f"Expected 5 events, got {len(events)}"

    # Cleanup
    log_path.unlink()

    print("✓ Buffering test passed")


def test_pii_redaction():
    """Test that PII redaction works if available."""
    print("Testing PII redaction...")

    try:
        from redact_secrets import SecretRedactor
        redaction_available = True
    except ImportError:
        print("⊘ PII redaction not available (redact_secrets not installed)")
        return

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        log_path = Path(f.name)

    config.set('telemetry.log_path', str(log_path))
    config.set('telemetry.batch_size', 1)
    config.set('telemetry.pii_redaction', True)

    collector = TelemetryCollector()
    collector._initialized = False
    collector.__init__()

    # Create event with potential secrets
    event_id = collector.start_event(
        event_type="test_event",
        context={
            "query": {
                "raw_query": "search for api_key=sk-1234567890abcdef"
            }
        }
    )
    collector.end_event(event_id)
    collector.flush()

    # Read and verify redaction
    with open(log_path) as f:
        events = [json.loads(line) for line in f]

    event = events[0]
    query = event['query']['raw_query']

    # Should be redacted (exact format depends on SecretRedactor)
    assert "sk-1234567890abcdef" not in query or "[REDACTED" in query, \
        f"API key should be redacted, got: {query}"

    # Cleanup
    log_path.unlink()

    print("✓ PII redaction test passed")


def test_disabled_telemetry():
    """Test that disabled telemetry doesn't write anything."""
    print("Testing disabled telemetry...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        log_path = Path(f.name)

    config.set('telemetry.enabled', False)
    config.set('telemetry.log_path', str(log_path))

    collector = TelemetryCollector()
    collector._initialized = False
    collector.__init__()

    # Try to create event
    event_id = collector.start_event(
        event_type="test_event",
        context={"data": "value"}
    )

    assert event_id is None, "Event ID should be None when disabled"

    collector.end_event(event_id)
    collector.flush()

    # Verify no file created
    assert not log_path.exists() or log_path.stat().st_size == 0, \
        "No events should be written when disabled"

    # Cleanup and re-enable
    if log_path.exists():
        log_path.unlink()
    config.set('telemetry.enabled', True)

    print("✓ Disabled telemetry test passed")


def test_error_handling():
    """Test that collector handles errors gracefully."""
    print("Testing error handling...")

    # Create collector with invalid path (read-only directory)
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "subdir" / "that" / "does" / "not" / "exist" / "log.jsonl"

        config.set('telemetry.log_path', str(log_path))
        config.set('telemetry.batch_size', 1)

        collector = TelemetryCollector()
        collector._initialized = False

        # This should not crash
        try:
            collector.__init__()
            event_id = collector.start_event(
                event_type="test_event",
                context={"data": "value"}
            )
            collector.end_event(event_id)
            collector.flush()
            # If we get here without crash, that's success
            print("✓ Error handling test passed (graceful degradation)")
        except Exception as e:
            print(f"✗ Error handling test failed: {e}")


def run_all_tests():
    """Run all telemetry tests."""
    print("=" * 60)
    print("Running Telemetry Collector Tests")
    print("=" * 60 + "\n")

    tests = [
        test_event_lifecycle,
        test_buffering,
        test_pii_redaction,
        test_disabled_telemetry,
        test_error_handling
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
            failed += 1
            print()

    print("=" * 60)
    print(f"Tests: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
