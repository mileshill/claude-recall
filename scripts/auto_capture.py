#!/usr/bin/env python3
"""
Auto-capture session context on session end.
Called by SessionEnd hook (configured in .claude/settings.json)

Receives JSON on stdin with:
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/Users/...",
  "permission_mode": "default",
  "hook_event_name": "SessionEnd",
  "reason": "other"
}
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import shutil

# Add scripts to path for imports
_script_dir = str(Path(__file__).parent)
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# Import the secret redaction module (sibling script)
try:
    from redact_secrets import SecretRedactor, RedactionReport
    REDACTION_AVAILABLE = True
except ImportError:
    # Fallback: add the scripts directory to the path and retry
    _script_dir = str(Path(__file__).parent)
    if _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)
    try:
        from redact_secrets import SecretRedactor, RedactionReport
        REDACTION_AVAILABLE = True
    except ImportError:
        REDACTION_AVAILABLE = False

def get_git_status(project_dir):
    """Get current git status"""
    try:
        result = subprocess.run(
            ['git', 'status', '-s'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "Unable to determine"
    except Exception as e:
        return f"Error: {e}"

def get_git_log(project_dir, count=5):
    """Get recent git commits"""
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', f'-{count}'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "No git history"
    except Exception as e:
        return f"Error: {e}"

def get_git_diff_files(project_dir):
    """Get list of modified files"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        files = result.stdout.strip().split('\n') if result.returncode == 0 else []
        return [f for f in files if f]
    except Exception as e:
        return []

def extract_transcript_summary(transcript_path):
    """Extract a summary from the transcript"""
    if not transcript_path or not Path(transcript_path).exists():
        return "[Transcript not available]", 0

    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        message_count = len(lines)

        # Extract first user message and last assistant message for context
        first_user = None
        last_assistant = None

        for line in lines:
            try:
                entry = json.loads(line)
                if entry.get('role') == 'user' and not first_user:
                    content = entry.get('content', '')
                    if isinstance(content, list):
                        content = ' '.join(str(c.get('text', '')) for c in content if isinstance(c, dict))
                    first_user = content[:200]  # First 200 chars

                if entry.get('role') == 'assistant':
                    content = entry.get('content', '')
                    if isinstance(content, list):
                        content = ' '.join(str(c.get('text', '')) for c in content if isinstance(c, dict))
                    last_assistant = content[:200]  # Keep updating to get last one
            except json.JSONDecodeError:
                continue

        summary = f"""## Transcript Summary

**Messages**: {message_count}

**First User Message**:
{first_user or '[No user message found]'}

**Last Assistant Message**:
{last_assistant or '[No assistant message found]'}

**Full Transcript**: {transcript_path}
"""
        return summary, message_count

    except Exception as e:
        return f"[Error reading transcript: {e}]", 0

def copy_transcript(transcript_path, session_dir, session_id):
    """Copy full transcript to session directory (plain copy, no redaction)"""
    if not transcript_path or not Path(transcript_path).exists():
        return None

    try:
        dest = session_dir / f"{session_id}_transcript.jsonl"
        shutil.copy2(transcript_path, dest)
        return str(dest)
    except Exception as e:
        print(f"WARNING: Failed to copy transcript: {e}", file=sys.stderr)
        return None


def _get_redactor():
    """
    Initialize and return a SecretRedactor instance.
    Returns None if the redaction module is not available.
    """
    if not REDACTION_AVAILABLE:
        return None
    try:
        return SecretRedactor()
    except Exception as e:
        print(f"WARNING: Failed to initialize SecretRedactor: {e}", file=sys.stderr)
        return None


