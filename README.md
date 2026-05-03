# 🧠 Obsidian Brain

> Chat with your Obsidian vault locally. Ask questions, get answers with source citations — powered by local LLMs or cloud providers.

No cloud lock-in. No subscriptions. Your notes stay yours.

---

## What it does

You type a question in your terminal. It searches your 1000s of notes semantically, feeds the most relevant chunks to an LLM, and streams back an answer — with exact note paths cited.

```
you › what are my ideas about RAG systems?

━━━━━━━━━━━━━━━━ thinking ━━━━━━━━━━━━━━━━
╭──────────────────────────────────────────╮
│ The user wants ideas about RAG systems.  │
│ I see relevant notes in Ideas.md and     │
│ Projects/BankPrep.md...                  │
╰──────────────────────────────────────────╯

━━━━━━━━━━━━━━━━ answer ━━━━━━━━━━━━━━━━

Based on your notes, here are your RAG ideas:

- **Local RAG for Obsidian** [Ideas.md] — build a CLI tool that
  indexes your vault into ChromaDB and queries it via LLM
- **BankPrep AI Question Lab** [Projects/BankPrep.md] — use RAG
  to generate exam questions from study material

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sources: Ideas  Projects/BankPrep.md
```

---

## Features

- 💬 **Interactive chat** with thinking phase — see the LLM reason before answering
- 🔍 **Semantic search** across your entire vault via ChromaDB
- 📁 **Auto-ingestion** — full vault index in one command
- 👁️ **File watcher** — incremental re-index on every save
- 🔀 **Multi-provider** — Ollama (local), Groq, or Gemini
- 🏷️ **Frontmatter aware** — understands tags, aliases, wikilinks
- 📝 **Source citations** — every answer shows which notes it came from
- ⚡ **Thinking phase** — toggle on/off with `/thinking`

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
pip install obsidian-brain
```

Or from source:

```bash
git clone https://github.com/harimsd07/obsidian-brain
cd obsidian-brain
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
```

### 3. Run setup wizard

```bash
brain init
```

Detects your vault, picks a provider, saves your API keys to `.env`.

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

| Command | Description |
|---|---|
| `brain init` | First-time setup wizard |
| `brain ingest` | Index your vault (run once, re-run after bulk changes) |
| `brain ingest --force` | Re-index everything |
| `brain watch` | File watcher — auto re-index on save |
| `brain chat` | Interactive Q&A with your notes |
| `brain stats` | Index stats + provider health check |
| `brain --version` | Show version |

### Chat commands

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

| Provider | Speed | Cost | Needs internet | Setup |
|---|---|---|---|---|
| Ollama (local) | Medium | Free | No | `ollama serve` |
| Groq | Fast | Free tier | Yes | API key |
| Gemini | Fast | Free tier | Yes | API key |

Switch providers anytime:

```bash
export BRAIN_LLM_PROVIDER=groq     # or gemini, ollama
brain chat
```

---

## Configuration

All config via `.env` in project root (created by `brain init`):

```bash
BRAIN_VAULT_PATH=~/Documents/Obsidian/MyVault
BRAIN_LLM_PROVIDER=ollama          # ollama | groq | gemini

GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
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
brain/
├── config.py           # all configuration
├── utils.py            # markdown parser, frontmatter, wikilinks
├── chunker.py          # heading + token-based chunking
├── db.py               # ChromaDB wrapper
├── llm.py              # Ollama / Groq / Gemini provider routing
├── ingest.py           # vault ingestion pipeline
├── watcher.py          # file watcher daemon
├── retriever.py        # semantic search
├── exceptions.py       # human-readable errors
└── commands/
    ├── chat.py         # interactive Q&A REPL
    └── init.py         # setup wizard
```

---

## Roadmap

- [x] Full vault ingestion with progress bar
- [x] Semantic search via ChromaDB
- [x] Multi-provider LLM (Ollama / Groq / Gemini)
- [x] Interactive chat with thinking phase
- [x] File watcher for incremental re-indexing
- [x] Setup wizard (`brain init`)
- [ ] `brain summarize` — summarize a note or folder
- [ ] `brain related` — find semantically related notes
- [ ] `brain tag` — auto-tag untagged notes
- [ ] `brain digest` — daily digest of recent notes
- [ ] Persistent chat history
- [ ] Hybrid search (semantic + BM25 keyword)
- [ ] MCP server mode — use your vault in Claude Desktop / Cursor
- [ ] `brain serve` — web UI mode

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
