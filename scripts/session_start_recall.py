#!/usr/bin/env python3
"""
SessionStart hook for automatic context recall.
Searches for relevant past sessions and displays them at session start.
"""

import json
import sys
from pathlib import Path
from subprocess import run, PIPE

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from smart_recall import smart_recall, format_recall_output, infer_context


def main():
    """SessionStart hook main function."""
    # Get project directory
    project_dir = Path.cwd()
    index_path = project_dir / ".claude/context/sessions/index.json"

    # Check if index exists
    if not index_path.exists():
        # No sessions yet, exit silently
        sys.exit(0)

    # Infer context from environment
    context_text = infer_context()

    # If we have context, search for relevant sessions
    if context_text:
        try:
            results = smart_recall(
                context_text=context_text,
                index_path=index_path,
                search_mode="auto",
                limit=3,
                min_relevance=0.4,  # Higher threshold for auto-display
                verbose=False
            )

            # If we found relevant sessions, display them
            if results:
                output = format_recall_output(results, context_text)
                print(output, file=sys.stderr)
                print("", file=sys.stderr)  # Blank line for spacing

        except Exception as e:
            # Fail silently to avoid disrupting session start
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
