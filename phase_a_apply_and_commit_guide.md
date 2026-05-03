# Phase A — Apply Changes & Push to GitHub

> Complete guide to applying all new files, replacing modified files, and making the first GitHub commit.

---

## Overview of all changes

### 🆕 New files to create

| File | Category |
|---|---|
| `brain/exceptions.py` | A2 — Error handling |
| `brain/commands/init.py` | A1 — Setup wizard |
| `tests/__init__.py` | A4 — Tests |
| `tests/conftest.py` | A4 — Tests |
| `tests/test_chunker.py` | A4 — Tests |
| `tests/test_utils.py` | A4 — Tests |
| `tests/test_retriever.py` | A4 — Tests |
| `tests/test_ingest.py` | A4 — Tests |
| `.github/workflows/tests.yml` | A4 — CI |
| `CONTRIBUTING.md` | A5 — Docs |
| `LICENSE` | A5 — Docs |

### ✏️ Files to replace (modified)

| File | What changed |
|---|---|
| `brain/cli.py` | Added `brain init`, `--version`, global error handling |
| `pyproject.toml` | Added dev deps, keywords, license metadata |
| `README.md` | Full community-ready rewrite |

---

## Step 1 — Verify your project root

```bash
cd ~/Desktop/Python/obsidian-brain
ls
```

You should see: `brain/`, `cli.py`, `pyproject.toml`, `requirements.txt`, `README.md`

---

## Step 2 — Create missing directories

```bash
mkdir -p tests
mkdir -p .github/workflows
```

---

## Step 3 — Create new files

### `brain/exceptions.py`

```bash
cat > brain/exceptions.py << 'EOF'
"""
brain/exceptions.py
All custom exceptions with user-friendly messages and fix suggestions.
"""


class BrainError(Exception):
    def __init__(self, message: str, fix: str = ""):
        self.message = message
        self.fix = fix
        super().__init__(message)


class OllamaNotRunning(BrainError):
    def __init__(self):
        super().__init__(
            message="Ollama is not running.",
            fix="Start it with:  ollama serve\nOr switch provider:  export BRAIN_LLM_PROVIDER=groq",
        )


class VaultNotFound(BrainError):
    def __init__(self, path: str):
        super().__init__(
            message=f"Vault not found at: {path}",
            fix="Run:  brain init  to reconfigure your vault path.",
        )


class VaultNotIndexed(BrainError):
    def __init__(self):
        super().__init__(
            message="Vault has not been indexed yet.",
            fix="Run:  brain ingest  to index your vault first.",
        )


class MissingAPIKey(BrainError):
    def __init__(self, provider: str):
        key_name = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}.get(provider, f"{provider.upper()}_API_KEY")
        super().__init__(
            message=f"{key_name} is not set.",
            fix=f"Add it to your .env file:\n  {key_name}=your_key_here\nOr run:  brain init  to reconfigure.",
        )


class EmbeddingFailed(BrainError):
    def __init__(self, reason: str):
        super().__init__(
            message=f"Embedding failed: {reason}",
            fix=(
                "Options:\n"
                "  1. Start Ollama:         ollama serve\n"
                "  2. Use Gemini embedding: export BRAIN_LLM_PROVIDER=gemini\n"
                "  3. Install fallback:     pip install sentence-transformers"
            ),
        )


class ProviderError(BrainError):
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"LLM provider '{provider}' failed: {reason}",
            fix="Check your API key or switch provider:  export BRAIN_LLM_PROVIDER=ollama",
        )


class ChromaError(BrainError):
    def __init__(self, reason: str):
        super().__init__(
            message=f"Database error: {reason}",
            fix="Try re-indexing:  brain ingest --force",
        )
EOF
```

### `tests/__init__.py`

```bash
touch tests/__init__.py
```

### `tests/conftest.py`

