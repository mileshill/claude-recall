"""
Telemetry collector for recall events.

Provides singleton collector for tracking recall operations with
buffered writes, PII redaction, and error handling.
"""

import sys
import uuid
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timezone

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics.jsonl_utils import BatchedJSONLWriter
from metrics.config import config

# Optional: redaction
try:
    from redact_secrets import SecretRedactor
    REDACTION_AVAILABLE = True
except ImportError:
    REDACTION_AVAILABLE = False
    SecretRedactor = None


class TelemetryCollector:
    """
    Singleton collector for recall telemetry.

    Handles event lifecycle (start → update → end), buffered writes,
    and optional PII redaction.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize collector (only once)."""
        if self._initialized:
            return

        # Load configuration
        self.enabled = config.get('telemetry.enabled', True)

        if not self.enabled:
            self._initialized = True
            return

        # Configure logging
        log_path_str = config.get('telemetry.log_path', '.claude/context/sessions/recall_analytics.jsonl')
        self.log_path = Path(log_path_str)

        # Make path absolute if not already
        if not self.log_path.is_absolute():
            self.log_path = Path.cwd() / self.log_path

        batch_size = config.get('telemetry.batch_size', 10)
        flush_interval = config.get('telemetry.batch_flush_interval_sec', 5.0)

        # Create writer
        self.writer = BatchedJSONLWriter(
            self.log_path,
            batch_size=batch_size,
            flush_interval=flush_interval
        )

        # Optional PII redaction
        self.pii_redaction = config.get('telemetry.pii_redaction', True)
        self.redactor = None
        if self.pii_redaction and REDACTION_AVAILABLE:
            try:
                self.redactor = SecretRedactor()
            except Exception as e:
                print(f"Warning: Failed to initialize SecretRedactor: {e}", file=sys.stderr)

        # Track in-progress events
        self.current_events = {}

        self._initialized = True

    def start_event(
        self,
        event_type: str,
        context: Dict
    ) -> Optional[str]:
        """
        Start tracking an event.

        Args:
            event_type: Type of event (e.g., "recall_triggered")
            context: Initial context dictionary

        Returns:
            Event ID (UUID) or None if disabled
        """
        if not self.enabled:
            return None

        # Generate event ID
        event_id = str(uuid.uuid4())

        # Redact query if present
        if self.redactor and 'query' in context:
            if isinstance(context['query'], dict) and 'raw_query' in context['query']:
                context['query']['raw_query'], _ = self.redactor.redact(context['query']['raw_query'])
            elif isinstance(context['query'], str):
                context['query'], _ = self.redactor.redact(context['query'])

        # Create event
        event = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **context
        }

        # Store for updates
        self.current_events[event_id] = event

        return event_id

    def update_event(
        self,
        event_id: Optional[str],
        data: Dict
    ):
        """
        Update event with additional data.

        Args:
            event_id: Event ID to update
            data: Additional data to merge
        """
        if not self.enabled or not event_id:
            return

        if event_id in self.current_events:
            self._deep_merge(self.current_events[event_id], data)

    def end_event(
        self,
        event_id: Optional[str],
        outcome: Optional[Dict] = None
    ):
        """
        Finalize and log event.

        Args:
            event_id: Event ID to finalize
            outcome: Optional outcome data
        """
        if not self.enabled or not event_id:
            return

        if event_id not in self.current_events:
            return

        event = self.current_events[event_id]

        # Add outcome
        if outcome:
            event["outcome"] = outcome

        # Write to log
        try:
            self.writer.append(event)
        except Exception as e:
            print(f"Warning: Failed to log telemetry event: {e}", file=sys.stderr)

        # Clean up
        del self.current_events[event_id]

    def log_event(self, event: Dict):
        """
        Log complete event immediately.

        Args:
            event: Complete event dictionary
        """
        if not self.enabled:
            return

        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Redact if needed
        if self.redactor and 'query' in event:
            if isinstance(event['query'], dict) and 'raw_query' in event['query']:
                event['query']['raw_query'], _ = self.redactor.redact(event['query']['raw_query'])
            elif isinstance(event['query'], str):
                event['query'], _ = self.redactor.redact(event['query'])

        # Write to log
        try:
            self.writer.append(event)
        except Exception as e:
            print(f"Warning: Failed to log telemetry event: {e}", file=sys.stderr)

    def flush(self):
        """Force flush buffered events to disk."""
        if self.enabled and hasattr(self, 'writer'):
            try:
                self.writer.flush()
            except Exception as e:
                print(f"Warning: Failed to flush telemetry: {e}", file=sys.stderr)

    def _deep_merge(self, target: Dict, source: Dict):
        """
        Deep merge source dictionary into target.

        Args:
            target: Target dictionary (modified in place)
            source: Source dictionary
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def __del__(self):
        """Destructor - flush on cleanup."""
        try:
            self.flush()
        except:
            pass  # Don't raise in destructor


# Singleton instance for import
_collector = TelemetryCollector()


def get_collector() -> TelemetryCollector:
    """
    Get singleton telemetry collector instance.

    Returns:
        TelemetryCollector instance
    """
    return _collector
