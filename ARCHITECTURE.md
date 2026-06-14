# Architecture Documentation

## System Overview

Obsidian Brain is a modular RAG (Retrieval-Augmented Generation) system that transforms your Obsidian vault into an intelligent knowledge base.

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interfaces                             │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │   CLI    │  │  Web UI    │  │   API    │  │ Telegram    │  │
│  │  (Typer) │  │ (FastAPI)  │  │(OpenAPI) │  │   Bot       │  │
│  └────┬─────┘  └─────┬──────┘  └────┬─────┘  └──────┬──────┘  │
└───────┼──────────────┼───────────────┼────────────────┼────────┘
        │              │               │                │
        └──────────────┼───────────────┼────────────────┘
                       │               │
        ┌──────────────▼───────────────▼──────────────┐
        │      Application Logic Layer                │
        │  ┌─────────────┐  ┌──────────────────────┐ │
        │  │  commands/  │  │  middleware/         │ │
        │  │  - ask      │  │  - rate_limiter      │ │
        │  │  - chat     │  │  - query_cache       │ │
        │  │  - search   │  │  - request_metrics   │ │
        │  └────┬────────┘  └──────────┬───────────┘ │
        └───────┼─────────────────────┼──────────────┘
                │                     │
        ┌───────▼─────────────────────▼──────────────┐
        │      Core Retrieval System                 │
        │  ┌──────────────────────────────────────┐  │
        │  │  retriever.py                        │  │
        │  │  - retrieve(query, n, hybrid)        │  │
        │  │  - Semantic search (embeddings)      │  │
        │  │  - Keyword search (BM25)             │  │
        │  │  - Result merging (70/30 weight)     │  │
        │  └──────────────────────────────────────┘  │
        └───────┬──────────────────────┬─────────────┘
                │                      │
    ┌───────────▼────┐      ┌──────────▼────────┐
    │  Data Access   │      │  LLM Integration  │
    │  Layer         │      │  Layer            │
    │                │      │                   │
    │ ┌────────────┐ │      │ ┌──────────────┐ │
    │ │ db.py      │ │      │ │ llm.py       │ │
    │ │ - ChromaDB │ │      │ │ - Provider   │ │
    │ │ - Metadata │ │      │ │   routing    │ │
    │ │ - Search   │ │      │ │ - Generate   │ │
    │ │ - Index    │ │      │ │ - Embed      │ │
    │ └────────────┘ │      │ └──────────────┘ │
    └───────┬────────┘      └──────────┬───────┘
            │                          │
            │       ┌─────────────────┐│
            │       │    config.py    ││
            │       │ - Settings      ││
            │       │ - Defaults      ││
            │       │ - Paths         ││
            │       └─────────────────┘│
            │                          │
    ┌───────▼──────────────────────────▼──────────────┐
    │      External Services & Storage                │
    │  ┌──────────────────────────────────────────┐   │
    │  │ LLM Providers:                           │   │
    │  │ • Ollama (local)                         │   │
    │  │ • Groq API (cloud)                       │   │
    │  │ • Google Gemini (cloud)                  │   │
    │  │ • NVIDIA NIM (enterprise)                │   │
    │  └──────────────────────────────────────────┘   │
    │  ┌──────────────────────────────────────────┐   │
    │  │ Storage:                                 │   │
    │  │ • ChromaDB Vector Database               │   │
    │  │ • Local Vault (Markdown files)           │   │
    │  │ • Cache Storage (Memory)                 │   │
    │  └──────────────────────────────────────────┘   │
    └────────────────────────────────────────────────┘
```

---

## Core Components

### 1. **Configuration Layer** (`brain/config.py`)

**Purpose**: Centralized configuration management

**Key Classes**:
```python
class LLMConfig(BaseModel):
    provider: Literal["ollama", "groq", "google", "nvidia-nim"]
    model: str
    base_url: Optional[str]  # For local providers
    api_key: Optional[str]    # For cloud providers

class Config:
    vault_path: Path
    llm_config: LLMConfig
    embedding_dimension: int
    chunk_size: int
    hybrid_search: bool
