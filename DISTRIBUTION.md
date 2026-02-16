# Context Recall System - Distribution Guide

Complete guide for packaging and distributing the recall system across projects and to other users.

## 📦 Distribution Methods Summary

| Method | Best For | Setup Time | Updates |
|--------|----------|------------|---------|
| **Install Script** | Quick local installs | 2 min | Manual |
| **Git Clone** | Development/testing | 1 min | Git pull |
| **Symlink** | Multiple local projects | 5 min | Automatic |
| **pip Package** | Public distribution | 10 min | pip install |
| **Git Submodule** | Version control | 2 min | Git update |
| **Template Repo** | New projects | 1 min | Fork/clone |

---

## 🚀 Quick Distribution (Recommended)

### For Your Other Local Projects

**Option 1: Install Script (Simplest)**

```bash
# In your new project
cd /path/to/new-project

# Copy install script from existing project
cp /path/to/existing-project/.claude/skills/recall/install.sh /tmp/

# Run installer
bash /tmp/install.sh

# Or one-liner from existing project:
bash /path/to/existing-project/.claude/skills/recall/install.sh
```

**What it does**:
- ✅ Copies all files to `.claude/skills/recall/`
- ✅ Installs dependencies
- ✅ Configures hooks
- ✅ Updates CLAUDE.md
- ✅ Runs tests

**Time**: ~2 minutes

---

**Option 2: Symlink (Best for Multiple Projects)**

Install once, use everywhere:

```bash
# 1. Create shared location
mkdir -p ~/.claude/shared/
cp -r /path/to/existing-project/.claude/skills/recall ~/.claude/shared/

# 2. In each new project, symlink
cd /path/to/project-1
mkdir -p .claude/skills
ln -s ~/.claude/shared/recall .claude/skills/recall

cd /path/to/project-2
mkdir -p .claude/skills
ln -s ~/.claude/shared/recall .claude/skills/recall

# 3. Configure hooks in each project's settings.json
# (See hook configuration below)
```

**Benefits**:
- ✅ Single installation
- ✅ All projects auto-update when you update shared location
- ✅ Save disk space

**Time**: 5 minutes initial, <1 minute per additional project

---

### For Other Users

**Option 1: GitHub Release (Recommended)**

1. **Create standalone repository**:

```bash
# Extract recall system to new repo
mkdir claude-recall
cd claude-recall

# Copy files
cp -r /path/to/project/.claude/skills/recall/* .
cp /path/to/project/.claude/PROACTIVE_RECALL_GUIDE.md docs/
cp /path/to/project/.claude/SEMANTIC_SEARCH_TEST_REPORT.md docs/

# Initialize git
git init
git add .
git commit -m "Initial release of Context Recall System"

# Push to GitHub
gh repo create claude-recall --public --source=. --remote=origin --push
```

2. **Create release**:

```bash
# Tag version
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Create GitHub release
gh release create v1.0.0 \
  --title "Context Recall System v1.0.0" \
  --notes "See README.md for installation instructions"
```

3. **Users install**:

```bash
# Download and install
curl -fsSL https://raw.githubusercontent.com/your-org/claude-recall/main/install.sh | bash

# Or manual:
git clone https://github.com/your-org/claude-recall.git /tmp/claude-recall
cd /tmp/claude-recall
bash install.sh
```

---

**Option 2: pip Package (For Python Users)**

1. **Prepare package structure**:

```
claude-recall/
├── setup.py
├── pyproject.toml
├── README.md
├── LICENSE
├── claude_recall/
│   ├── __init__.py
│   ├── capture.py
│   ├── search.py
│   ├── smart_recall.py
│   └── cli.py
├── config/
│   └── secret_patterns.json
└── tests/
    └── test_*.py
```

2. **Build package**:

```bash
# Install build tools
python3 -m pip install --upgrade build twine

# Build
python3 -m build

# This creates:
# dist/claude-recall-1.0.0.tar.gz
# dist/claude_recall-1.0.0-py3-none-any.whl
```

3. **Publish**:

```bash
# Test on TestPyPI first
python3 -m twine upload --repository testpypi dist/*

# If looks good, publish to PyPI
python3 -m twine upload dist/*
```

4. **Users install**:

```bash
# Install from PyPI
pip install claude-recall

# With semantic search
pip install claude-recall[semantic]

# Initialize in project
claude-recall init
```

---

## 📁 Package Structure for Distribution

### Standalone Repository Layout