```bash
cat > tests/conftest.py << 'EOF'
import pytest
from pathlib import Path


@pytest.fixture
def tmp_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()

    (vault / "Projects.md").write_text(
        "---\ntags: [projects, work]\naliases: [my projects]\n---\n"
        "# Projects\n\nThis is my projects note.\n\n## BankPrep\n\nA React PWA for banking exams.\n"
    )
    (vault / "Ideas.md").write_text(
        "# Ideas\n\nRandom ideas go here.\n\n## RAG System\n\nBuild a local RAG for Obsidian.\n"
    )
    (vault / "Links.md").write_text(
        "# Links\n\nSee [[Projects]] and [[Ideas]] for more.\n"
        "Also check [[Projects|my work]] page.\n"
    )
    (vault / "Empty.md").write_text("")

    sub = vault / "Daily"
    sub.mkdir()
    (sub / "2024-01-01.md").write_text(
        "---\ntags: [daily]\n---\n# 2024-01-01\n\nToday I worked on the RAG system.\n"
    )
    (vault / ".obsidian" / "config.json").write_text("{}")
    return vault


@pytest.fixture
def sample_markdown():
    return """---
tags: [python, ai]
aliases: [ml notes]
---
# Machine Learning

Introduction to ML concepts.

## Supervised Learning

Learning from labeled data.

## Unsupervised Learning

Finding patterns without labels.

### Clustering

K-means and DBSCAN.
"""


@pytest.fixture
def sample_chunks():
    from brain.retriever import RetrievedChunk
    return [
        RetrievedChunk(
            doc_id="Projects.md::0",
            file_path="Projects.md",
            note_title="Projects",
            heading="__intro__",
            text="This is my projects note.",
            score=0.12,
        ),
        RetrievedChunk(
            doc_id="Ideas.md::0",
            file_path="Ideas.md",
            note_title="Ideas",
            heading="RAG System",
            text="Build a local RAG for Obsidian.",
            score=0.23,
        ),
    ]
EOF
```

### `.github/workflows/tests.yml`

```bash
cat > .github/workflows/tests.yml << 'EOF'
name: Tests

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest tests/ -v --tb=short
      - name: Check coverage
        run: pytest tests/ --cov=brain --cov-report=term-missing --cov-fail-under=60
EOF
```

### `CONTRIBUTING.md`

```bash
cat > CONTRIBUTING.md << 'EOF'
# Contributing to Obsidian Brain

## Setup

```bash
git clone https://github.com/harimsd07/obsidian-brain
cd obsidian-brain
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest                        # run all tests
pytest tests/test_chunker.py  # specific file
pytest -v --tb=short          # verbose
```

Tests are fully mocked — no Ollama or API keys needed.

## Adding a new command

1. Create `brain/commands/your_command.py` with a `run_your_command()` function
2. Add `@app.command()` in `brain/cli.py`
3. Wrap with `try/except BrainError`
4. Add tests in `tests/test_your_command.py`

## PR checklist

- [ ] Tests pass
- [ ] No API keys in code
- [ ] `.env` is gitignored
- [ ] Errors are human-readable
EOF
```

### `LICENSE`

```bash
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2024 harimsd07

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
```

---

## Step 4 — Copy test files

For the 4 test files (`test_chunker.py`, `test_utils.py`, `test_retriever.py`, `test_ingest.py`) — copy them directly from the files Claude showed you in the previous message into the `tests/` directory.

Or download the latest zip from Claude and copy just the `tests/` folder.

---

## Step 5 — Replace modified files

### Replace `brain/cli.py`

Copy the full `brain/cli.py` content from the file Claude provided in the previous message.
The key things that changed:
- Added `brain init` command
- Added `--version` / `-V` flag
- Added `_handle_error()` — no raw tracebacks
- All commands now catch `BrainError` and print clean panels

### Replace `pyproject.toml`

```bash
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "obsidian-brain"
version = "0.1.0"
description = "Chat with your Obsidian vault locally using RAG and LLMs"
requires-python = ">=3.11"
readme = "README.md"
license = {text = "MIT"}
keywords = ["obsidian", "rag", "llm", "cli", "notes", "second-brain"]
dependencies = [
    "chromadb>=0.5.0",
    "ollama>=0.2.0",
    "watchdog>=4.0.0",
    "typer[all]>=0.12.0",
    "rich>=13.7.0",
    "python-frontmatter>=1.1.0",
    "tiktoken>=0.7.0",
    "python-dotenv>=1.0.0",
    "groq>=0.9.0",
    "google-generativeai>=0.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.12.0",
    "pytest-cov>=5.0.0",
]

[project.scripts]
brain = "brain.cli:app"

[tool.setuptools.packages.find]
where = ["."]
include = ["brain*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
EOF
```