```

**Features**:
- Loads from environment variables and `.env` file
- Type-safe configuration with Pydantic
- Support for multiple LLM providers
- Graceful defaults

---

### 2. **Database Layer** (`brain/db.py`)

**Purpose**: Vector store and metadata management

**Key Functions**:
```python
def get_db() -> Chroma
    # Returns ChromaDB instance

def add_documents(texts: List[str], metadatas: List[dict])
    # Index documents with metadata

def search(query: str, n: int = 5) -> List[SearchResult]
    # Semantic search using embeddings

def delete_collection()
    # Clear all indexed documents
```

**Features**:
- ChromaDB as vector database
- Metadata persistence (source file, creation date, etc.)
- Efficient similarity search
- Collection management

---

### 3. **LLM Integration Layer** (`brain/llm.py`)

**Purpose**: Unified interface to multiple LLM providers

**Architecture**:
```
Provider Selection
       ↓
   [ollama/groq/google/nvidia-nim]
       ↓
LLMProvider (abstract base)
       ↓
Text Generation + Embeddings
```

**Supported Providers**:

| Provider | Text Gen | Embeddings | Latency | Cost |
|----------|----------|-----------|---------|------|
| Ollama | ✓ | ✓ | ~200ms | Free |
| Groq | ✓ | (via Gemini) | ~500ms | Free tier |
| Gemini | ✓ | ✓ | ~800ms | Free tier |
| NVIDIA NIM | ✓ | ✓ | ~300ms | Enterprise |

**Key Functions**:
```python
def generate_answer(prompt: str, model: str) -> str
    # Generate LLM response

def embed_text(text: str) -> List[float]
    # Convert text to embeddings
```

---

### 4. **Retrieval System** (`brain/retriever.py`)

**Purpose**: Unified search interface with hybrid capabilities

**Key Algorithm**:
```python
def retrieve(query: str, n: int = 5, hybrid: bool = True) -> List[RetrievedChunk]:
    if not query or query.isspace():
        return []
    
    if hybrid:
        # Get semantic results (70% weight)
        semantic = semantic_search(query, n)
        
        # Get keyword results (30% weight)
        keyword = keyword_search(query, n)
        
        # Merge with weighted scoring
        return merge_results(semantic, keyword, weight_semantic=0.7)
    else:
        # Pure semantic search
        return semantic_search(query, n)
```

**Hybrid Search Details**:
- **Semantic**: Uses embeddings for conceptual similarity
- **Keyword**: Uses BM25 for exact phrase matching
- **Merging**: Normalized scores with 70/30 weighting
- **Deduplication**: Removes duplicate results

**Input Validation**:
- Empty/whitespace queries → empty list
- `n <= 0` → defaults to TOP_K (5)
- `n > 1000` → capped at 1000
- `None` queries → empty list

---

### 5. **Command Layer** (`brain/commands/`)

**Purpose**: CLI entry points for user interactions

**Available Commands**:

| Command | File | Purpose |
|---------|------|---------|
| `brain init` | `init.py` | Setup wizard |
| `brain ingest` | `ingest.py` | Index vault |
| `brain ask` | `ask.py` | Single question |
| `brain chat` | `chat.py` | Interactive session |
| `brain search` | `search.py` | Text search |
| `brain serve` | N/A | Start web UI |
| `brain telegram` | N/A | Start bot |
| `brain watch` | `watch.py` | Auto-index |

**Command Pattern**:
```python
@app.command()
def ask(
    question: str = typer.Argument(...),
    top_k: int = typer.Option(5),
    hybrid: bool = typer.Option(True),
    raw: bool = typer.Option(False)
):
    """Ask a question about your vault"""
    # 1. Call retrieve(question, n=top_k, hybrid=hybrid)
    # 2. Generate answer using LLM
    # 3. Format and display results
