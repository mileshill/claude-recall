#!/bin/bash
# Manual session capture script (until hooks implemented)
# Usage: ./capture_session.sh "Session description" [topics]

set -e

# Get project root (assumes script is in .claude/skills/recall/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SESSION_DIR="$PROJECT_ROOT/.claude/context/sessions"
mkdir -p "$SESSION_DIR"

# Parse arguments
DESCRIPTION="${1:-Manual session snapshot}"
TOPICS="${2:-general}"
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
SESSION_FILE="$SESSION_DIR/${TIMESTAMP}_session.md"

echo "=== Claude Code Session Capture ==="
echo "Timestamp: $TIMESTAMP"
echo "Description: $DESCRIPTION"
echo "Topics: $TOPICS"
echo ""

# Create session file with metadata
cat > "$SESSION_FILE" <<EOF
# Session: $TIMESTAMP

**Status**: Manual Snapshot
**Description**: $DESCRIPTION
**Topics**: [$TOPICS]
**Captured**: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Session Notes

$DESCRIPTION

## Git Status at Time of Capture

\`\`\`
$(cd "$PROJECT_ROOT" && git status -s 2>/dev/null || echo "Not a git repository")
\`\`\`

## Recent Git Commits

\`\`\`
$(cd "$PROJECT_ROOT" && git log --oneline -5 2>/dev/null || echo "No git history")
\`\`\`

## Files Modified in This Session

\`\`\`
$(cd "$PROJECT_ROOT" && git diff --name-only 2>/dev/null || echo "Unable to determine")
\`\`\`

---

## Full Transcript

To capture full transcript, use Claude Code's export feature:
1. In Claude Code, use /export or copy conversation
2. Paste below this line

---

[Transcript will be added here]

EOF

echo "✓ Session file created: $SESSION_FILE"
echo ""
echo "Next steps:"
echo "1. Copy your conversation transcript and paste into: $SESSION_FILE"
echo "2. Run: python3 $SCRIPT_DIR/index_session.py $SESSION_FILE"
echo "3. Test with: /recall query='your question'"
echo ""
echo "Quick edit: open $SESSION_FILE"
