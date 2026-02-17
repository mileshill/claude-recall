#!/usr/bin/env python3
"""
Extract relevant context from session transcripts based on query.

Searches through .jsonl transcript files to find messages that match
the query, then extracts those messages with surrounding context.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def extract_message_text(entry: dict) -> Optional[str]:
    """
    Extract readable text from a transcript entry.

    Args:
        entry: JSONL transcript entry

    Returns:
        Extracted text or None
    """
    # Check if this is a user or assistant message
    entry_type = entry.get('type', '')
    if entry_type not in ('user', 'assistant'):
        return None

    message = entry.get('message', {})
    if not message:
        return None

    role = message.get('role', entry_type)  # Fallback to entry type
    content = message.get('content')

    if not content:
        return None

    # Extract text from content
    text_parts = []

    # Content can be a string (user messages) or list (assistant messages)
    if isinstance(content, str):
        text_parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                block_type = block.get('type', '')

                # Text content
                if block_type == 'text' and 'text' in block:
                    text_parts.append(block['text'])

                # Tool use
                elif block_type == 'tool_use':
                    tool_name = block.get('name', 'unknown')
                    text_parts.append(f"[Tool: {tool_name}]")

                # Skip thinking blocks for brevity

            elif isinstance(block, str):
                text_parts.append(block)

    if not text_parts:
        return None

    full_text = '\n'.join(text_parts)

    # Truncate very long messages
    if len(full_text) > 1000:
        full_text = full_text[:1000] + "..."

    # Format with role prefix
    role_prefix = "👤 User:" if role == "user" else "🤖 Assistant:"
    return f"{role_prefix} {full_text}"


def search_transcript_for_query(
    transcript_path: Path,
    query_terms: List[str],
    context_lines: int = 2,
    max_excerpts: int = 3
) -> List[Dict]:
    """
    Search transcript for messages matching query terms.

    Args:
        transcript_path: Path to transcript .jsonl file
        query_terms: List of search terms
        context_lines: Number of messages before/after to include
        max_excerpts: Maximum number of excerpts to return

    Returns:
        List of excerpt dictionaries with matched messages and context
    """
    if not transcript_path.exists():
        return []

    try:
        # Read all entries
        entries = []
        with open(transcript_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        # Extract messages with text
        messages = []
        for i, entry in enumerate(entries):
            text = extract_message_text(entry)
            if text:
                messages.append({
                    'index': i,
                    'text': text,
                    'entry': entry
                })

        if not messages:
            return []

        # Search for matching messages
        query_pattern = '|'.join(re.escape(term.lower()) for term in query_terms)
        matched_indices = []

        for i, msg in enumerate(messages):
            text_lower = msg['text'].lower()
            if re.search(query_pattern, text_lower):
                matched_indices.append(i)

        if not matched_indices:
            return []

        # Extract excerpts with context
        excerpts = []
        used_ranges = set()

        for match_idx in matched_indices[:max_excerpts]:
            # Calculate context range
            start_idx = max(0, match_idx - context_lines)
            end_idx = min(len(messages) - 1, match_idx + context_lines)

            # Skip if this range overlaps with a previous excerpt
            range_key = (start_idx, end_idx)
            if range_key in used_ranges:
                continue
            used_ranges.add(range_key)

            # Extract context messages
            context_messages = messages[start_idx:end_idx + 1]

            excerpts.append({
                'match_index': match_idx,
                'match_message': messages[match_idx]['text'],
                'context_start': start_idx,
                'context_end': end_idx,
                'context_messages': [msg['text'] for msg in context_messages],
                'total_messages': len(messages)
            })

        return excerpts

    except Exception as e:
        print(f"Warning: Failed to search transcript {transcript_path}: {e}")
        return []


def format_excerpt(excerpt: Dict, max_chars: int = 1500) -> str:
    """
    Format an excerpt for display.

    Args:
        excerpt: Excerpt dictionary from search_transcript_for_query
        max_chars: Maximum characters to include

    Returns:
        Formatted excerpt string
    """
    lines = []

    # Header
    match_idx = excerpt['match_index']
    total = excerpt['total_messages']
    lines.append(f"   📄 Message {match_idx + 1} of {total}:")
    lines.append("")

    # Context messages
    current_chars = 0
    for msg_text in excerpt['context_messages']:
        # Truncate if too long
        if current_chars + len(msg_text) > max_chars:
            remaining = max_chars - current_chars
            if remaining > 100:  # Only show if there's meaningful space left
                truncated = msg_text[:remaining] + "..."
                lines.append(f"      {truncated}")
            lines.append(f"      [...{len(excerpt['context_messages']) - len(lines) + 2} more messages truncated...]")
            break

        # Add message
        lines.append(f"      {msg_text}")
        lines.append("")
        current_chars += len(msg_text)

    return '\n'.join(lines)


def extract_relevant_context(
    session_file: str,
    query: str,
    sessions_dir: Path,
    max_excerpts: int = 2,
    max_chars_per_excerpt: int = 1000
) -> Optional[str]:
    """
    Extract relevant context from a session's transcript.

    Args:
        session_file: Session filename (e.g., "2026-02-17_031626_session.md")
        query: Search query
        sessions_dir: Path to sessions directory
        max_excerpts: Maximum excerpts per session
        max_chars_per_excerpt: Max characters per excerpt

    Returns:
        Formatted context string or None
    """
    # Get transcript path
    session_id = session_file.replace('_session.md', '')
    transcript_path = sessions_dir / f"{session_id}_transcript.jsonl"

    if not transcript_path.exists():
        return None

    # Extract query terms
    query_terms = [term for term in re.findall(r'\w+', query.lower()) if len(term) >= 3]

    if not query_terms:
        return None

    # Search transcript
    excerpts = search_transcript_for_query(
        transcript_path,
        query_terms,
        context_lines=1,  # 1 message before/after
        max_excerpts=max_excerpts
    )

    if not excerpts:
        return None

    # Format excerpts
    formatted_lines = []
    formatted_lines.append("   💬 Relevant conversation excerpts:")
    formatted_lines.append("")

    for excerpt in excerpts:
        formatted_lines.append(format_excerpt(excerpt, max_chars_per_excerpt))

    return '\n'.join(formatted_lines)


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) < 3:
        print("Usage: extract_transcript_context.py <transcript.jsonl> <query>")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    query = sys.argv[2]

    query_terms = [term for term in re.findall(r'\w+', query.lower()) if len(term) >= 3]

    excerpts = search_transcript_for_query(transcript_path, query_terms)

    for excerpt in excerpts:
        print(format_excerpt(excerpt))
        print("\n" + "="*60 + "\n")