```

---

### 6. **Web UI Layer** (`brain/web_ui.py`)

**Purpose**: REST API and web interface

**Architecture**:
```
FastAPI Application
    ├── /api/search (POST)
    │   ├── Input: SearchRequest (query, top_k, hybrid)
    │   ├── Process: retrieve() + format
    │   └── Output: SearchResponse (results, metadata)
    │
    ├── /api/ask (POST)
    │   ├── Input: AskRequest (question, top_k, thinking)
    │   ├── Process: retrieve() + LLM generation
    │   └── Output: AskResponse (answer, sources, thinking)
    │
    ├── /api/stats (GET)
    │   ├── Process: Get vault metrics
    │   └── Output: StatsResponse (uptime, counts, cache)
    │
    ├── /api/docs (GET)
    │   └── Swagger UI (interactive API docs)
    │
    ├── /api/redoc (GET)
    │   └── ReDoc (reference documentation)
    │
    └── / (GET)
        └── Frontend (HTML/CSS/JS)
```

**Middleware Stack**:
1. **Rate Limiting**: Token bucket algorithm per IP per endpoint
2. **Caching**: TTL-based query cache (1 hour)
3. **Metrics**: Request counting and statistics
4. **Logging**: Structured logging for all operations

---

### 7. **Middleware Components** (`brain/middleware.py`)

**RateLimiter**:
```python
class RateLimiter:
    # Token bucket algorithm
    # Per IP, per endpoint limits
    # 100/hr search, 50/hr ask, 1000/hr stats
    
    def check_rate_limit(ip: str, endpoint: str) -> bool
        # Returns True if within limit, False if exceeded
```

**QueryCache**:
```python
class QueryCache:
    # TTL: 1 hour
    # Max items: 1000
    # Key: MD5(endpoint:query:n:hybrid)
    
    def get(key: str) -> Optional[CachedResult]
    def set(key: str, value: Any) -> None
```

**RequestMetrics**:
```python
class RequestMetrics:
    # Tracks: uptime, request counts, cache stats
    
    def record_request(endpoint: str) -> None
    def get_metrics() -> MetricsResponse
```

---

### 8. **Integration Layer** (`brain/mcp_server.py`, `brain/telegram_bot.py`)

**MCP Server** (Claude Desktop/Cursor):
- Tool: `search_vault` - Semantic search
- Tool: `ask_vault` - AI-powered Q&A
- Tool: `get_vault_stats` - Vault statistics

**Telegram Bot**:
- Command: `/ask` - Single question
- Command: `/search` - Text search
- Command: `/stats` - Vault statistics
- Features: Message splitting (Telegram 4096 char limit)

---

## Data Flow Diagrams

### Search Flow
```
User Input (Web/CLI/API)
    ↓
Validation (length, format)
    ↓
Rate Limit Check
    ↓
Cache Lookup (MD5 key)
    ↓ (cache miss)
retrieve(query, n=top_k, hybrid=hybrid)
    ├─ Semantic Search
    │  └─ Embed query → Find similar in DB
    │
    ├─ Keyword Search
    │  └─ BM25 on indexed documents
    │
    └─ Merge Results
       ├─ Normalize scores
       ├─ Apply weights (0.7 semantic, 0.3 keyword)
       └─ Remove duplicates
    ↓
Format Results (with metadata)
    ↓
Cache Store (1 hour TTL)
    ↓
Return to User
```

### Q&A Flow
```
User Question (Web/CLI/API)
    ↓
Validation
    ↓
Rate Limit Check
    ↓
Cache Lookup
    ↓ (cache miss)
retrieve(question, n=top_k)
    ↓
Extract relevant context
    ↓
Build prompt with context
    ↓
LLM Generation (provider routing)
    ├─ Ollama (local)
    ├─ Groq (cloud)
    ├─ Gemini (cloud)
    └─ NVIDIA NIM (enterprise)
    ↓
Parse answer + extract citations
    ↓
Format response
    ↓
Cache Store (1 hour TTL)
    ↓
Return to User
```

### Indexing Flow
```
Vault Path
    ↓
Scan for .md files (recursive)
    ↓
For each file:
    ├─ Read content
    ├─ Split into chunks (default: 512 chars)
    ├─ Create metadata (file, date, line)
    ├─ Generate embeddings (provider-specific)
    └─ Store in ChromaDB
    ↓
Update collection metadata
    ↓
