#!/usr/bin/env python3
"""
Index a session file for fast searching.
Creates/updates .claude/context/sessions/index.json
Uses BM25 for relevance scoring.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime
from rank_bm25 import BM25Okapi

def tokenize_text(text: str) -> list:
    """Tokenize text for BM25 indexing."""
    # Convert to lowercase and extract words
    tokens = re.findall(r'\w+', text.lower())
    return tokens

def parse_session_metadata(session_file: Path) -> dict:
    """Extract metadata from session file."""
    content = session_file.read_text()

    # Extract from frontmatter-style metadata
    metadata = {
        "id": session_file.stem,
        "file": session_file.name,
        "timestamp": session_file.stem.split('_')[0] if '_' in session_file.stem else "unknown",
        "status": "captured",
        "topics": [],
        "files_modified": [],
        "beads_issues": [],
        "decisions": [],
        "summary": "",
        "message_count": 0,
        "tokens_approx": 0
    }

    # Parse topics
    topics_match = re.search(r'\*\*Topics\*\*:\s*\[(.*?)\]', content)
    if topics_match:
        topics_str = topics_match.group(1)
        metadata["topics"] = [t.strip() for t in topics_str.split(',')]

    # Parse description as summary
    desc_match = re.search(r'\*\*Description\*\*:\s*(.*?)(?:\n|$)', content)
    if desc_match:
        metadata["summary"] = desc_match.group(1).strip()

    # Parse status
    status_match = re.search(r'\*\*Status\*\*:\s*(.*?)(?:\n|$)', content)
    if status_match:
        metadata["status"] = status_match.group(1).strip().lower()

    # Extract files modified
    files_section = re.search(r'## Files Modified.*?\`\`\`(.*?)\`\`\`', content, re.DOTALL)
    if files_section:
        files_text = files_section.group(1).strip()
        metadata["files_modified"] = [
            line.strip() for line in files_text.split('\n')
            if line.strip() and not line.startswith('Unable')
        ]

    # Find beads references
    beads_refs = re.findall(r'beads-[a-z0-9]+', content)
    metadata["beads_issues"] = list(set(beads_refs))

    # Estimate message count (rough heuristic)
    metadata["message_count"] = content.count('\n## ') + content.count('\n### ')

    # Estimate tokens (very rough: ~4 chars per token)
    metadata["tokens_approx"] = len(content) // 4

    # Extract captured timestamp
    captured_match = re.search(r'\*\*Captured\*\*:\s*(\S+)', content)
    if captured_match:
        metadata["captured"] = captured_match.group(1)

    # Build searchable text corpus for BM25
    # Weight important fields by repeating them
    corpus_parts = []

    # Summary (weight: 3x)
    if metadata["summary"]:
        corpus_parts.extend([metadata["summary"]] * 3)

    # Topics (weight: 2x)
    for topic in metadata["topics"]:
        corpus_parts.extend([topic] * 2)

    # Files (weight: 1x)
    corpus_parts.extend(metadata["files_modified"])

    # Beads issues (weight: 1x)
    corpus_parts.extend(metadata["beads_issues"])

    # Full content excerpt (first 500 chars, weight: 1x)
    # Extract key sections from content
    sections_to_index = []

    # Extract session notes
    notes_match = re.search(r'## Session Notes(.*?)(?=##|$)', content, re.DOTALL)
    if notes_match:
        sections_to_index.append(notes_match.group(1).strip()[:500])

    # Extract key decisions
    decisions_match = re.search(r'### Key Decisions(.*?)(?=###|##|$)', content, re.DOTALL)
    if decisions_match:
        sections_to_index.append(decisions_match.group(1).strip()[:500])

    corpus_parts.extend(sections_to_index)

    # Join and tokenize
    full_text = ' '.join(corpus_parts)
    metadata["bm25_tokens"] = tokenize_text(full_text)

    # Mark as needing embeddings (will be set to False after embed_sessions.py runs)
    metadata["needs_embedding"] = True
    metadata["has_embedding"] = False

    return metadata

def rebuild_bm25_index(sessions: list) -> dict:
    """Rebuild BM25 index from all sessions."""
    # Extract tokenized corpus for all sessions
    corpus = []
    session_ids = []

    for session in sessions:
        tokens = session.get("bm25_tokens", [])
        if tokens:
            corpus.append(tokens)
            session_ids.append(session["id"])

    # Build BM25 index
    if corpus:
        bm25 = BM25Okapi(corpus)
        # Store BM25 parameters for reconstruction
        bm25_data = {
            "doc_len": bm25.doc_len,
            "avgdl": bm25.avgdl,
            "doc_freqs": bm25.doc_freqs,
            "idf": bm25.idf,
            "session_ids": session_ids
        }
    else:
        bm25_data = None

    return bm25_data

def update_index(session_metadata: dict, index_path: Path):
    """Add or update session in index and rebuild BM25."""
    # Load existing index
    if index_path.exists():
        with open(index_path, 'r') as f:
            index = json.load(f)
    else:
        index = {"sessions": [], "last_updated": None, "bm25_index": None}

    # Remove existing entry if present (update case)
    index["sessions"] = [
        s for s in index["sessions"]
        if s["id"] != session_metadata["id"]
    ]

    # Add new entry
    index["sessions"].append(session_metadata)

    # Sort by timestamp (newest first)
    index["sessions"].sort(key=lambda s: s.get("timestamp", ""), reverse=True)

    # Rebuild BM25 index
    index["bm25_index"] = rebuild_bm25_index(index["sessions"])

    # Update last_updated
    index["last_updated"] = datetime.now(datetime.UTC if hasattr(datetime, 'UTC') else None).isoformat()

    # Write back
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

    return index

def main():
    if len(sys.argv) < 2:
        print("Usage: index_session.py <session_file>")
        sys.exit(1)

    session_file = Path(sys.argv[1])
    if not session_file.exists():
        print(f"Error: Session file not found: {session_file}")
        sys.exit(1)

    # Parse metadata
    print(f"Parsing: {session_file}")
    metadata = parse_session_metadata(session_file)

    # Update index
    index_path = session_file.parent / "index.json"
    print(f"Updating index: {index_path}")
    index = update_index(metadata, index_path)

    print(f"\n✓ Indexed session: {metadata['id']}")
    print(f"  Summary: {metadata['summary']}")
    print(f"  Topics: {', '.join(metadata['topics'])}")
    print(f"  Files: {len(metadata['files_modified'])}")
    print(f"  Beads: {', '.join(metadata['beads_issues']) if metadata['beads_issues'] else 'none'}")
    print(f"  Tokens: ~{metadata['tokens_approx']:,}")
    print(f"\nTotal sessions in index: {len(index['sessions'])}")

if __name__ == "__main__":
    main()