```
claude-recall/
├── README.md                    # Main documentation
├── LICENSE                      # MIT License
├── install.sh                   # Automated installer
├── setup.py                     # pip package setup
├── pyproject.toml              # Modern Python packaging
│
├── scripts/                     # Core scripts
│   ├── auto_capture.py
│   ├── index_session.py
│   ├── search_index.py
│   ├── embed_sessions.py
│   ├── smart_recall.py
│   ├── session_start_recall.py
│   ├── redact_secrets.py
│   ├── test_bm25.py
│   └── test_semantic.py
│
├── config/                      # Configuration files
│   └── secret_patterns.json
│
├── tests/                       # Test suite
│   └── test_redact_secrets.py
│
├── docs/                        # Documentation
│   ├── INSTALL.md
│   ├── SEMANTIC_SEARCH.md
│   ├── PROACTIVE_RECALL_GUIDE.md
│   ├── PHASE3_ANALYSIS.md
│   └── SEMANTIC_SEARCH_TEST_REPORT.md
│
├── requirements-core.txt        # BM25 dependencies
├── requirements-optional.txt   # Semantic search dependencies
│
└── examples/                    # Example configurations
    ├── settings.json.example
    └── CLAUDE.md.example
```

---

## 🔧 Creating a Standalone Repository

### Step-by-Step Extraction

```bash
# 1. Create new directory
mkdir -p ~/claude-recall
cd ~/claude-recall

# 2. Copy recall system files
SOURCE="/path/to/existing-project/.claude/skills/recall"
cp -r $SOURCE/scripts ./
cp -r $SOURCE/config ./
cp -r $SOURCE/tests ./
cp $SOURCE/requirements-*.txt ./
cp $SOURCE/install.sh ./
cp $SOURCE/setup.py ./

# 3. Copy documentation
mkdir docs
cp /path/to/existing-project/.claude/PROACTIVE_RECALL_GUIDE.md docs/
cp /path/to/existing-project/.claude/SEMANTIC_SEARCH_TEST_REPORT.md docs/
cp /path/to/existing-project/.claude/PHASE3_ANALYSIS.md docs/
cp $SOURCE/README.md ./
cp $SOURCE/SEMANTIC_SEARCH.md docs/
cp $SOURCE/INSTALL.md docs/

# 4. Create examples directory
mkdir examples
cat > examples/settings.json.example <<'EOF'
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
EOF

# 5. Create pyproject.toml for modern packaging
cat > pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "claude-recall"
version = "1.0.0"
description = "Automatic context recall system for Claude Code"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "rank-bm25>=0.2.2",
]

[project.optional-dependencies]
semantic = [
    "sentence-transformers>=2.2.0",
    "torch>=1.11.0",
    "transformers>=4.41.0",
]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
]

[project.urls]
Homepage = "https://github.com/your-org/claude-recall"
Documentation = "https://github.com/your-org/claude-recall#readme"
Repository = "https://github.com/your-org/claude-recall"
Issues = "https://github.com/your-org/claude-recall/issues"

[project.scripts]
claude-recall = "scripts.cli:main"
EOF

# 6. Create LICENSE
cat > LICENSE <<'EOF'
MIT License

Copyright (c) 2026 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# 7. Create .gitignore
cat > .gitignore <<'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.env
.venv
env/
venv/
.DS_Store
*.swp
*.swo
*~
EOF

# 8. Initialize git
git init
git add .
git commit -m "Initial release: Context Recall System v1.0.0"

# 9. Create GitHub repo
gh repo create claude-recall \
  --public \
  --description "Automatic context recall system for Claude Code" \
  --source=. \
  --remote=origin \
  --push

# 10. Create release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
gh release create v1.0.0 \
  --title "Context Recall System v1.0.0" \
  --notes-file docs/INSTALL.md
```

---

## 🌐 Distribution Channels

### 1. GitHub (Recommended)

**Advantages**:
- ✅ Free hosting
- ✅ Version control
- ✅ Issue tracking
- ✅ Release management
- ✅ Easy installation (`curl | bash`)

**Setup**:
```bash
gh repo create claude-recall --public
git push origin main
```

**User installation**:
```bash
curl -fsSL https://raw.githubusercontent.com/USERNAME/claude-recall/main/install.sh | bash
```

---

### 2. PyPI (For Python Package)

**Advantages**:
- ✅ Standard Python distribution
- ✅ `pip install` simplicity
- ✅ Dependency management
- ✅ Version management

**Setup**:
```bash
python3 -m build
python3 -m twine upload dist/*
```

**User installation**:
```bash
pip install claude-recall
claude-recall init
```

---

### 3. npm (If Creating Node.js Wrapper)

For projects that prefer npm:

**Setup**:
```bash
npm init
npm publish
```

**User installation**:
```bash
npx claude-recall init
```

---

### 4. Docker Hub (Containerized)

For teams using containers:

