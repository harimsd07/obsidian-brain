# CLI Commands Reference

Complete reference for all Obsidian Brain CLI commands.

---

## Getting Help

### Show Help
```bash
# Global help
brain --help

# Command-specific help
brain ask --help
brain chat --help
brain serve --help
```

### Show Version
```bash
brain --version
```

---

## Setup & Configuration

### `brain init`

Interactive setup wizard for first-time configuration.

**Usage**:
```bash
brain init
```

**Prompts**:
1. **Vault Path**: Location of your Obsidian vault
   - Default: `~/Obsidian`
   - Example: `/Users/john/Documents/Obsidian`

2. **LLM Provider**: Choose your LLM provider
   - `1` - Ollama (local, privacy-focused)
   - `2` - Groq (cloud, very fast)
   - `3` - Google Gemini (cloud, free)
   - `4` - NVIDIA NIM (enterprise, fastest)

3. **Model**: Provider-specific model
   - Ollama: `llama2`, `mistral`, `neural-chat`
   - Groq: `mixtral-8x7b-32768`
   - Gemini: `gemini-1.5-pro`
   - NVIDIA NIM: `meta/llama-3.1-70b-instruct`

4. **API Key** (if cloud provider)
   - Where to get: See INSTALLATION.md

5. **Embedding Model** (if Ollama)
   - Default: `nomic-embed-text`
   - Options: `mistral-embed`, `neural-embed`

**Output**:
```
✓ Configuration saved to .env
✓ Vault verified at /path/to/vault
✓ LLM provider connection: OK
✓ Setup complete! Run: brain ingest
```

---

### `brain config show`

Display current configuration.

**Usage**:
```bash
brain config show
```

**Output**:
```
Vault Path:           /Users/john/Obsidian
LLM Provider:         groq
LLM Model:            mixtral-8x7b-32768
Hybrid Search:        true
Default Top K:        5
Web UI Host:          127.0.0.1
Web UI Port:          8000
```

---

### `brain config test`

Test current configuration for connectivity and validity.

**Usage**:
```bash
brain config test
```

**Output**:
```
Testing Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Vault path accessible
✓ LLM provider reachable
✓ Embeddings working
✓ Configuration OK
```

---

## Indexing

### `brain ingest`

Index your entire Obsidian vault into the vector database.

**Usage**:
```bash
# Basic ingest
brain ingest

# Show progress
brain ingest --verbose

# Process only new/modified files
brain ingest --incremental

# Force re-index all files
brain ingest --force
```

**Options**:
- `--verbose`, `-v`: Show detailed progress
- `--incremental`: Only process changed files (default: true)
- `--force`, `-f`: Re-index all files ignoring timestamps
- `--batch-size INT`: Documents per batch (default: 32)

**Output**:
```
Indexing vault: /Users/john/Obsidian
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Processing files: ▓▓▓▓▓▓▓▓▓▓ 100% [120/120]
✓ Indexed 120 documents
✓ Created 2,450 chunks
✓ Generated 2,450 embeddings
✓ Indexing complete in 35.2s
```

---

### `brain watch`

Watch vault for changes and automatically re-index modified files.

**Usage**:
```bash
# Start watching
brain watch

# With polling (if file system events don't work)
brain watch --poll

# Check for changes every 30 seconds
brain watch --poll-interval 30
```

**Options**:
- `--poll`: Use polling instead of file system events
- `--poll-interval INT`: Polling interval in seconds (default: 10)

**Output**:
```
Watching vault for changes...
[2024-01-15 10:30:45] Modified: Python.md
  ✓ Re-indexed (5 chunks, 0.8s)
[2024-01-15 10:31:20] New file: React.md
  ✓ Indexed (8 chunks, 1.2s)
```

---

## Searching

### `brain ask`

Ask a question about your vault (single query).

**Usage**:
```bash
# Simple question
brain ask "What is Python?"

# Get more results
brain ask "Python" -k 10

# Semantic search only (no keyword matching)
brain ask "decorators" --semantic-only

# Show raw JSON output
brain ask "Python" --raw

# With thinking (shows reasoning)
brain ask "Best practices" --thinking
```

**Options**:
- `QUESTION`: The question to ask (required)
- `--top-k`, `-k INT`: Number of results (default: 5, max: 1000)
- `--semantic-only`: Disable keyword matching (use only semantic search)
- `--hybrid`: Use hybrid search (default: true)
- `--raw`: Output raw JSON
- `--thinking`: Show LLM reasoning process
- `--no-citations`: Don't include source citations

