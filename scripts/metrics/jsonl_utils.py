"""
JSONL utilities for reading and writing log files.

Provides thread-safe JSONL reading/writing with file locking,
batching, and error handling.
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime, timezone, timedelta
import fcntl


class JSONLReader:
    """Read and filter JSONL logs with error handling."""

    @staticmethod
    def read_log(
        path: Path,
        days: int = None,
        filter_fn: Callable[[dict], bool] = None
    ) -> List[dict]:
        """
        Read JSONL with optional filtering.

        Args:
            path: Path to JSONL file
            days: Only return entries from last N days
            filter_fn: Optional filter function (entry) -> bool

        Returns:
            List of dict entries
        """
        if not path.exists():
            return []

        cutoff = None
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        entries = []
        with open(path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)

                    # Date filter
                    if cutoff:
                        timestamp_str = entry.get("timestamp", "")
                        if timestamp_str:
                            try:
                                timestamp = datetime.fromisoformat(
                                    timestamp_str.replace('Z', '+00:00')
                                )
                                if timestamp < cutoff:
                                    continue
                            except (ValueError, AttributeError):
                                # Skip entries with invalid timestamps
                                continue

                    # Custom filter
                    if filter_fn and not filter_fn(entry):
                        continue

                    entries.append(entry)

                except json.JSONDecodeError as e:
                    # Log but continue
                    print(f"Warning: Malformed JSON at {path}:{line_num}: {e}",
                          file=sys.stderr)
                except Exception as e:
                    print(f"Warning: Error reading {path}:{line_num}: {e}",
                          file=sys.stderr)

        return entries


class JSONLWriter:
    """Thread-safe JSONL writer with file locking."""

    def __init__(self, path: Path):
        """
        Initialize writer.

        Args:
            path: Path to JSONL file
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, data: dict):
        """
        Atomically append entry to JSONL file.

        Args:
            data: Dictionary to append as JSON line
        """
        with open(self.path, 'a') as f:
            try:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                # Write JSON line (use default=str for datetime, etc.)
                f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
                f.flush()
            finally:
                # Release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def append_batch(self, data_list: List[dict]):
        """
        Atomically append multiple entries.

        Args:
            data_list: List of dictionaries to append
        """
        if not data_list:
            return

        with open(self.path, 'a') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                for data in data_list:
                    f.write(json.dumps(data, ensure_ascii=False, default=str) + '\n')
                f.flush()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class BatchedJSONLWriter:
    """
    Buffered JSONL writer with automatic batching.

    Accumulates entries in memory and flushes when:
    - Buffer reaches batch_size
    - Time since last flush exceeds flush_interval
    - flush() is called explicitly
    """

    def __init__(
        self,
        path: Path,
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        """
        Initialize batched writer.

        Args:
            path: Path to JSONL file
            batch_size: Flush when buffer reaches this size
            flush_interval: Flush after this many seconds (0 = disable)
        """
        self.path = Path(path)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []
        self.last_flush = time.time()
        self.writer = JSONLWriter(path)

    def append(self, data: dict):
        """
        Add entry to buffer (may trigger flush).

        Args:
            data: Dictionary to append
        """
        self.buffer.append(data)

        # Flush if batch full or time elapsed
        should_flush = (
            len(self.buffer) >= self.batch_size or
            (self.flush_interval > 0 and
             (time.time() - self.last_flush) > self.flush_interval)
        )

        if should_flush:
            self.flush()

    def flush(self):
        """Force flush buffered entries to disk."""
        if not self.buffer:
            return

        try:
            self.writer.append_batch(self.buffer)
            self.buffer.clear()
            self.last_flush = time.time()
        except Exception as e:
            print(f"Warning: Failed to flush batch to {self.path}: {e}",
                  file=sys.stderr)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush remaining buffer."""
        self.flush()

    def __del__(self):
        """Destructor - flush on cleanup."""
        try:
            self.flush()
        except:
            pass  # Don't raise exceptions in destructor
