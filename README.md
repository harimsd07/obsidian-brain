# 🧠 Obsidian Brain

> Chat with your Obsidian vault locally. Ask questions, get answers with source citations — powered by local LLMs or free-tier cloud providers.

No cloud lock-in. No subscriptions. Your notes stay yours.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-80%2B-brightgreen)
![Providers](https://img.shields.io/badge/Providers-Ollama%20%7C%20Groq%20%7C%20Gemini-purple)

---

## What it does

You type a question in your terminal. It searches your notes semantically, feeds the most relevant chunks to an LLM, and streams back an answer — with exact note paths cited.

```
you › what are my ideas about multi-agent AI systems?

━━━━━━━━━━━━━━━━ thinking ━━━━━━━━━━━━━━━━
╭──────────────────────────────────────────╮
│ The user wants ideas about multi-agent   │
│ systems. I see relevant notes in         │
│ Projects/AI-Agents.md and               │
│ ObsidianForArch/AI/Agents/...           │
╰──────────────────────────────────────────╯

━━━━━━━━━━━━━━━━ answer ━━━━━━━━━━━━━━━━

Based on your notes, here are your key ideas:

- **Supervisor + worker pattern** [Projects/AI-Agents.md] — a
  supervisor agent delegates tasks to specialized sub-agents
- **CrewAI for prototyping** [AI Agent System — Tech Stack] —
  best for enterprise multi-agent prototyping
- **LangGraph for production** — better for large-scale stateful systems

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sources: AI-Agents.md  AI Agent System — Tech Stack Decisions.md
```

---

## Features

- 💬 **`brain chat`** — interactive Q&A with live thinking phase
- 📄 **`brain summarize`** — summarize any note or folder
- 🔗 **`brain related`** — find semantically similar notes
- 🏷️ **`brain tag`** — auto-tag untagged notes via LLM
- 📰 **`brain digest`** — daily/weekly digest of recent notes
- 📋 **`brain list-notes`** — browse your indexed vault
- 👁️ **`brain watch`** — file watcher, auto re-index on save
- 🔀 **Multi-provider** — Ollama (local), Groq, Gemini
- ⚡ **Thinking phase** — see the LLM reason before answering
- 🏷️ **Frontmatter aware** — understands tags, aliases, wikilinks
- 📍 **Source citations** — every answer shows which notes it came from
- 🧪 **80+ tests** — pytest suite with GitHub Actions CI

---

## Quick Start

### 1. Install Ollama and pull models

```bash
# Install: https://ollama.com
ollama pull nomic-embed-text
ollama pull llama3
```

### 2. Install obsidian-brain

```bash
# From source
git clone https://github.com/harimsd07/obsidian-brain
cd obsidian-brain
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
```

### 3. Run setup wizard

```bash
brain init
```

Auto-detects your vault, lets you pick a provider, saves API keys to `.env`.

### 4. Index your vault

```bash
brain ingest
```

### 5. Start chatting

```bash
brain chat
```

---

## Commands

### Core

| Command | Description |
|---|---|
| `brain init` | First-time setup wizard |
| `brain ingest` | Index full vault (run once, re-run after bulk changes) |
| `brain ingest --force` | Re-index everything |
| `brain watch` | File watcher — auto re-index on every save |
| `brain stats` | Index stats + provider health check |
| `brain --version` | Show version |

### Explore

| Command | Description |
|---|---|
| `brain chat` | Interactive Q&A with your notes |
| `brain summarize --note "Projects/BankPrep"` | Summarize a single note |
| `brain summarize --folder "Projects/"` | Summarize a folder |
| `brain summarize --folder "Daily/" --since 7d` | Folder filtered by recency |
| `brain related "arch-setup"` | Find semantically related notes |
| `brain related "arch-setup" --top 10` | More results |
| `brain tag` | Preview auto-suggested tags (dry-run) |
| `brain tag --apply` | Write tags to frontmatter |
| `brain tag --note "VIm text editor" --apply` | Tag a specific note |
| `brain digest` | Digest of notes from last 24h |
| `brain digest --since 7d` | Weekly digest |
| `brain digest --since 7d --save` | Save digest as new note in vault |
| `brain list-notes` | List all indexed notes |
| `brain list-notes --folder "Linux"` | Filter by folder |
| `brain list-notes --search "agent"` | Search by note name |

### Chat commands (inside `brain chat`)

| Command | Action |
|---|---|
| `/thinking` | Toggle thinking phase on/off |
| `/sources` | Show all sources from last answer |
| `/top N` | Change retrieval depth (default: 5) |
| `/clear` | Clear conversation history |
| `/model` | Show active provider and models |
| `/help` | Show all commands |
| `/exit` | Quit |

---

## Provider comparison

| Provider | Speed | Cost | Internet | Setup |
|---|---|---|---|---|
| Ollama (local) | Medium | Free forever | ❌ No | `ollama serve` |
| Groq | ⚡ Fastest | Free tier | ✅ Yes | API key |
| Gemini | Fast | Free tier | ✅ Yes | API key |

Switch providers anytime:

```bash
export BRAIN_LLM_PROVIDER=groq     # or gemini, ollama
brain chat
```

> **Note:** Embedding always uses `nomic-embed-text` via Ollama locally.
> If Ollama is not running, embedding falls back to Gemini (`text-embedding-004`)
> or `sentence-transformers` if installed.

---

## Configuration

All config via `.env` in project root (created by `brain init`):

```bash
BRAIN_VAULT_PATH=~/Documents/Obsidian/MyVault
BRAIN_LLM_PROVIDER=ollama          # ollama | groq | gemini

GROQ_API_KEY=your_key_here         # https://console.groq.com/keys
GEMINI_API_KEY=your_key_here       # https://aistudio.google.com/app/apikey
```

Advanced config in `brain/config.py`:

```python
CHUNK_SIZE = 512        # tokens per chunk
CHUNK_OVERLAP = 64      # overlap between chunks
TOP_K = 5               # chunks retrieved per query
```

---

## Project structure

```
obsidian-brain/
├── brain/
│   ├── config.py           # all configuration
│   ├── utils.py            # markdown parser, frontmatter, wikilinks
│   ├── chunker.py          # heading + token-based chunking
│   ├── db.py               # ChromaDB wrapper
│   ├── llm.py              # Ollama / Groq / Gemini provider routing
│   ├── ingest.py           # vault ingestion pipeline
│   ├── watcher.py          # file watcher daemon
│   ├── retriever.py        # semantic search
│   ├── exceptions.py       # human-readable errors
│   └── commands/
│       ├── init.py         # setup wizard
│       ├── chat.py         # interactive Q&A REPL
│       ├── summarize.py    # note + folder summarization
│       ├── related.py      # semantic similarity search
│       ├── tag.py          # auto-tagging
│       └── digest.py       # daily/weekly digest
├── tests/                  # 80+ pytest tests (fully mocked)
├── .github/workflows/      # GitHub Actions CI
├── CONTRIBUTING.md
├── LICENSE
└── pyproject.toml
```

---

## Tips

**Large folders hit token limits on free-tier Groq?**
Target subfolders instead of the whole tree:
```bash
brain summarize --folder "ObsidianForArch/AI/Agents" --limit 10
```
Or switch to Ollama which has no rate limits:
```bash
export BRAIN_LLM_PROVIDER=ollama
brain summarize --folder "ObsidianForArch/"
```

**Note not found?**
Use `brain list-notes --search "keyword"` to find the exact path,
then pass it to `brain related` or `brain summarize`.

**After using `brain tag --apply`:**
Run `brain ingest` to re-index the updated frontmatter into ChromaDB.

**After `brain digest --save`:**
Run `brain ingest` to index the new digest note into the vault.

---

## Roadmap

- [x] Full vault ingestion with progress bar
- [x] Semantic search via ChromaDB
- [x] Multi-provider LLM (Ollama / Groq / Gemini)
- [x] Interactive chat with thinking phase
- [x] File watcher for incremental re-indexing
- [x] Setup wizard (`brain init`)
- [x] `brain summarize` — summarize a note or folder
- [x] `brain related` — find semantically related notes
- [x] `brain tag` — auto-tag untagged notes
- [x] `brain digest` — daily digest of recent notes
- [x] `brain list-notes` — browse vault structure
- [x] Human-readable error handling
- [x] 80+ tests + GitHub Actions CI
- [ ] Persistent chat history
- [ ] `brain ask` — one-shot Q&A without REPL
- [ ] Hybrid search (semantic + BM25 keyword)
- [ ] MCP server mode — use your vault in Claude Desktop / Cursor
- [ ] `brain serve` — web UI mode
- [ ] Telegram bot mode

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

```bash
# Run tests
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE)

---

*Built with Python · ChromaDB · Ollama · Typer · Rich*

*Made by [@harimsd07](https://github.com/harimsd07)*