def _log_redaction_report(session_dir, report, source_label, timestamp):
    """
    Append a redaction report entry to the redaction log (JSONL format).

    Args:
        session_dir: Path to the sessions directory.
        report: A RedactionReport instance.
        source_label: Label identifying what was redacted (e.g., "session_md", "transcript_jsonl").
        timestamp: Session timestamp string for correlation.
    """
    log_path = session_dir / "redaction_log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_timestamp": timestamp,
        "source": source_label,
        "total_findings": report.total_findings,
        "high_confidence": report.high_confidence,
        "medium_confidence": report.medium_confidence,
        "elapsed_ms": round(report.elapsed_ms, 2),
        "text_length": report.text_length,
        "findings": [
            {
                "pattern": f.pattern_name if hasattr(f, 'pattern_name') else f.get("pattern_name", ""),
                "category": f.category if hasattr(f, 'category') else f.get("category", ""),
                "confidence": f.confidence if hasattr(f, 'confidence') else f.get("confidence", ""),
                "evidence": f.evidence if hasattr(f, 'evidence') else f.get("evidence", ""),
            }
            for f in report.findings
        ],
    }

    try:
        with open(log_path, "a") as logfile:
            logfile.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"WARNING: Failed to write redaction log: {e}", file=sys.stderr)


def redact_and_copy_transcript(transcript_path, session_dir, session_id, redactor, timestamp):
    """
    Copy transcript to session directory with secrets redacted.

    Reads the original transcript JSONL, runs redaction on all content,
    writes the redacted version to the session directory, and logs findings.

    Args:
        transcript_path: Path to the original transcript JSONL file.
        session_dir: Path to the session output directory.
        session_id: Timestamp-based session identifier.
        redactor: A SecretRedactor instance (or None to skip redaction).
        timestamp: Session timestamp for log correlation.

    Returns:
        Tuple of (dest_path_str, RedactionReport or None).
    """
    if not transcript_path or not Path(transcript_path).exists():
        return None, None

    dest = session_dir / f"{session_id}_transcript.jsonl"

    if redactor is None:
        # No redactor available; fall back to plain copy
        try:
            shutil.copy2(transcript_path, dest)
            return str(dest), None
        except Exception as e:
            print(f"WARNING: Failed to copy transcript: {e}", file=sys.stderr)
            return None, None

    try:
        with open(transcript_path, "r") as f:
            raw_jsonl = f.read()

        redacted_jsonl, report = redactor.redact_jsonl(raw_jsonl)

        with open(dest, "w") as f:
            f.write(redacted_jsonl)

        if report and report.total_findings > 0:
            _log_redaction_report(session_dir, report, "transcript_jsonl", timestamp)

        return str(dest), report

    except Exception as e:
        print(f"WARNING: Redaction failed for transcript, falling back to plain copy: {e}", file=sys.stderr)
        try:
            shutil.copy2(transcript_path, dest)
            return str(dest), None
        except Exception as copy_err:
            print(f"WARNING: Plain copy also failed: {copy_err}", file=sys.stderr)
            return None, None

