#!/bin/bash
# Context Recall System - Automated Installation Script
# Usage: ./install.sh [options]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR=".claude/skills/recall"
DOCS_DIR=".claude"
SETTINGS_FILE=".claude/settings.json"
CLAUDE_MD="CLAUDE.md"

# Options
SKIP_DEPS=false
SKIP_SEMANTIC=false
SKIP_HOOKS=false
SKIP_TESTS=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-deps)
      SKIP_DEPS=true
      shift
      ;;
    --skip-semantic)
      SKIP_SEMANTIC=true
      shift
      ;;
    --skip-hooks)
      SKIP_HOOKS=true
      shift
      ;;
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    -h|--help)
      echo "Context Recall System - Installation Script"
      echo ""
      echo "Usage: ./install.sh [options]"
      echo ""
      echo "Options:"
      echo "  --skip-deps      Skip Python dependency installation"
      echo "  --skip-semantic  Skip semantic search dependencies (faster)"
      echo "  --skip-hooks     Skip automatic hook configuration"
      echo "  --skip-tests     Skip installation tests"
      echo "  --force          Overwrite existing installation"
      echo "  -h, --help       Show this help message"
      echo ""
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Helper functions
print_header() {
  echo -e "${BLUE}============================================================${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}============================================================${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
  echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
  print_header "Checking Prerequisites"

  # Check Python
  if ! command -v python3 &> /dev/null; then
    print_error "python3 not found. Please install Python 3.8 or later."
    exit 1
  fi
  print_success "Python3: $(python3 --version)"

  # Check pip
  if ! python3 -m pip --version &> /dev/null; then
    print_error "pip not found. Please install pip."
    exit 1
  fi
  print_success "pip: $(python3 -m pip --version | head -n1)"

  # Check we're in a project directory
  if [[ ! -d ".claude" ]]; then
    print_warning ".claude directory not found. Creating..."
    mkdir -p .claude
  fi

  # Check for existing installation
  if [[ -d "$INSTALL_DIR" ]] && [[ "$FORCE" != true ]]; then
    print_error "Recall system already installed at $INSTALL_DIR"
    print_info "Use --force to overwrite existing installation"
    exit 1
  fi

  echo ""
}

# Create directory structure
create_directories() {
  print_header "Creating Directory Structure"

  mkdir -p "$INSTALL_DIR/scripts"
  mkdir -p "$INSTALL_DIR/config"
  mkdir -p "$INSTALL_DIR/tests"
  mkdir -p "$DOCS_DIR/context/sessions"

  print_success "Directories created"
  echo ""
}

# Copy files
copy_files() {
  print_header "Installing Files"

  local SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # Copy scripts
  print_info "Copying scripts..."
  cp "$SOURCE_DIR/scripts/"*.py "$INSTALL_DIR/scripts/"
  chmod +x "$INSTALL_DIR/scripts/"*.py
  print_success "Scripts installed"

  # Copy config
  print_info "Copying config files..."
  cp "$SOURCE_DIR/config/"*.json "$INSTALL_DIR/config/" 2>/dev/null || true
  print_success "Config files installed"

  # Copy tests
  print_info "Copying tests..."
  cp -r "$SOURCE_DIR/tests/"*.py "$INSTALL_DIR/tests/" 2>/dev/null || true
  print_success "Tests installed"

  # Copy requirements
  print_info "Copying requirements..."
  cp "$SOURCE_DIR/requirements-"*.txt "$INSTALL_DIR/"
  print_success "Requirements files installed"

  # Copy documentation
  print_info "Copying documentation..."
  cp "$SOURCE_DIR/README.md" "$INSTALL_DIR/" 2>/dev/null || true
  cp "$SOURCE_DIR/SEMANTIC_SEARCH.md" "$INSTALL_DIR/" 2>/dev/null || true
  cp "$SOURCE_DIR/INSTALL.md" "$INSTALL_DIR/" 2>/dev/null || true
  cp "$SOURCE_DIR/../PROACTIVE_RECALL_GUIDE.md" "$DOCS_DIR/" 2>/dev/null || true
  print_success "Documentation installed"

  echo ""
}

# Install dependencies
install_dependencies() {
  if [[ "$SKIP_DEPS" == true ]]; then
    print_warning "Skipping dependency installation (--skip-deps)"
    return
  fi

  print_header "Installing Dependencies"

  # Install core dependencies (BM25)
  print_info "Installing core dependencies (rank-bm25)..."
  python3 -m pip install --user -q -r "$INSTALL_DIR/requirements-core.txt"
  print_success "Core dependencies installed"

  # Install semantic search dependencies (optional)
  if [[ "$SKIP_SEMANTIC" != true ]]; then
    print_info "Installing semantic search dependencies (sentence-transformers)..."
    print_warning "This may take a few minutes (~500MB download)..."
    python3 -m pip install --user -q -r "$INSTALL_DIR/requirements-optional.txt"
    print_success "Semantic search dependencies installed"
  else
    print_warning "Skipping semantic search dependencies (--skip-semantic)"
    print_info "System will fall back to BM25-only search"
  fi

  echo ""
}

