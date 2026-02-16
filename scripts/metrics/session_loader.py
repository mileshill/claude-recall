"""
Session content loader with caching.

Provides utilities to load session markdown files and transcripts
with in-memory caching for performance.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
from .jsonl_utils import JSONLReader


class SessionLoader:
    """Load and cache session content."""

    def __init__(self, session_dir: Path):
        """
        Initialize loader.

        Args:
            session_dir: Directory containing session files
        """
        self.session_dir = Path(session_dir)
        self._cache = {}

    def load_session(
        self,
        session_id: str,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Load session markdown and parse metadata.

        Args:
            session_id: Session ID (e.g., "2026-02-16_093045")
            use_cache: Whether to use cached content

        Returns:
            Dictionary with metadata and content, or None if not found
        """
        if use_cache and session_id in self._cache:
            return self._cache[session_id]

        session_file = self.session_dir / f"{session_id}_session.md"
        if not session_file.exists():
            return None

        try:
            content = session_file.read_text()

            # Parse metadata
            metadata = self._parse_metadata(content)
            metadata["content"] = content
            metadata["session_id"] = session_id
            metadata["file_path"] = str(session_file)

            if use_cache:
                self._cache[session_id] = metadata

            return metadata

        except Exception as e:
            print(f"Warning: Failed to load session {session_id}: {e}")
            return None

    def load_transcript(
        self,
        session_id: str
    ) -> List[dict]:
        """
        Load session transcript JSONL.

        Args:
            session_id: Session ID

        Returns:
            List of transcript entries (messages)
        """
        transcript_file = self.session_dir / f"{session_id}_transcript.jsonl"
        if not transcript_file.exists():
            return []

        return JSONLReader.read_log(transcript_file)

    def load_multiple_sessions(
        self,
        session_ids: List[str],
        use_cache: bool = True
    ) -> Dict[str, dict]:
        """
        Load multiple sessions efficiently.

        Args:
            session_ids: List of session IDs to load
            use_cache: Whether to use cached content

        Returns:
            Dictionary mapping session IDs to metadata
        """
        sessions = {}

        for session_id in session_ids:
            session = self.load_session(session_id, use_cache=use_cache)
            if session:
                sessions[session_id] = session

        return sessions

    def _parse_metadata(self, content: str) -> Dict:
        """
        Extract metadata from session markdown.

        Args:
            content: Session markdown content

        Returns:
            Dictionary of metadata fields
        """
        metadata = {}

        # Define patterns for each field
        patterns = {
            "status": r'\*\*Status\*\*:\s*(.+?)(?:\n|$)',
            "summary": r'\*\*Description\*\*:\s*(.+?)(?:\n|$)',
            "topics": r'\*\*Topics\*\*:\s*\[(.+?)\]',
            "captured": r'\*\*Captured\*\*:\s*(.+?)(?:\n|$)',
            "message_count": r'\*\*Messages\*\*:\s*(\d+)',
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                value = match.group(1).strip()

                # Special handling for topics
                if key == "topics":
                    value = [t.strip() for t in value.split(',')]
                # Special handling for message_count
                elif key == "message_count":
                    value = int(value)

                metadata[key] = value

        # Extract files modified section
        files_match = re.search(
            r'## Files Modified.*?\n```\n(.*?)\n```',
            content,
            re.DOTALL
        )
        if files_match:
            files_text = files_match.group(1).strip()
            if files_text and files_text != "No modified files detected":
                metadata["files_modified"] = [
                    f.strip() for f in files_text.split('\n')
                    if f.strip()
                ]
            else:
                metadata["files_modified"] = []
        else:
            metadata["files_modified"] = []

        # Extract beads issues
        beads_matches = re.findall(r'beads-[a-zA-Z0-9]+', content)
        metadata["beads_issues"] = list(set(beads_matches))

        return metadata

    def get_session_summary(
        self,
        session_id: str
    ) -> Optional[str]:
        """
        Get just the summary text for a session.

        Args:
            session_id: Session ID

        Returns:
            Summary text or None
        """
        session = self.load_session(session_id)
        return session.get("summary") if session else None

    def get_session_topics(
        self,
        session_id: str
    ) -> List[str]:
        """
        Get topics for a session.

        Args:
            session_id: Session ID

        Returns:
            List of topic strings
        """
        session = self.load_session(session_id)
        return session.get("topics", []) if session else []

    def extract_section(
        self,
        content: str,
        section_title: str
    ) -> Optional[str]:
        """
        Extract a specific markdown section.

        Args:
            content: Full markdown content
            section_title: Section heading (e.g., "Session Notes")

        Returns:
            Section content or None
        """
        # Match section heading and capture until next heading or end
        pattern = rf'##\s+{re.escape(section_title)}.*?\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            return match.group(1).strip()

        return None

    def clear_cache(self):
        """Clear session cache."""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """
        Get number of cached sessions.

        Returns:
            Cache size
        """
        return len(self._cache)
