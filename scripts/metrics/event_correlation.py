"""
Event correlation utilities.

Provides event ID generation and cross-log correlation to link
related events across different log files (telemetry, impact, quality).
"""

import uuid
from pathlib import Path
from typing import Dict, List
from .jsonl_utils import JSONLReader


class EventCorrelator:
    """Manage event correlation across logs."""

    @staticmethod
    def generate_event_id() -> str:
        """
        Generate unique event ID.

        Returns:
            UUID string for event identification
        """
        return str(uuid.uuid4())

    @staticmethod
    def find_related_events(
        event_id: str,
        *log_paths: Path
    ) -> Dict[str, List[dict]]:
        """
        Find all events with matching event_id or recall_event_id.

        Args:
            event_id: Event ID to search for
            *log_paths: Paths to JSONL log files

        Returns:
            Dictionary mapping log names to matching events
        """
        related = {}

        for log_path in log_paths:
            if not log_path.exists():
                continue

            # Read log with filter
            events = JSONLReader.read_log(
                log_path,
                filter_fn=lambda e: (
                    e.get("event_id") == event_id or
                    e.get("recall_event_id") == event_id
                )
            )

            if events:
                # Use stem as log name (e.g., "recall_analytics")
                log_name = log_path.stem
                related[log_name] = events

        return related

    @staticmethod
    def build_event_timeline(
        event_id: str,
        all_logs: Dict[str, Path]
    ) -> List[dict]:
        """
        Build chronological timeline of related events.

        Args:
            event_id: Event ID to trace
            all_logs: Dictionary mapping log names to paths

        Returns:
            List of events sorted chronologically with source annotation
        """
        all_events = []

        for log_name, log_path in all_logs.items():
            if not log_path.exists():
                continue

            # Find matching events
            events = JSONLReader.read_log(
                log_path,
                filter_fn=lambda e: (
                    e.get("event_id") == event_id or
                    e.get("recall_event_id") == event_id
                )
            )

            # Annotate with source
            for event in events:
                event["_source_log"] = log_name
                all_events.append(event)

        # Sort chronologically
        all_events.sort(
            key=lambda e: e.get("timestamp", "")
        )

        return all_events

    @staticmethod
    def get_event_chain(
        event_id: str,
        telemetry_log: Path,
        impact_log: Path = None,
        quality_log: Path = None
    ) -> Dict[str, dict]:
        """
        Get complete event chain: telemetry → impact → quality.

        Args:
            event_id: Root event ID (from telemetry)
            telemetry_log: Path to recall_analytics.jsonl
            impact_log: Path to context_impact.jsonl (optional)
            quality_log: Path to quality_scores.jsonl (optional)

        Returns:
            Dictionary with telemetry, impact, quality events (if found)
        """
        chain = {}

        # Get telemetry event
        if telemetry_log.exists():
            telemetry_events = JSONLReader.read_log(
                telemetry_log,
                filter_fn=lambda e: e.get("event_id") == event_id
            )
            if telemetry_events:
                chain["telemetry"] = telemetry_events[0]

        # Get impact analysis (uses recall_event_id)
        if impact_log and impact_log.exists():
            impact_events = JSONLReader.read_log(
                impact_log,
                filter_fn=lambda e: e.get("recall_event_id") == event_id
            )
            if impact_events:
                chain["impact"] = impact_events[0]

        # Get quality score (uses recall_event_id)
        if quality_log and quality_log.exists():
            quality_events = JSONLReader.read_log(
                quality_log,
                filter_fn=lambda e: e.get("recall_event_id") == event_id
            )
            if quality_events:
                chain["quality"] = quality_events[0]

        return chain

    @staticmethod
    def find_session_events(
        session_id: str,
        telemetry_log: Path
    ) -> List[dict]:
        """
        Find all recall events for a session.

        Args:
            session_id: Session ID to search for
            telemetry_log: Path to recall_analytics.jsonl

        Returns:
            List of telemetry events for this session
        """
        if not telemetry_log.exists():
            return []

        return JSONLReader.read_log(
            telemetry_log,
            filter_fn=lambda e: e.get("session_id") == session_id
        )

    @staticmethod
    def get_event_count_by_type(log_path: Path) -> Dict[str, int]:
        """
        Count events by type in a log file.

        Args:
            log_path: Path to JSONL log file

        Returns:
            Dictionary mapping event types to counts
        """
        if not log_path.exists():
            return {}

        events = JSONLReader.read_log(log_path)

        counts = {}
        for event in events:
            event_type = event.get("event_type", "unknown")
            counts[event_type] = counts.get(event_type, 0) + 1

        return counts