Log results (success/errors)
    ↓
Complete
```

---

## Key Design Decisions

### 1. Hybrid Search (70/30 Split)
**Rationale**: 
- Semantic search alone misses exact phrase matches
- Keyword search alone misses conceptual relevance
- 70/30 weighting balances both approaches
- User can disable with `--semantic-only` flag

### 2. Multi-Provider Support
**Rationale**:
- Ollama for offline/privacy-focused users
- Groq/Gemini for free cloud option
- NVIDIA NIM for enterprise deployments
- Easy switching without code changes

### 3. Token Bucket Rate Limiting
**Rationale**:
- Protects server from abuse
- Per-IP tracking prevents single client from monopolizing
- Different limits per endpoint (search high, ask medium, stats very high)
- 1-hour window allows recovery

### 4. TTL-Based Query Cache
**Rationale**:
- Knowledge bases change slowly
- 1-hour TTL balances freshness and performance
- MD5 key hashing is fast and collision-resistant
- Max 1000 items prevents memory bloat

### 5. Middleware-Based Metrics
**Rationale**:
- Decoupled from business logic
- Easy to enable/disable
- Comprehensive monitoring without boilerplate
- Minimal performance overhead

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| CLI | Typer | Command-line interface |
| Web | FastAPI | REST API framework |
| Database | ChromaDB | Vector database |
| LLM | Multiple providers | Generative AI |
| Testing | pytest | Unit/integration tests |
| Data | Pydantic | Type validation |
| Async | asyncio | Concurrent operations |

---

## Extension Points

### Adding a New LLM Provider
1. Add provider to `LLMConfig` enum
2. Implement `_generate_{provider}()` in `llm.py`
3. Implement `_embed_{provider}()` in `llm.py`
4. Add to provider router switch statement
5. Update `init.py` wizard
6. Add tests

### Adding a New Command
1. Create file in `commands/`
2. Use Typer decorator
3. Use `retrieve()` for search logic
4. Add to `cli.py`

### Adding Middleware
1. Extend `brain/middleware.py`
2. Implement before/after hooks
3. Integrate in `web_ui.py` request handlers

---

## Performance Characteristics

| Operation | Typical Time | Bottleneck |
|-----------|-------------|-----------|
| Search (API) | 1.6s | Embedding API |
| Q&A (API) | 2-5s | LLM generation |
| Cache hit | <1ms | Memory lookup |
| Indexing (per note) | 50-200ms | Embedding generation |
| Rate limit check | <0.1ms | Dict lookup |

---

## Error Handling

**Validation Layer**:
- Input: Length, format, type checks
- Output: 422 (Unprocessable Entity)

**Rate Limit Layer**:
- Exceeded: 429 (Too Many Requests)
- Retry-After header included

**Database Layer**:
- Connection error: 500 (Internal Server Error)
- Retry logic for transient errors

**LLM Layer**:
- API error: 500 with error message
- Timeout: 504 (Gateway Timeout)

---

## Monitoring & Observability

**Metrics Tracked**:
- Server uptime (seconds)
- Request counts per endpoint
- Cache hit/miss rates
- Cache current size vs max size
- Rate limit violations per IP

**Logging**:
- INFO: Normal operations
- WARNING: Rate limit exceeded
- ERROR: Exception handling
- DEBUG: Detailed execution (optional)

**Access Points**:
- `/api/stats` - Metrics dashboard
- Application logs - Structured logging
- CLI output - Real-time feedback

---

## Security Considerations

1. **Input Validation**: All user inputs validated
2. **Rate Limiting**: Prevents abuse
3. **Query Isolation**: No SQL injection (using ChromaDB)
4. **API Keys**: Stored in `.env` (not in code)
5. **Error Messages**: Generic public errors, detailed logging

---

## Future Architecture Improvements

1. **Authentication/Authorization**: API key system
2. **Distributed Caching**: Redis for multi-instance
3. **Database Replication**: High availability
4. **Query Pipeline Optimization**: Parallel retrieval
5. **Custom Embedding Models**: Fine-tuned embeddings
6. **Analytics Dashboard**: Advanced monitoring