**Output**:
```
Question: What is Python?

Answer:
Python is a high-level, interpreted programming language created by Guido van Rossum
in 1991. It's known for its simple syntax and readability, making it popular for
beginners and experts alike.

Sources:
• Python.md (line 42)
• Programming/Languages.md (line 15)
• /Snippets/python-basics.md (line 8)
```

---

### `brain search`

Search vault for relevant documents (semantic + keyword).

**Usage**:
```bash
# Basic search
brain search "machine learning"

# Get more results
brain search "ML" -k 20

# Semantic only
brain search "neural networks" --semantic-only

# Show relevance scores
brain search "Python" --scores

# Raw output
brain search "decorators" --raw
```

**Options**:
- `QUERY`: Search query (required)
- `--top-k`, `-k INT`: Number of results (default: 5, max: 1000)
- `--semantic-only`: Use only semantic search
- `--hybrid`: Use hybrid search (default: true)
- `--scores`: Show relevance scores
- `--raw`: Raw JSON output

**Output**:
```
Searching: "machine learning"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ML Basics (Score: 0.94)
   Location: ML/Introduction.md
   Preview: Machine learning is a subset of artificial intelligence...

2. Supervised Learning (Score: 0.89)
   Location: ML/Algorithms.md
   Preview: Supervised learning uses labeled data to train models...

3. Neural Networks (Score: 0.85)
   Location: AI/Deep-Learning.md
   Preview: Neural networks are inspired by biological neurons...
```

---

## Interactive Mode

### `brain chat`

Interactive chat session with your vault.

**Usage**:
```bash
brain chat
```

**Commands Inside Chat**:
```
/search <query>     Search for documents
/ask <question>     Ask a question
/top <n>            Set number of results (default: 5)
/hybrid on|off      Enable/disable hybrid search
/reset              Clear conversation history
/history            Show conversation history
/help               Show available commands
/exit               Exit chat mode
```

**Example Session**:
```
🧠 Obsidian Brain Chat
Type /help for commands

> /search python decorators
Results:
1. Decorators (Score: 0.92)
   Python/advanced-topics.md
2. Function Wrappers (Score: 0.88)
   Python/patterns.md

> /ask how do decorators work?
Answer: Decorators are functions that modify other functions...
Sources: Python/advanced-topics.md, Python/patterns.md

> /top 10
✓ Results per query set to 10

> /exit
👋 Goodbye!
```

---

## Web Interface

### `brain serve`

Start the web UI server for browser-based access.

**Usage**:
```bash
# Default (localhost:8000)
brain serve

# Custom host and port
brain serve --host 0.0.0.0 --port 8080

# Disable auto-reload
brain serve --no-reload

# Show API docs
brain serve --docs
```

**Options**:
- `--host TEXT`: Host to bind to (default: 127.0.0.1)
- `--port INT`: Port to bind to (default: 8000)
- `--reload / --no-reload`: Auto-reload on code changes (default: true)
- `--docs / --no-docs`: Show API documentation (default: true)
- `--workers INT`: Number of worker processes (default: 1)

**Output**:
```
🧠 Obsidian Brain Web UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
INFO:     Press CTRL+C to quit

Access points:
• Web UI:  http://127.0.0.1:8000
• Docs:    http://127.0.0.1:8000/api/docs
• ReDoc:   http://127.0.0.1:8000/api/redoc
```

**Features**:
- **Search Tab**: Hybrid semantic and keyword search
- **Ask Tab**: Ask questions with AI-powered answers
- **Stats Tab**: Vault statistics and metrics
- **API Docs**: Interactive Swagger UI

---

## Telegram Integration

### `brain telegram`

Start Telegram bot for chatting via Telegram.

**Usage**:
```bash
# Start bot
brain telegram

# With verbose output
brain telegram --verbose

# Custom poll interval
brain telegram --poll-interval 2
```

**Options**:
- `--verbose`, `-v`: Show detailed logs
- `--poll-interval INT`: Poll interval in seconds (default: 1)

**Setup**:
1. Create bot via @BotFather on Telegram
2. Copy bot token
3. Add to `.env`: `TELEGRAM_BOT_TOKEN=your_token`
4. Run: `brain telegram`

**Commands**:
- `/ask <question>` - Ask a question
- `/search <query>` - Search vault
- `/stats` - Show vault statistics
- `/help` - Show available commands

---

## Database Management

### `brain db reset`

Clear all indexed documents and reset database.

**Usage**:
```bash
brain db reset

# Force without confirmation
brain db reset --force
```

**⚠️ Warning**: This is irreversible! All indexed documents will be deleted.

**When to Use**:
- Switching LLM providers (especially different embedding dimensions)
- Corrupted database
- Starting fresh

