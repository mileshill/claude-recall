# Claude Recall

> Automatic context recall system for [Claude Code](https://claude.ai/code) conversations

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Never lose context across sessions. Claude Recall automatically captures, indexes, and retrieves conversation history, enabling Claude to remember and build on previous work.

## ✨ Features

- 🔄 **Auto-Capture**: Automatically saves conversation context at session end
- 🔍 **Hybrid Search**: BM25 keyword matching + semantic embeddings
- 🤖 **Proactive Recall**: Claude automatically searches when you mention topics
- 🔒 **Secret Redaction**: 35 patterns + entropy detection prevents credential leaks
- ⚡ **Fast**: 7-10ms search latency (100x under target)
- 🎯 **Smart**: Understands concepts, not just keywords
- 📊 **Temporal Decay**: Recent sessions weighted higher
- 🔧 **Easy Install**: One command setup

## 🚀 Quick Start

### Installation

\`\`\`bash
# One-command install
curl -fsSL https://raw.githubusercontent.com/mileshill/claude-recall/main/install.sh | bash

# Or manual
git clone https://github.com/mileshill/claude-recall.git
cd claude-recall
bash install.sh
\`\`\`

See [INSTALL.md](INSTALL.md) for all installation methods.

## 📊 Analytics & Insights (Optional)

Track recall efficacy and optimize performance with the built-in analytics system:

**Features:**
- 📈 **Telemetry**: Automatic tracking of all recall operations
- 🎯 **Impact Analysis**: Measure conversation continuity and time saved
- ⭐ **Quality Scoring**: LLM-based evaluation (optional, ~$0.50/month)
- 🔍 **Quality Checks**: 7 automated health monitors
- 📑 **Reporting**: Generate comprehensive analytics reports

**Quick Start:**
```bash
# Generate summary report
python3 scripts/generate_recall_report.py --summary

# Run quality checks
python3 scripts/run_quality_checks.py --quick

# Full 30-day report
python3 scripts/generate_recall_report.py --period 30 --output report.md
```

See [Analytics Guide](docs/ANALYTICS_GUIDE.md) for complete documentation.

## 📖 Full Documentation

### Core Features
- [Installation Guide](INSTALL.md) - 9 installation methods
- [Semantic Search](SEMANTIC_SEARCH.md) - Search algorithms and features
- [Proactive Recall](PROACTIVE_RECALL_GUIDE.md) - How Claude uses recall
- [Distribution Guide](DISTRIBUTION.md) - Share across projects
- [Test Report](SEMANTIC_SEARCH_TEST_REPORT.md) - Performance validation

### Analytics (Optional)
- [Analytics Guide](docs/ANALYTICS_GUIDE.md) - Complete analytics documentation
- [Telemetry Schema](docs/TELEMETRY_SCHEMA.md) - Event types and fields reference
- [Quality Checks Guide](docs/QUALITY_CHECKS_GUIDE.md) - Understanding health checks
- [Quality Checks Scheduling](docs/QUALITY_CHECKS_SCHEDULING.md) - Automated monitoring setup
- [Analytics Config Reference](config/ANALYTICS_CONFIG.md) - Configuration options
- [Shared Utilities](scripts/metrics/README.md) - Developer API reference

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for the Claude Code community**

[⭐ Star this repo](https://github.com/mileshill/claude-recall) if you find it useful!