**Dockerfile**:
```dockerfile
FROM python:3.12-slim
WORKDIR /workspace
COPY . /usr/local/claude-recall
RUN pip install --no-cache-dir /usr/local/claude-recall
CMD ["claude-recall", "init"]
```

**User installation**:
```bash
docker run -v $(pwd):/workspace claude-recall/recall-system init
```

---

## 📚 Documentation Package

### Essential Documentation Files

1. **README.md** - Quick start and overview
2. **INSTALL.md** - Detailed installation instructions
3. **SEMANTIC_SEARCH.md** - Feature documentation
4. **PROACTIVE_RECALL_GUIDE.md** - Usage guide
5. **EXAMPLES.md** - Example configurations
6. **TROUBLESHOOTING.md** - Common issues
7. **CHANGELOG.md** - Version history
8. **CONTRIBUTING.md** - Development guide

### README.md Template

```markdown
# Context Recall System

Automatic context recall for Claude Code conversations.

## Features

- ✅ Auto-capture sessions at end
- ✅ BM25 + semantic search
- ✅ Secret redaction
- ✅ Proactive recall during conversations

## Quick Install

bash
curl -fsSL https://url/install.sh | bash


## Documentation

- [Installation Guide](docs/INSTALL.md)
- [Semantic Search](docs/SEMANTIC_SEARCH.md)
- [Proactive Recall](docs/PROACTIVE_RECALL_GUIDE.md)

## License

MIT
```

---

## 🎯 Recommended Distribution Strategy

### For Personal Use Across Projects

**Use symlink approach**:
- Install once in `~/.claude/shared/recall`
- Symlink in each project
- Easy updates, single source of truth

### For Team Distribution

**Use Git repository**:
- Host on GitHub/GitLab
- Install script for easy setup
- Issue tracking for bugs
- Release management for versions

### For Public Distribution

**Use multiple channels**:
1. **GitHub** - Primary source, documentation
2. **PyPI** - pip install convenience
3. **Template repo** - Easy project starts
4. **Blog post** - Announce and explain

---

## ✅ Pre-Distribution Checklist

Before sharing publicly:

- [ ] Remove any private/sensitive information
- [ ] Update author/email in setup.py
- [ ] Add LICENSE file (MIT recommended)
- [ ] Test installation on clean system
- [ ] Write comprehensive README
- [ ] Create usage examples
- [ ] Document known limitations
- [ ] Set up issue templates
- [ ] Create GitHub releases
- [ ] Write announcement post

---

## 📊 Version Management

### Semantic Versioning

Use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Example:
- v1.0.0 - Initial release
- v1.1.0 - Add new search mode
- v1.1.1 - Fix bug in search
- v2.0.0 - Change hook configuration format

### Release Process

```bash
# 1. Update version in setup.py and pyproject.toml

# 2. Update CHANGELOG.md

# 3. Commit changes
git add .
git commit -m "Bump version to 1.1.0"

# 4. Tag release
git tag -a v1.1.0 -m "Release v1.1.0"

# 5. Push
git push origin main --tags

# 6. Create GitHub release
gh release create v1.1.0 --notes "See CHANGELOG.md"

# 7. Publish to PyPI (if applicable)
python3 -m build
python3 -m twine upload dist/*
```

---

## 🤝 Support & Community

### Issue Tracking

Set up GitHub Issues with templates:

**.github/ISSUE_TEMPLATE/bug_report.md**:
```markdown
**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce.

**Expected behavior**
What you expected.

**System info**
- OS: [e.g. macOS 14.0]
- Python version: [e.g. 3.12]
- Installation method: [e.g. pip, script]
```

### Discussions

Enable GitHub Discussions for:
- Questions and answers
- Feature requests
- Show and tell
- General discussion

---

## 📝 License Recommendations

**MIT License** (Recommended):
- ✅ Very permissive
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed

**Apache 2.0**:
- Similar to MIT
- Explicit patent grant
- More formal

**GPL v3**:
- Copyleft - derivatives must be open source
- More restrictive

Choose MIT for maximum adoption and simplicity.

---

## 🎉 Summary

**For your local projects**:
```bash
# Symlink approach (recommended)
mkdir -p ~/.claude/shared
cp -r .claude/skills/recall ~/.claude/shared/
ln -s ~/.claude/shared/recall .claude/skills/recall  # in each project
```

**For other users**:
```bash
# Create GitHub repo + install script
gh repo create claude-recall --public
# Users install with:
# curl -fsSL https://url/install.sh | bash
```

**For public distribution**:
- GitHub repository with releases
- pip package (optional)
- Comprehensive documentation
- Support via issues/discussions

Choose the method that fits your distribution needs!
