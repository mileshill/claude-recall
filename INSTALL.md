# Context Recall System - Installation Guide

Multiple installation methods for different use cases.

## Quick Install (Recommended)

### Method 1: Automated Installation Script

One command to install everything:

```bash
curl -fsSL https://raw.githubusercontent.com/your-org/claude-recall/main/install.sh | bash
```

Or download and run:

```bash
wget https://raw.githubusercontent.com/your-org/claude-recall/main/install.sh
chmod +x install.sh
./install.sh
```

**What it does**:
- ✅ Copies all scripts to `.claude/skills/recall/`
- ✅ Installs Python dependencies
- ✅ Configures SessionStart and SessionEnd hooks
- ✅ Tests installation
- ✅ Displays usage instructions

---

## Manual Installation

### Method 2: Copy from Template

If you already have the recall system in one project:

```bash
# From project WITH recall system
cd /path/to/project-with-recall

# Copy to new project
cp -r .claude/skills/recall /path/to/new-project/.claude/skills/
cp .claude/PROACTIVE_RECALL_GUIDE.md /path/to/new-project/.claude/

# Install dependencies
cd /path/to/new-project
python3 -m pip install --user -r .claude/skills/recall/requirements-core.txt
python3 -m pip install --user -r .claude/skills/recall/requirements-optional.txt

# Configure hooks (see Method 3)
```

---

### Method 3: Add to Existing Project

Add recall to a project with existing `.claude/settings.json`:

**Step 1: Copy files**
```bash
# Download recall system
git clone https://github.com/your-org/claude-recall.git /tmp/claude-recall
cp -r /tmp/claude-recall/skills/recall .claude/skills/
cp /tmp/claude-recall/docs/* .claude/
```

**Step 2: Install dependencies**
```bash
python3 -m pip install --user rank-bm25>=0.2.2
python3 -m pip install --user sentence-transformers>=2.2.0  # Optional
```

**Step 3: Update settings.json**

Add hooks to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/skills/recall/scripts/session_start_recall.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/skills/recall/scripts/auto_capture.py"
          }
        ]
      }
    ]
  }
}
```

**Step 4: Update CLAUDE.md** (optional)

Add proactive recall instructions:
```bash
cat .claude/PROACTIVE_RECALL_GUIDE.md >> CLAUDE.md
```

**Step 5: Test**
```bash
# Test capture
python3 .claude/skills/recall/scripts/auto_capture.py <<< '{"session_id":"test","transcript_path":"/tmp/test.jsonl","reason":"test"}'

# Test search
python3 .claude/skills/recall/scripts/search_index.py --query "test"

# Test smart recall
python3 .claude/skills/recall/scripts/smart_recall.py --context "test context"
```

---

## Distribution Options

### Method 4: Claude Code Plugin (Future)

Package as a Claude Code plugin for marketplace distribution:

```bash
# Install from Claude Code marketplace (when available)
/plugin install recall-system@official
```

---

### Method 5: Python Package (pip)

Install as a Python package:

```bash
# Install system-wide or in virtualenv
pip install claude-recall

# Initialize in project
claude-recall init

# This would:
# - Create .claude/skills/recall/
# - Generate settings.json hooks
# - Install dependencies
# - Run tests
```

---

### Method 6: Git Submodule

For projects in git, use as a submodule:

```bash
# Add as submodule
git submodule add https://github.com/your-org/claude-recall.git .claude/skills/recall

# Initialize in new clone
git submodule update --init --recursive

# Update to latest
cd .claude/skills/recall
git pull origin main
cd ../../..
git add .claude/skills/recall
git commit -m "Update recall system"
```

---

### Method 7: Template Repository

Use as a template for new projects:

```bash
# Create new project from template
gh repo create my-project --template your-org/claude-code-template

