#!/usr/bin/env python3
"""
Regenerate session descriptions from transcripts for existing session files.
This updates the Description field in session markdown files to use the first
user message instead of the generic "Session automatically captured" text.
"""

import json
import re
import sys
from pathlib import Path


def extract_first_user_message(transcript_path):
    """Extract first user message from transcript."""
    if not transcript_path or not Path(transcript_path).exists():
        return None

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_type = entry.get('type')
                    message_obj = entry.get('message', {})
                    role = message_obj.get('role') if isinstance(message_obj, dict) else None

                    if entry_type == 'user' or role == 'user':
                        content = message_obj.get('content', entry.get('content', ''))
                        if isinstance(content, str) and content.strip():
                            text = content.strip()[:150]
                            if len(content.strip()) > 150:
                                text += "..."
                            return text
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text = item.get('text', '').strip()
                                    if text:
                                        result = text[:150]
                                        if len(text) > 150:
                                            result += "..."
                                        return result
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)

    return None


def update_session_description(session_file):
    """Update description in session file."""
    session_file = Path(session_file)
    if not session_file.exists():
        print(f"Session file not found: {session_file}", file=sys.stderr)
        return False

    # Find transcript file
    session_id = session_file.stem.replace('_session', '')
    transcript_file = session_file.parent / f"{session_id}_transcript.jsonl"

    if not transcript_file.exists():
        print(f"No transcript found for {session_file.name}", file=sys.stderr)
        return False

    # Extract first user message
    description = extract_first_user_message(transcript_file)
    if not description:
        print(f"Could not extract user message from {transcript_file.name}", file=sys.stderr)
        return False

    # Read session file
    content = session_file.read_text()

    # Check if already has a good description
    current_desc_match = re.search(r'\*\*Description\*\*:\s*(.*?)(?:\n|$)', content)
    if current_desc_match:
        current_desc = current_desc_match.group(1).strip()
        if current_desc != "Session automatically captured by SessionEnd hook" and \
           current_desc != "Session automatically captured at end":
            print(f"Skipping {session_file.name} - already has custom description", file=sys.stderr)
            return False

    # Update description
    new_content = re.sub(
        r'(\*\*Description\*\*:)\s*(.*?)(?=\n)',
        f'\\1 {description}',
        content
    )

    # Write back
    session_file.write_text(new_content)
    print(f"✓ Updated: {session_file.name}")
    print(f"  New description: {description[:80]}...")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: regenerate_session_descriptions.py <session_dir_or_file>")
        print()
        print("Examples:")
        print("  # Update all sessions in directory")
        print("  python3 regenerate_session_descriptions.py .claude/context/sessions")
        print()
        print("  # Update single session")
        print("  python3 regenerate_session_descriptions.py .claude/context/sessions/2026-02-16_100458_session.md")
        sys.exit(1)

    path = Path(sys.argv[1])

    if path.is_file():
        # Single file
        success = update_session_description(path)
        sys.exit(0 if success else 1)
    elif path.is_dir():
        # Directory - process all session files
        session_files = sorted(path.glob("*_session.md"))
        if not session_files:
            print(f"No session files found in {path}", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(session_files)} session file(s)")
        print()

        updated = 0
        for session_file in session_files:
            if update_session_description(session_file):
                updated += 1

        print()
        print(f"Updated {updated}/{len(session_files)} session(s)")
        sys.exit(0)
    else:
        print(f"Error: {path} is neither a file nor directory", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