# Configure hooks
configure_hooks() {
  if [[ "$SKIP_HOOKS" == true ]]; then
    print_warning "Skipping hook configuration (--skip-hooks)"
    return
  fi

  print_header "Configuring Hooks"

  # Create settings.json if it doesn't exist
  if [[ ! -f "$SETTINGS_FILE" ]]; then
    print_info "Creating $SETTINGS_FILE..."
    cat > "$SETTINGS_FILE" <<'EOF'
{
  "hooks": {}
}
EOF
  fi

  # Check if we have jq for JSON manipulation
  if command -v jq &> /dev/null; then
    print_info "Using jq to update settings.json..."

    # Add SessionStart hook
    TMP_FILE=$(mktemp)
    jq '.hooks.SessionStart = [{"matcher": "*", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/skills/recall/scripts/session_start_recall.py"}]}]' "$SETTINGS_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$SETTINGS_FILE"

    # Add SessionEnd hook
    TMP_FILE=$(mktemp)
    jq '.hooks.SessionEnd = [{"matcher": "*", "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/skills/recall/scripts/auto_capture.py"}]}]' "$SETTINGS_FILE" > "$TMP_FILE"
    mv "$TMP_FILE" "$SETTINGS_FILE"

    print_success "Hooks configured in settings.json"
  else
    print_warning "jq not found. Please manually add hooks to $SETTINGS_FILE"
    print_info "See INSTALL.md for hook configuration"
  fi

  echo ""
}

# Update CLAUDE.md
update_claude_md() {
  print_header "Updating CLAUDE.md"

  if [[ ! -f "$CLAUDE_MD" ]]; then
    print_warning "CLAUDE.md not found. Skipping..."
    return
  fi

  # Check if proactive recall section already exists
  if grep -q "Proactive Context Recall" "$CLAUDE_MD"; then
    print_info "CLAUDE.md already contains recall instructions"
  else
    print_info "Adding proactive recall instructions to CLAUDE.md..."
    cat >> "$CLAUDE_MD" <<'EOF'

## Proactive Context Recall

See .claude/PROACTIVE_RECALL_GUIDE.md for complete instructions.

Quick reference:
- System automatically searches when topics mentioned
- SessionStart hook provides context at session start
- Use search_index.py or smart_recall.py for on-demand searches

EOF
    print_success "CLAUDE.md updated"
  fi

  echo ""
}

# Run tests
run_tests() {
  if [[ "$SKIP_TESTS" == true ]]; then
    print_warning "Skipping tests (--skip-tests)"
    return
  fi

  print_header "Running Tests"

  # Test core dependencies
  print_info "Testing core dependencies..."
  if python3 -c "import rank_bm25" 2>/dev/null; then
    print_success "rank-bm25 installed correctly"
  else
    print_error "rank-bm25 not found"
    return 1
  fi

  # Test semantic dependencies (if installed)
  if [[ "$SKIP_SEMANTIC" != true ]]; then
    print_info "Testing semantic search dependencies..."
    if python3 -c "import sentence_transformers" 2>/dev/null; then
      print_success "sentence-transformers installed correctly"
    else
      print_warning "sentence-transformers not found (expected if --skip-semantic)"
    fi
  fi

  # Test scripts
  print_info "Testing scripts..."
  if python3 "$INSTALL_DIR/scripts/search_index.py" --help &>/dev/null; then
    print_success "search_index.py works"
  else
    print_error "search_index.py failed"
    return 1
  fi

  if python3 "$INSTALL_DIR/scripts/smart_recall.py" --help &>/dev/null; then
    print_success "smart_recall.py works"
  else
    print_error "smart_recall.py failed"
    return 1
  fi

  print_success "All tests passed"
  echo ""
}

# Print summary
print_summary() {
  print_header "Installation Complete!"

  echo ""
  echo -e "${GREEN}✓ Context Recall System installed successfully${NC}"
  echo ""
  echo "📁 Installation directory: $INSTALL_DIR"
  echo "📖 Documentation: $INSTALL_DIR/README.md"
  echo "🚀 Quick start: $DOCS_DIR/PROACTIVE_RECALL_GUIDE.md"
  echo ""

  if [[ "$SKIP_HOOKS" != true ]]; then
    echo -e "${GREEN}Hooks configured:${NC}"
    echo "  ✓ SessionStart: Automatic context recall"
    echo "  ✓ SessionEnd: Automatic session capture"
    echo ""
  fi

  if [[ "$SKIP_SEMANTIC" == true ]]; then
    echo -e "${YELLOW}Note: Semantic search not installed (BM25-only mode)${NC}"
    echo "To enable semantic search later:"
    echo "  python3 -m pip install --user sentence-transformers"
    echo "  python3 $INSTALL_DIR/scripts/embed_sessions.py"
    echo ""
  fi

  echo -e "${BLUE}Next steps:${NC}"
  echo "1. Start a new Claude Code session (hook will activate)"
  echo "2. Or test manually:"
  echo "     python3 $INSTALL_DIR/scripts/smart_recall.py --context \"test\""
  echo "3. Generate embeddings (if semantic search installed):"
  echo "     python3 $INSTALL_DIR/scripts/embed_sessions.py"
  echo ""
  echo "For detailed usage, see:"
  echo "  - $INSTALL_DIR/README.md"
  echo "  - $INSTALL_DIR/SEMANTIC_SEARCH.md"
  echo "  - $DOCS_DIR/PROACTIVE_RECALL_GUIDE.md"
  echo ""
}

# Main installation flow
main() {
  print_header "Context Recall System - Installation"
  echo ""

  check_prerequisites
  create_directories
  copy_files
  install_dependencies
  configure_hooks
  update_claude_md
  run_tests
  print_summary
}

# Run main
main