def run_impact_analysis(session_id, transcript_path, session_dir, project_dir):
    """
    Run impact analysis for recall events in this session.

    Args:
        session_id: Current session ID
        transcript_path: Path to session transcript
        session_dir: Path to sessions directory
        project_dir: Project root directory

    Returns:
        Number of analyses performed
    """
    try:
        # Import impact analysis components
        from impact_analysis import ImpactAnalyzer
        from metrics.config import config

        # Check if impact analysis is enabled
        if not config.get('impact_analysis.enabled', True):
            return 0

        # Check minimum recall events threshold
        min_events = config.get('impact_analysis.min_recall_events', 1)

        # Load telemetry log to find recall events for this session
        telemetry_log = Path(project_dir) / config.get(
            'telemetry.log_path',
            '.claude/context/sessions/recall_analytics.jsonl'
        )

        if not telemetry_log.exists():
            return 0  # No telemetry data yet

        # Find recall events for this session
        recall_events = []
        with open(telemetry_log) as f:
            for line in f:
                try:
                    event = json.loads(line)
                    # Match by session_id or check if event is recent
                    if event.get('session_id') == session_id or \
                       event.get('session_id', '').endswith(str(os.getpid())):
                        if event.get('event_type') in ('recall_triggered', 'smart_recall_completed'):
                            recall_events.append(event)
                except json.JSONDecodeError:
                    continue

        if len(recall_events) < min_events:
            return 0  # Not enough recall events to analyze

        # Load current transcript
        if not transcript_path or not Path(transcript_path).exists():
            return 0

        transcript_text = ""
        try:
            with open(transcript_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        content = entry.get('content', '')
                        if isinstance(content, list):
                            content = ' '.join(
                                str(c.get('text', '')) for c in content
                                if isinstance(c, dict)
                            )
                        transcript_text += content + "\n"
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return 0

        # Load index to get recalled session data
        index_path = session_dir / 'index.json'
        if not index_path.exists():
            return 0

        with open(index_path) as f:
            index_data = json.load(f)

        # Initialize analyzer
        analyzer = ImpactAnalyzer(log_path=session_dir / 'context_impact.jsonl')

        # Analyze each recall event
        analyses_count = 0
        for event in recall_events:
            event_id = event.get('event_id')
            if not event_id:
                continue

            # Get recalled session IDs from event
            recalled_ids = []
            if 'results' in event and 'retrieved_sessions' in event['results']:
                recalled_ids = event['results']['retrieved_sessions']

            # Load recalled sessions from index
            recalled_sessions = [
                s for s in index_data.get('sessions', [])
                if s.get('id') in recalled_ids
            ]

            if not recalled_sessions:
                continue

            # Run analysis
            try:
                analyzer.analyze_recall_event(
                    recall_event_id=event_id,
                    current_transcript=transcript_text,
                    recalled_sessions=recalled_sessions,
                    session_data={'timestamp': datetime.now(timezone.utc).isoformat()}
                )
                analyses_count += 1
            except Exception as e:
                print(f"WARNING: Impact analysis failed for event {event_id}: {e}", file=sys.stderr)
                continue

        return analyses_count

    except Exception as e:
        print(f"WARNING: Impact analysis error: {e}", file=sys.stderr)
        return 0


def auto_capture_session(hook_input):
    """
    Automatically capture session context from SessionEnd hook.

    Applies secret redaction to both session markdown content and transcript
    JSONL before writing to disk. Logs any redaction findings to
    .claude/context/sessions/redaction_log.jsonl.
    """

    session_id = hook_input.get('session_id', 'unknown')
    transcript_path = hook_input.get('transcript_path')
    project_dir = hook_input.get('cwd', os.getcwd())
    reason = hook_input.get('reason', 'other')

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')

    session_dir = Path(project_dir) / '.claude/context/sessions'
    session_dir.mkdir(parents=True, exist_ok=True)

    session_file = session_dir / f"{timestamp}_session.md"

    # Initialize the secret redactor
    redactor = _get_redactor()
    total_secrets_found = 0

    # Gather session data
    git_status = get_git_status(project_dir)
    git_log = get_git_log(project_dir)
    files_modified = get_git_diff_files(project_dir)

    # Extract transcript summary
    transcript_summary, message_count = extract_transcript_summary(transcript_path)

    # Redact transcript summary content before including in session file
    summary_report = None
    if redactor and transcript_summary:
        transcript_summary, summary_report = redactor.redact(transcript_summary)
        if summary_report and summary_report.total_findings > 0:
            _log_redaction_report(session_dir, summary_report, "transcript_summary", timestamp)
            total_secrets_found += summary_report.total_findings

    # Copy and redact full transcript JSONL
    transcript_copy, transcript_report = redact_and_copy_transcript(
        transcript_path, session_dir, timestamp, redactor, timestamp
    )
    if transcript_report and transcript_report.total_findings > 0:
        total_secrets_found += transcript_report.total_findings

    # Determine topics from messages (simple heuristic)
    topics = ['auto-captured']
    if message_count > 0:
        topics.append('conversation')
    if files_modified:
        topics.append('code-changes')
    if total_secrets_found > 0:
        topics.append('secrets-redacted')

    # Build the redaction status line for the hook status section
    if redactor is None:
        redaction_status = "-- Redaction module not available (secrets may be present)"
    elif total_secrets_found > 0:
        redaction_status = (
            f"!! WARNING: {total_secrets_found} secret(s) detected and redacted"
        )
    else:
        redaction_status = "OK Secret scan complete - no secrets detected"

    # Create session file with metadata
    content = f"""# Session: {timestamp}

**Status**: Auto-Captured (SessionEnd hook)
**Session ID**: {session_id}
**Description**: Session automatically captured by SessionEnd hook
**Topics**: [{', '.join(topics)}]
**Captured**: {datetime.now(timezone.utc).isoformat()}
**Trigger**: SessionEnd
**Reason**: {reason}
**Messages**: {message_count}

## Session Notes

This session was automatically captured by the SessionEnd hook.

## Git Status at Time of Capture

```
{git_status}
```

## Recent Git Commits

```
{git_log}
```

## Files Modified in This Session

```
{chr(10).join(files_modified) if files_modified else 'No modified files detected'}
```

---

{transcript_summary}

---

## Transcript Files

- **Summary**: Included above
- **Full Transcript (JSONL)**: {transcript_copy or transcript_path or 'Not available'}
- **Session File**: {session_file.name}

## Hook Status

[+] SessionEnd hook triggered successfully
[+] Transcript captured ({message_count} messages)
[+] Git data captured
[+] Session file created
[+] Ready for indexing
[{redaction_status}]

"""

    # Redact the final session markdown content itself
    session_report = None
    if redactor:
        content, session_report = redactor.redact(content)
        if session_report and session_report.total_findings > 0:
            _log_redaction_report(session_dir, session_report, "session_md", timestamp)
            total_secrets_found += session_report.total_findings

    # Write session file
    session_file.write_text(content)

    # Index the session
    index_script = Path(project_dir) / '.claude/skills/recall/scripts/index_session.py'
    if index_script.exists():
        try:
            result = subprocess.run(
                ['python3', str(index_script), str(session_file)],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"[+] Session indexed: {session_file.name}", file=sys.stderr)
            else:
                print(f"WARNING: Indexing failed: {result.stderr}", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: Indexing error: {e}", file=sys.stderr)

    # Run impact analysis if enabled
    try:
        analyses_count = run_impact_analysis(
            session_id=session_id,
            transcript_path=transcript_path,
            session_dir=session_dir,
            project_dir=project_dir
        )
        if analyses_count > 0:
            print(f"[+] Impact analysis: {analyses_count} recall event(s) analyzed", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: Impact analysis integration error: {e}", file=sys.stderr)

    # Print capture summary
    print(f"[+] Session captured: {session_file.name}", file=sys.stderr)
    print(f"[+] Messages: {message_count}", file=sys.stderr)
    print(f"[+] Transcript: {transcript_copy or 'Referenced only'}", file=sys.stderr)

    # Print redaction warnings
    if total_secrets_found > 0:
        print(
            f"[!] WARNING: {total_secrets_found} secret(s) were detected and redacted!",
            file=sys.stderr,
        )
        print(
            f"[!] See redaction log: {session_dir / 'redaction_log.jsonl'}",
            file=sys.stderr,
        )
    elif redactor:
        print("[+] Secret scan: clean (no secrets detected)", file=sys.stderr)
    else:
        print("[--] Secret redaction not available", file=sys.stderr)

    return str(session_file)

def main():
    """Main entry point - reads JSON from stdin"""
    try:
        # Read JSON input from stdin (provided by SessionEnd hook)
        input_data = sys.stdin.read()

        if not input_data.strip():
            print("❌ No input received from SessionEnd hook", file=sys.stderr)
            print("Expected JSON on stdin with session_id, transcript_path, etc.", file=sys.stderr)
            return 1

        hook_input = json.loads(input_data)

        # Validate required fields
        if 'session_id' not in hook_input:
            print("⚠️  Warning: session_id not in hook input", file=sys.stderr)

        # Capture the session
        session_file = auto_capture_session(hook_input)
        print(f"\n✅ Auto-capture successful: {session_file}", file=sys.stderr)
        return 0

    except json.JSONDecodeError as e:
        print(f"\n❌ Failed to parse hook input JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Auto-capture failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
