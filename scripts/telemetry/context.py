"""
Context utilities for telemetry.

Provides functions to get current session ID and system state information.
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_current_session_id() -> str:
    """
    Get current Claude Code session ID.

    Returns:
        Session ID from environment or process-based fallback
    """
    # Try environment variable (set by Claude Code hooks)
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    if session_id:
        return session_id

    # Fallback to process ID
    return f'pid_{os.getpid()}'


def get_system_state(index_path: Optional[Path] = None) -> Dict:
    """
    Get current system state.

    Args:
        index_path: Path to index.json (optional)

    Returns:
        Dictionary with system state information
    """
    state = {}

    # Index information
    if index_path and index_path.exists():
        try:
            with open(index_path) as f:
                index = json.load(f)
                state['index_size'] = len(index.get('sessions', []))
                state['embeddings_available'] = 'embedding_index' in index
        except Exception:
            pass  # Silently fail

    # Memory usage (if psutil available)
    if PSUTIL_AVAILABLE:
        try:
            process = psutil.Process()
            state['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
        except Exception:
            pass

    return state


def get_project_dir() -> Path:
    """
    Get current project directory.

    Returns:
        Path to project directory
    """
    # Try environment variable
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    if project_dir:
        return Path(project_dir)

    # Fallback to current working directory
    return Path.cwd()


def is_hook_triggered() -> bool:
    """
    Check if we're running from a Claude Code hook.

    Returns:
        True if hook context detected
    """
    return 'CLAUDE_SESSION_ID' in os.environ
