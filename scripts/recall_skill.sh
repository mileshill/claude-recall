#!/bin/bash
#
# /recall skill - Query past session context
#
# Usage:
#   /recall query="How did we implement X?"
#   /recall query="What was done?" session=2026-02-16
#   /recall topics="authentication, jwt"
#

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments from $ARGUMENTS environment variable or command line
QUERY=""
SCOPE="all"
SESSION=""
TOPICS=""
LIMIT="5"
MIN_RELEVANCE="0.3"
VERBOSE=""

# Parse $ARGUMENTS if set (from skill invocation)
if [ -n "$ARGUMENTS" ]; then
    # Extract query="..." pattern
    if [[ "$ARGUMENTS" =~ query=\"([^\"]+)\" ]] || [[ "$ARGUMENTS" =~ query=\'([^\']+)\' ]]; then
        QUERY="${BASH_REMATCH[1]}"
    elif [[ "$ARGUMENTS" =~ query=([^[:space:]]+) ]]; then
        QUERY="${BASH_REMATCH[1]}"
    fi

    # Extract other parameters
    [[ "$ARGUMENTS" =~ scope=([^[:space:]]+) ]] && SCOPE="${BASH_REMATCH[1]}"
    [[ "$ARGUMENTS" =~ session=([^[:space:]]+) ]] && SESSION="${BASH_REMATCH[1]}"
    [[ "$ARGUMENTS" =~ topics=\"([^\"]+)\" ]] && TOPICS="${BASH_REMATCH[1]}"
    [[ "$ARGUMENTS" =~ topics=\'([^\']+)\' ]] && TOPICS="${BASH_REMATCH[1]}"
    [[ "$ARGUMENTS" =~ topics=([^[:space:]]+) ]] && TOPICS="${BASH_REMATCH[1]}"
    [[ "$ARGUMENTS" =~ limit=([0-9]+) ]] && LIMIT="${BASH_REMATCH[1]}"
    [[ "$ARGUMENTS" =~ verbose ]] && VERBOSE="--verbose"
fi

# Also support direct command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        query=*)
            QUERY="${1#*=}"
            shift
            ;;
        scope=*)
            SCOPE="${1#*=}"
            shift
            ;;
        session=*)
            SESSION="${1#*=}"
            shift
            ;;
        topics=*)
            TOPICS="${1#*=}"
            shift
            ;;
        limit=*)
            LIMIT="${1#*=}"
            shift
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            # Assume it's a query if no key=value
            if [ -z "$QUERY" ]; then
                QUERY="$1"
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "$QUERY" ]; then
    cat >&2 <<EOF
❌ Error: query parameter required

Usage:
  /recall query="How did we implement X?"
  /recall query="What was done?" session=2026-02-16
  /recall topics="authentication, jwt"

Arguments:
  query="..."           Natural language question (required)
  scope=all|decisions   Narrow search scope (optional)
  session=YYYY-MM-DD    Search specific session (optional)
  topics="tag1,tag2"    Filter by topic tags (optional)
  limit=N               Max sessions to search (default: 5)
  --verbose, -v         Show analysis details

Examples:
  /recall query="How did we structure the auth flow?"
  /recall query="What files did we modify today?" session=2026-02-16
  /recall query="Show me decisions about caching" scope=decisions
EOF
    exit 1
fi

# Check if index exists
INDEX_PATH=".claude/context/sessions/index.json"
if [ ! -f "$INDEX_PATH" ]; then
    cat >&2 <<EOF
📭 No session history found yet.

Session capture is automatic - just continue working and sessions will be saved
when you exit. On your next session, you'll be able to recall this conversation.

To check if capture is working:
  1. Complete this session (Ctrl+D or exit)
  2. Check for .claude/context/sessions/*.md files
  3. Start a new session and use /recall

If you don't see any sessions being created, check that the SessionEnd hook
is configured in .claude/settings.json
EOF
    exit 0
fi

# Build search context from query and filters
SEARCH_CONTEXT="$QUERY"

# Add session filter to context
if [ -n "$SESSION" ]; then
    SEARCH_CONTEXT="$SEARCH_CONTEXT session:$SESSION"
fi

# Add topic filters to context
if [ -n "$TOPICS" ]; then
    SEARCH_CONTEXT="$SEARCH_CONTEXT topics:$TOPICS"
fi

# Run smart recall
echo "🔍 Searching session history..." >&2
echo "" >&2

python3 "$SCRIPT_DIR/smart_recall.py" \
    --context "$SEARCH_CONTEXT" \
    --index "$INDEX_PATH" \
    --mode auto \
    --limit "$LIMIT" \
    --min-relevance "$MIN_RELEVANCE" \
    $VERBOSE

# Check if search was successful
if [ $? -eq 0 ]; then
    echo "" >&2
    echo "💡 Tip: Use 'Read' tool to view full session files for more details" >&2
else
    echo "" >&2
    echo "❌ Search failed. Check that sessions have been indexed properly." >&2
    exit 1
fi
