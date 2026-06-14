# 🧠 Obsidian Brain

Transform your Obsidian vault into an intelligent knowledge base with semantic search, AI-powered answers, and multi-provider LLM support.

**Chat with your notes using RAG (Retrieval-Augmented Generation) powered by local or cloud LLMs.**

---

## ✨ Features

### Core Capabilities
- **Hybrid Search**: Combines semantic similarity (70%) + keyword matching (30%) for best results
- **Semantic Search**: Vector-based search using embeddings (768-4096 dimensions)
- **Keyword Search**: BM25 algorithm for exact phrase matching
- **AI Q&A**: Ask questions about your vault and get AI-powered answers with citations
- **Citation Support**: All answers include source notes

### LLM Providers (4 Supported)
| Provider | Model | Embedding Dim | Cost | Speed | Setup |
|----------|-------|---------------|------|-------|-------|
| **Ollama** | Any local model | Varies | Free | Fast (local) | Easy |
| **Groq** | Mixtral 8x7B | 768 | Free tier | Very Fast | API key |
| **Google Gemini** | Gemini 1.5 Pro | 768 | Free tier | Fast | API key |
| **NVIDIA NIM** | Llama 3.1 70B | 4096 | Enterprise | Very Fast | API key |

### Interfaces
- **CLI**: Command-line interface with rich formatting
- **Web UI**: Modern web interface at http://localhost:8000
- **REST API**: OpenAPI-documented endpoints with Swagger UI
- **MCP Server**: Integration with Claude Desktop and Cursor IDE
- **Telegram Bot**: Chat with your vault via Telegram

### Production Features
- **Rate Limiting**: 100 searches/hr, 50 questions/hr, 1000 stats/hr
- **Query Caching**: 1-hour TTL, 1000-item cache
- **Request Metrics**: Uptime, request counts, cache statistics
- **Logging**: Structured logging for monitoring and debugging
- **Error Handling**: Comprehensive input validation and error messages

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- Your Obsidian vault

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/obsidian-brain.git
cd obsidian-brain

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Initialize
```bash
# First time setup - choose your LLM provider
brain init

# Follow the wizard to select:
# 1. Vault path (default: ~/Obsidian)
# 2. LLM provider (Ollama, Groq, Gemini, NVIDIA NIM)
# 3. API keys (if needed)
```

### 3. Index Your Vault
```bash
# Ingest all notes into the vector database
brain ingest

# Or watch for changes and auto-index
brain watch
```

### 4. Start Using
```bash
# Quick question
brain ask "What's in my Python notes?"

# Interactive chat mode
brain chat

# Web UI
brain serve

# Telegram bot
brain telegram
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [INSTALLATION.md](./INSTALLATION.md) | Detailed setup and configuration guide |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design and component overview |
| [COMMANDS.md](./COMMANDS.md) | CLI commands reference |
| [WORKFLOW.md](./WORKFLOW.md) | Usage examples and workflows |
| [API.md](./API.md) | REST API reference |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Development setup and contribution guide |

---

## 🎯 Usage Examples

### Search Your Vault
```bash
# Hybrid search (semantic + keyword)
brain ask "How do I use Python decorators?"

# Get multiple results
brain ask -k 10 "Git workflow best practices"

# Raw output for piping
brain ask --raw "My favorite tools"
```

### Interactive Chat
```bash
# Start chat mode
brain chat

# Inside chat mode:
/search python decorators
/ask How do I use them?
/top 10    # Set number of results
/help      # Show commands
```

### Web UI
```bash
# Start web server
brain serve --host 0.0.0.0 --port 8000

# Open browser to http://localhost:8000
# - Search tab: Semantic search
# - Ask tab: AI-powered questions
# - Stats tab: Vault statistics
```

### API Usage
```bash
# Search via API
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python decorators",
    "top_k": 5,
    "hybrid": true
  }'

# Ask via API
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do decorators work?",
    "top_k": 5,
    "thinking": true
  }'
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Required
BRAIN_VAULT_PATH=/path/to/obsidian/vault