**After Reset**:
```bash
brain ingest  # Re-index your vault
```

---

### `brain db optimize`

Optimize the vector database for better performance.

**Usage**:
```bash
brain db optimize

# Show detailed optimization stats
brain db optimize --verbose
```

**Output**:
```
Optimizing database...
✓ Removed 120 duplicate entries
✓ Rebuilt indexes
✓ Compacted storage
✓ Database size reduced: 45.2MB → 38.5MB
✓ Query time improved: ~5% faster
```

---

### `brain db stats`

Show database statistics and usage.

**Usage**:
```bash
brain db stats
```

**Output**:
```
Database Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Documents:      350
Total Chunks:         7,250
Vector Dimension:     768
Database Size:        42.5 MB
Indexed Collections:  1
Last Updated:         2024-01-15 14:32:10
```

---

## Vault Statistics

### `brain stats`

Show detailed statistics about your vault.

**Usage**:
```bash
# Basic stats
brain stats

# Detailed breakdown
brain stats --detailed

# Show as JSON
brain stats --json
```

**Options**:
- `--detailed`, `-d`: Show file-by-file breakdown
- `--json`: Output as JSON
- `--format TEXT`: Output format (table, json, csv)

**Output**:
```
Vault Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Files:          350
Total Words:          145,230
Total Size:           12.4 MB

By Category:
  Programming:        85 files (210,120 words)
  Databases:          45 files (95,230 words)
  DevOps:             32 files (78,120 words)
  Other:              188 files (65,760 words)

Most Recent Update:   2024-01-15 14:30:00
```

---

## Maintenance & Cleanup

### `brain cleanup`

Remove orphaned and invalid entries from database.

**Usage**:
```bash
brain cleanup

# Dry run (show what would be deleted)
brain cleanup --dry-run

# Verbose output
brain cleanup --verbose
```

**Options**:
- `--dry-run`: Show what would be removed without removing
- `--verbose`, `-v`: Show detailed output

---

### `brain sync`

Synchronize vault with latest changes from file system.

**Usage**:
```bash
# Sync (checks for new/modified files)
brain sync

# Force full re-sync
brain sync --force

# Show changes
brain sync --verbose
```

---

## Development Commands

### `brain test`

Run test suite.

**Usage**:
```bash
# Run all tests
brain test

# Run specific test file
brain test tests/test_retriever.py

# Show coverage
brain test --cov

# Verbose output
brain test -v
```

---

### `brain lint`

Check code for style issues.

**Usage**:
```bash
brain lint

# Fix issues automatically
brain lint --fix
```

---

## Tips & Tricks

### Search Tips

```bash
# Use quotes for exact phrases
brain ask "machine learning models"

# Combine multiple concepts
brain ask "Python async programming patterns"

# Use specific terms
brain ask "decorator implementation" --top-k 10

# Hybrid search (default)
brain ask "Python"  # Uses semantic + keyword

# Pure semantic search (for concepts)
brain ask "How to structure projects?" --semantic-only
```

### Performance Tips

```bash
# Incremental indexing (default, faster)
brain ingest

# Process specific directory
brain ingest --path ~/Obsidian/Python

# Batch size optimization
brain ingest --batch-size 64  # For large vaults
```

### Troubleshooting Commands

```bash
# Check configuration
brain config show

# Test connectivity
brain config test

# View database stats
brain db stats

# Verify vault
brain stats

# Check recent logs
brain logs --tail 50
```

---

## Command Shortcuts

Common workflows as aliases:

```bash
# Add to .bashrc or .zshrc

# Quick search
alias bsearch='brain search'
alias bask='brain ask'

# Quick indexing
alias bingest='brain ingest'
alias bwatch='brain watch'

# Web UI
alias bweb='brain serve'
alias bchat='brain chat'

# Admin
alias bstats='brain stats'
alias bconfig='brain config show'
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Usage error (invalid options) |
| 3 | Configuration error |
| 4 | Vault not found |
| 5 | LLM provider error |
| 6 | Database error |
| 7 | Rate limit exceeded |

---

## Environment Variable Overrides

All options can be set via environment variables:

```bash
# Override without flags
export BRAIN_TOP_K=10
brain ask "Python"

# One-time override
BRAIN_LLM_PROVIDER=groq brain ask "Python"

# Web server
BRAIN_WEB_HOST=0.0.0.0 BRAIN_WEB_PORT=8080 brain serve
```

---

## See Also

- [INSTALLATION.md](./INSTALLATION.md) - Setup guide
- [WORKFLOW.md](./WORKFLOW.md) - Usage examples
- [API.md](./API.md) - REST API reference