---

## Step 6 — Update .gitignore

Make sure `.gitignore` has these entries:

```bash
cat > .gitignore << 'EOF'
.venv/
data/
__pycache__/
*.pyc
*.pyo
.env
*.env
*.egg-info/
dist/
build/
.DS_Store
.pytest_cache/
htmlcov/
.coverage
EOF
```

---

## Step 7 — Install dev dependencies and run tests

```bash
source obsidian_brain/bin/activate      # activate your venv
pip install -e ".[dev]"                  # installs pytest, pytest-mock, pytest-cov
pytest                                   # run all tests
```

Expected output:
```
tests/test_chunker.py ........ PASSED
tests/test_utils.py ......... PASSED
tests/test_retriever.py ..... PASSED
tests/test_ingest.py ........ PASSED
```

---

## Step 8 — Verify CLI still works

```bash
brain --version
brain --help
brain stats
```

---

## Step 9 — Push to GitHub

### If this is a brand new repo:

```bash
# Initialize git
git init

# Stage everything
git add .

# Verify nothing sensitive is staged
git status
git grep "AIza"       # should return nothing
git grep "gsk_"       # should return nothing

# First commit
git commit -m "feat: initial release v0.1.0-beta

- Full vault ingestion pipeline with ChromaDB
- Multi-provider LLM (Ollama, Groq, Gemini)
- Interactive chat with thinking phase
- File watcher for incremental re-indexing
- Setup wizard (brain init)
- Human-readable error handling
- Test suite with 30+ tests
- GitHub Actions CI"

# Add remote and push
git remote add origin https://github.com/harimsd07/obsidian-brain.git
git branch -M main
git push -u origin main
```

### If repo already exists with previous commits:

```bash
# Stage all changes
git add .

# Verify status
git status

# Commit Phase A changes
git commit -m "feat: Phase A release blocker fixes

- Add brain init setup wizard (A1)
- Add human-readable error handling via exceptions.py (A2)
- Add --version flag (A3)
- Add full test suite: chunker, utils, retriever, ingest (A4)
- Add GitHub Actions CI workflow (A4)
- Overhaul README for community release (A5)
- Add CONTRIBUTING.md and LICENSE"

# Push
git push origin main
```

---

## Step 10 — Tag the release

```bash
git tag -a v0.1.0-beta -m "v0.1.0-beta — Phase A complete"
git push origin v0.1.0-beta
```

---

## Final project structure after all changes

```
obsidian-brain/
├── .github/
│   └── workflows/
│       └── tests.yml          ← NEW: CI on every PR
├── brain/
│   ├── __init__.py
│   ├── chunker.py
│   ├── cli.py                 ← MODIFIED: init, version, error handling
│   ├── config.py
│   ├── db.py
│   ├── exceptions.py          ← NEW: human-readable errors
│   ├── ingest.py
│   ├── llm.py
│   ├── retriever.py
│   ├── utils.py
│   ├── watcher.py
│   └── commands/
│       ├── __init__.py
│       ├── chat.py
│       └── init.py            ← NEW: setup wizard
├── tests/
│   ├── __init__.py            ← NEW
│   ├── conftest.py            ← NEW
│   ├── test_chunker.py        ← NEW
│   ├── test_ingest.py         ← NEW
│   ├── test_retriever.py      ← NEW
│   └── test_utils.py          ← NEW
├── .gitignore                 ← MODIFIED: added pytest cache
├── CONTRIBUTING.md            ← NEW
├── LICENSE                    ← NEW
├── README.md                  ← MODIFIED: full overhaul
├── pyproject.toml             ← MODIFIED: dev deps, metadata
└── requirements.txt
```