# LLM Provider (defaults: ollama)
BRAIN_LLM_PROVIDER=groq              # ollama, groq, google, nvidia-nim
BRAIN_LLM_MODEL=mixtral-8x7b-32768  # Provider-specific model

# API Keys (if using cloud providers)
GROQ_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
NVIDIA_NIM_API_KEY=your_key_here

# Search Settings
BRAIN_HYBRID_SEARCH=true
BRAIN_TOP_K=5

# Web UI
BRAIN_WEB_HOST=127.0.0.1
BRAIN_WEB_PORT=8000
```

See [INSTALLATION.md](./INSTALLATION.md) for detailed configuration.

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI / Web UI / API                    │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
        ┌───────▼─────────┐          ┌────────▼────────┐
        │  brain.commands │          │  brain.web_ui   │
        │  (ask, chat)    │          │  (REST API)     │
        └───────┬─────────┘          └────────┬────────┘
                │                              │
        ┌───────▼──────────────────────────────▼─────────┐
        │          brain.retriever (Retrieval)           │
        │  - Semantic search (embeddings)                │
        │  - Keyword search (BM25)                       │
        │  - Hybrid results merging                      │
        └───────┬──────────────────────────────┬─────────┘
                │                              │
        ┌───────▼──────────────┐    ┌─────────▼────────┐
        │    brain.llm         │    │   brain.db       │
        │  - Generate answers  │    │  (ChromaDB)      │
        │  - Route providers   │    │  - Vector store  │
        └──────────────────────┘    │  - Metadata      │
                │                   └──────────────────┘
        ┌───────▼────────────────────────┐
        │   LLM Providers & Embeddings   │
        │ - Ollama (local)               │
        │ - Groq (cloud)                 │
        │ - Google Gemini (cloud)        │
        │ - NVIDIA NIM (enterprise)      │
        └────────────────────────────────┘
```

For detailed architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## 🛠️ Troubleshooting

### Issue: "Vault not indexed"
```bash
# Run ingest to index all notes
brain ingest
```

### Issue: Slow search queries
```bash
# Check your provider:
# - Ollama running locally? (brain init)
# - API keys valid? (check .env file)
# - Network latency? (switch to faster provider)
```

### Issue: Rate limit errors (429)
```bash
# Wait 1 hour or:
# - Reduce request frequency
# - Use caching (automatic)
# - Upgrade LLM provider
```

### Issue: Embedding dimension mismatch
```bash
# When switching providers:
rm -rf data/chroma/
brain ingest  # Re-index with new provider
```

---

## 📈 Performance

| Operation | Time | Provider |
|-----------|------|----------|
| Search | 1.5s | NVIDIA NIM |
| Q&A | 2-5s | Groq/Gemini |
| Cache hit | <1ms | Local |
| Index (1000 notes) | ~30s | Local |

---

## 🤝 Contributing

See [DEVELOPMENT.md](./DEVELOPMENT.md) for:
- Setting up development environment
- Running tests (149 test suite)
- Making code contributions
- Creating pull requests

---

## 📋 Project Status

- ✅ Core retrieval working (hybrid search)
- ✅ All 4 LLM providers integrated
- ✅ Web UI with rate limiting and caching
- ✅ REST API with OpenAPI documentation
- ✅ CLI commands complete
- ✅ Telegram bot integration
- ✅ MCP server for Claude Desktop
- ✅ 149 tests passing
- ✅ Production-ready features (rate limiting, caching, logging)

---

## 📝 License

MIT License - see LICENSE file

---

## 🙏 Acknowledgments

Built with:
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [LangChain](https://www.langchain.com/) - LLM orchestration
- [Ollama](https://ollama.ai/) - Local LLM support

---

## 📞 Support

- **Issues**: Report bugs on GitHub
- **Discussions**: Ask questions in GitHub Discussions
- **Docs**: Check documentation files
- **Examples**: See WORKFLOW.md

---

**Made with ❤️ for knowledge workers**