# The template includes:
# - .claude/skills/recall/ (complete system)
# - .claude/settings.json (hooks configured)
# - CLAUDE.md (with recall instructions)
# - requirements.txt (dependencies)
```

---

## Quick Start for Multi-Project Use

### Option A: Symlink (Single Install)

Install once, use everywhere:

```bash
# Install in a central location
mkdir -p ~/.claude/shared/recall
cp -r .claude/skills/recall/* ~/.claude/shared/recall/

# Symlink in each project
cd /path/to/project
mkdir -p .claude/skills
ln -s ~/.claude/shared/recall .claude/skills/recall

# Update settings.json to use symlinked path
```

**Pros**: Single installation, easy updates
**Cons**: All projects share same version

---

### Option B: Separate Installs

Install separately in each project:

```bash
# Use install script per project
cd /path/to/project
curl -fsSL https://url/install.sh | bash
```

**Pros**: Each project independent
**Cons**: Manual updates per project

---

## For Teams / Organizations

### Method 8: Internal Package Repository

For enterprise use:

```bash
# Host on internal PyPI server
pip install claude-recall --index-url https://pypi.company.com/simple

# Or internal git server
pip install git+https://github.company.com/tools/claude-recall.git
```

---

### Method 9: Docker Container

Include in development containers:

```dockerfile
FROM python:3.12

# Install recall system
RUN pip install claude-recall

# Configure for project
WORKDIR /workspace
COPY .claude .claude/
RUN claude-recall init
```

---

## Configuration Options

### Minimal Setup (BM25 Only)

Just keyword search, no embeddings:

```bash
# Install only core dependencies
pip install rank-bm25

# Skip semantic search installation
# System automatically falls back to BM25
```

---

### Full Setup (BM25 + Semantic)

Complete system with semantic search:

```bash
# Install all dependencies
pip install rank-bm25 sentence-transformers

# Generate embeddings
python3 .claude/skills/recall/scripts/embed_sessions.py
```

### Analytics Setup (Optional)

Enable analytics and quality checks:

```bash
# Install analytics dependencies
pip install jinja2  # For report templates
pip install pytest  # For running tests (optional)

# Enable analytics in config
# Edit config/analytics_config.json:
# Set telemetry.enabled, impact_analysis.enabled, quality_checks.enabled to true

# Optional: Enable quality scoring (requires API key)
export ANTHROPIC_API_KEY="your-api-key"
# Set quality_scoring.enabled to true in analytics_config.json
```

**What you get:**
- Automatic telemetry tracking
- Impact analysis after sessions
- Quality checks (7 automated checks)
- Report generation
- Optional LLM-based quality scoring (~$0.50/month)

**Quick test:**
```bash
# Generate summary report
python3 scripts/generate_recall_report.py --summary

# Run quality checks
python3 scripts/run_quality_checks.py --quick
```

See [Analytics Guide](docs/ANALYTICS_GUIDE.md) for complete documentation.

---

### Custom Configuration

Adjust thresholds and parameters:

**Edit `session_start_recall.py`**:
```python
# Line 24: Minimum relevance threshold
min_relevance=0.4,  # 0.3 = more results, 0.5 = fewer results

# Line 23: Number of results
limit=3,  # Show top 3 (increase/decrease as needed)

# Line 22: Search mode
search_mode="auto",  # auto, hybrid, bm25, semantic
```

**Edit `auto_capture.py`**:
```python
# Add custom metadata
metadata["project_name"] = "My Project"
metadata["team"] = "Engineering"
```

---

## Verification

After installation, verify everything works:

```bash
# 1. Check files exist
ls -la .claude/skills/recall/scripts/

# 2. Check dependencies
python3 -c "import rank_bm25; print('✓ rank-bm25')"
python3 -c "import sentence_transformers; print('✓ sentence-transformers')"

# 3. Test search
python3 .claude/skills/recall/scripts/search_index.py --query "test"

# 4. Test smart recall
python3 .claude/skills/recall/scripts/smart_recall.py --context "test"

# 5. Check hooks configured
jq '.hooks' .claude/settings.json
```

Expected output:
```
✓ rank-bm25
✓ sentence-transformers
Found X matching session(s)
[Search results displayed]
```

---

## Troubleshooting

### Issue: "No module named 'rank_bm25'"

**Solution**:
```bash
python3 -m pip install --user rank-bm25
```

### Issue: "No session index found"

**Solution**:
```bash
# Create a test session to initialize
echo '{"session_id":"test","transcript_path":"/tmp/test.jsonl","reason":"test"}' | \
  python3 .claude/skills/recall/scripts/auto_capture.py
```

### Issue: "SessionStart hook not running"

**Solution**:
```bash
# 1. Check settings.json syntax
jq . .claude/settings.json

# 2. Test hook manually
python3 .claude/skills/recall/scripts/session_start_recall.py

# 3. Check script executable
chmod +x .claude/skills/recall/scripts/*.py

# 4. Check Claude Code logs
tail -f ~/.claude/logs/*.log
```

### Issue: "Semantic search not working"

**Solution**:
```bash
# 1. Install dependencies
python3 -m pip install --user sentence-transformers

# 2. Generate embeddings
python3 .claude/skills/recall/scripts/embed_sessions.py

# 3. Verify embeddings exist
ls -lh .claude/context/sessions/embeddings.npz
```

### Issue: "Analytics reports show no data"

**Problem**: Reports show "No search activity recorded" despite using recall.

**Root Causes & Solutions**:

1. **Event type mismatch** (Fixed in v1.0.1):
   ```bash
   # Verify you have the latest aggregator.py
   grep "recall_triggered" ~/.claude/shared/recall/scripts/reporting/aggregator.py
   # Should find multiple matches
   ```

2. **Hooks not configured**:
   ```bash
   # Check if hooks are configured
   grep -A 10 "hooks" ~/.claude/settings.json

   # Should see SessionStart and SessionEnd hooks
   # If missing, add them (see Step 3 in Method 3 above)
   ```

3. **Incorrect hook paths**:
   - If using shared install at `~/.claude/shared/recall/`, hooks should use absolute paths:
   ```json
   {
     "hooks": {
       "SessionStart": [{
         "matcher": "*",
         "hooks": [{
           "type": "command",
           "command": "python3 ~/.claude/shared/recall/scripts/session_start_recall.py"
         }]
       }],
       "SessionEnd": [{
         "matcher": "*",
         "hooks": [{
           "type": "command",
           "command": "python3 ~/.claude/shared/recall/scripts/auto_capture.py"
         }]
       }]
     }
   }
   ```

4. **Quality scoring disabled**:
   ```bash
   # Check config
   grep -A 2 "quality_scoring" ~/.claude/shared/recall/config/analytics_config.json

   # Enable if needed (costs ~$0.50/month with API key, or free with heuristic fallback)
   # Edit config/analytics_config.json: "enabled": true
   ```

5. **Impact analysis not running**:
   ```bash
   # Verify impact log exists after a session ends
   ls -la ~/.claude/context/sessions/context_impact.jsonl

   # If missing, hooks may not be triggering
   # Check Claude Code logs for hook errors
   ```

**See also**: [RECALL_ANALYTICS_FIXES_2026-02-17.md](RECALL_ANALYTICS_FIXES_2026-02-17.md)

---

## Updating

### Update from Git

```bash
cd .claude/skills/recall
git pull origin main
python3 -m pip install --user -r requirements-core.txt -U
```

### Update from pip

```bash
pip install --upgrade claude-recall
```

### Update symlinked install

```bash
cd ~/.claude/shared/recall
git pull origin main
# All projects using symlink automatically updated
```

---

## Optional: Analytics Features

The recall system includes optional analytics features for tracking efficacy and optimizing performance.

### Analytics Dependencies

```bash
# Install optional analytics dependencies
pip install --user pytest jinja2 psutil anthropic
```

**Dependencies**:
- `pytest` - For running analytics tests
- `jinja2` - For report templates
- `psutil` - For system metrics (memory, CPU)
- `anthropic` - For LLM-based quality scoring (optional, costs ~$0.12/month)

### Enable Analytics

Analytics features are configured in `config/analytics_config.json`:

```bash
# View current configuration
cat config/analytics_config.json

# Or use Python
python3 -c "from metrics.config import config; print(config.get_all())"
```

**Analytics Features**:
- **Telemetry** (enabled by default): Track all recall events
- **Impact Analysis** (enabled by default): Measure conversation improvements
- **Quality Scoring** (disabled by default): LLM-based evaluation (~$0.12/month)
- **Quality Checks** (enabled by default): Automated monitoring
- **Reporting** (enabled by default): Generate analytics reports

### Quick Status

```bash
# Check analytics status (after Phase 7 implementation)
python3 scripts/analytics_status.py

# Generate report
python3 scripts/generate_recall_report.py --summary

# Run quality checks
python3 scripts/run_quality_checks.py
```

### Configuration

See [Analytics Configuration Reference](config/ANALYTICS_CONFIG.md) for complete configuration options.

**Quick toggles**:
```json
{
  "telemetry": {"enabled": true},
  "impact_analysis": {"enabled": true},
  "quality_scoring": {"enabled": false},
  "quality_checks": {"enabled": true},
  "reporting": {"enabled": true}
}
```

---

## Uninstallation

```bash
# Remove files
rm -rf .claude/skills/recall
rm .claude/PROACTIVE_RECALL_GUIDE.md
rm .claude/SEMANTIC_SEARCH_TEST_REPORT.md

# Remove hooks from settings.json
# Edit .claude/settings.json and remove SessionStart/SessionEnd entries

# Uninstall dependencies (optional)
pip uninstall rank-bm25 sentence-transformers

# Remove captured sessions (optional - destroys history!)
rm -rf .claude/context/sessions/
```

---

## Support & Resources

- **Documentation**: `.claude/skills/recall/README.md`
- **Semantic Search Guide**: `.claude/skills/recall/SEMANTIC_SEARCH.md`
- **Proactive Recall Guide**: `.claude/PROACTIVE_RECALL_GUIDE.md`
- **Test Report**: `.claude/SEMANTIC_SEARCH_TEST_REPORT.md`

- **GitHub**: https://github.com/your-org/claude-recall
- **Issues**: https://github.com/your-org/claude-recall/issues
- **Discussions**: https://github.com/your-org/claude-recall/discussions

---

## License

MIT License - Free to use, modify, and distribute.

See LICENSE file for details.
