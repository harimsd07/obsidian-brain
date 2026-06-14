# Installation & Configuration Guide

## System Requirements

### Minimum
- Python 3.11 or higher
- 4GB RAM
- 500MB disk space (plus space for vault)
- Linux, macOS, or Windows (WSL2 recommended for Windows)

### Recommended
- Python 3.12+
- 8GB+ RAM
- SSD for faster indexing
- Modern CPU for embedding generation

---

## Installation Methods

### Method 1: From Source (Recommended for Development)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/obsidian-brain.git
cd obsidian-brain

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (CMD):
.venv\Scripts\activate.bat

# 4. Install in development mode
pip install -e .

# 5. Verify installation
brain --help
```

### Method 2: Pip Installation (from PyPI)

```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install package
pip install obsidian-brain

# Verify
brain --help
```

### Method 3: Docker

```bash
# Build image
docker build -t obsidian-brain .

# Run container with volume mount
docker run -it \
  -v /path/to/vault:/vault \
  -v /path/to/.env:/.env \
  obsidian-brain

# Inside container:
brain init
brain ingest
brain serve
```

---

## Configuration

### Quick Setup (Interactive)

```bash
# Start interactive setup wizard
brain init

# Follow prompts:
# 1. Vault path (default: ~/Obsidian)
# 2. LLM provider (1: Ollama, 2: Groq, 3: Gemini, 4: NVIDIA NIM)
# 3. API keys (if cloud provider)
# 4. Embedding model
# 5. Search settings
```

### Manual Configuration

Create `.env` file in project root:

```bash
# Vault Configuration
BRAIN_VAULT_PATH=/path/to/obsidian/vault

# LLM Provider (ollama, groq, google, nvidia-nim)
BRAIN_LLM_PROVIDER=ollama
BRAIN_LLM_MODEL=llama2

# Cloud Provider API Keys (if needed)
GROQ_API_KEY=your_api_key_here
GOOGLE_API_KEY=your_api_key_here
NVIDIA_NIM_API_KEY=your_api_key_here

# Search Settings
BRAIN_HYBRID_SEARCH=true
BRAIN_TOP_K=5

# Web UI Settings
BRAIN_WEB_HOST=127.0.0.1
BRAIN_WEB_PORT=8000

# Indexing Settings
BRAIN_CHUNK_SIZE=512
BRAIN_BATCH_SIZE=32
```

---

## Provider Setup

### Option 1: Ollama (Local - Recommended for Privacy)

**Setup**:
```bash
# 1. Install Ollama from https://ollama.ai
# 2. Start Ollama service
ollama serve

# 3. In another terminal, pull a model
ollama pull llama2          # Small, fast
ollama pull mistral         # Better quality
ollama pull neural-chat     # Chat optimized
ollama pull nomic-embed-text  # Embeddings

# 4. Configure in Obsidian Brain
brain init
# Select: 1 (Ollama)
# Model: llama2 (or your chosen model)
```

**Advantages**:
- ✓ Complete privacy (runs locally)
- ✓ No API costs
- ✓ Fast (GPU accelerated)
- ✓ Works offline

**Disadvantages**:
- ✗ Requires local GPU for speed
- ✗ Lower quality than cloud models

**Environment Variables**:
```bash
BRAIN_LLM_PROVIDER=ollama
BRAIN_LLM_MODEL=llama2
BRAIN_OLLAMA_BASE_URL=http://localhost:11434  # Optional
```

---

### Option 2: Groq (Cloud - Free, Very Fast)

**Setup**:
```bash
# 1. Create account at https://console.groq.com
# 2. Generate API key from console
# 3. Configure in Obsidian Brain
brain init
# Select: 2 (Groq)
# API Key: [paste your key]
```

**Advantages**:
- ✓ Very fast (dedicated LPU hardware)
- ✓ Free tier available
- ✓ High quality models (Mixtral 8x7B)
- ✓ No setup required

**Disadvantages**:
- ✗ Rate limited (free tier)
- ✗ Requires internet
- ✗ Data sent to cloud

**Environment Variables**:
```bash
BRAIN_LLM_PROVIDER=groq
BRAIN_LLM_MODEL=mixtral-8x7b-32768
GROQ_API_KEY=your_api_key_here
```

**Getting API Key**:
1. Visit https://console.groq.com/keys
2. Create new API key
3. Copy and paste into setup

---

### Option 3: Google Gemini (Cloud - Free)

**Setup**:
```bash
# 1. Get API key from https://makersuite.google.com/app/apikey
# 2. Configure in Obsidian Brain
brain init
# Select: 3 (Gemini)
# API Key: [paste your key]
```

**Advantages**:
- ✓ Free tier available
- ✓ Excellent quality
- ✓ Vision capabilities (future)
- ✓ Easy setup

**Disadvantages**:
- ✗ Rate limited (free tier: 60/min)
- ✗ Requires internet
- ✗ Data sent to Google

**Environment Variables**:
```bash
BRAIN_LLM_PROVIDER=google
BRAIN_LLM_MODEL=gemini-1.5-pro
GOOGLE_API_KEY=your_api_key_here
```

**Getting API Key**:
1. Visit https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy and paste into setup

---

### Option 4: NVIDIA NIM (Enterprise - Best Performance)

**Setup**:
```bash
# 1. Get API key from https://build.nvidia.com
# 2. Configure in Obsidian Brain
brain init
# Select: 4 (NVIDIA NIM)
# API Key: [paste your key]
```

**Advantages**:
- ✓ Fastest performance (3-5x faster than cloud)
- ✓ Highest quality models (Llama 3.1 70B)
- ✓ Enterprise support
- ✓ High rate limits

**Disadvantages**:
- ✗ Enterprise pricing
- ✗ Requires signup
- ✗ Data sent to NVIDIA

**Environment Variables**:
```bash
BRAIN_LLM_PROVIDER=nvidia-nim
BRAIN_LLM_MODEL=meta/llama-3.1-70b-instruct
NVIDIA_NIM_API_KEY=your_api_key_here
BRAIN_NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
```

**Getting API Key**:
1. Visit https://build.nvidia.com
2. Sign up and verify email
3. Create new API key
4. Copy and paste into setup

---

## Post-Installation Verification

### 1. Check Installation
```bash
# Should show version and help
brain --help

# Should show configuration
brain config show
```

### 2. Verify LLM Provider
```bash
# For Ollama
ollama list  # Should show at least one model

# For Cloud Providers
brain config test  # Tests API connectivity
```

### 3. Configure Vault Path
```bash
# Update .env
BRAIN_VAULT_PATH=/path/to/your/obsidian/vault

# Or use setup wizard
brain init
```

### 4. First Indexing
```bash
# Index your vault
brain ingest

# Watch for progress output
# Should show: "Indexed X documents"

# Check indexed documents
brain stats
```

### 5. Test Search
```bash
# Try a search
brain search "python"

# Should return results from your vault
```

### 6. Test Q&A
```bash
# Ask a question
brain ask "What notes do I have about Python?"

# Should return answer with citations
```

---

## Troubleshooting Installation

### Issue: Python version not supported
```bash
# Check Python version
python --version

# Should be 3.11 or higher
# If not, install newer version from python.org
```

### Issue: Virtual environment not activating
```bash
# Try explicit path
source /full/path/to/.venv/bin/activate

# Or use Python module method
python -m venv .venv
python -m venv --upgrade .venv
```

### Issue: Dependencies not installing
```bash
# Clear pip cache
pip cache purge

# Try upgrading pip
pip install --upgrade pip

# Install with verbose output
pip install -e . -v
```

### Issue: Ollama not connecting
```bash
# Check Ollama is running
ollama serve

# Check it's accessible
curl http://localhost:11434/api/tags

# Update base URL in .env if needed
BRAIN_OLLAMA_BASE_URL=http://localhost:11434
```

### Issue: API key not working
```bash
# Verify key is correct
echo $GROQ_API_KEY

# Check .env file is loaded
brain config show

# Test API connection
brain config test
```

### Issue: Vault path not found
```bash
# Check path exists
ls -la /path/to/vault

# Update .env with correct path
BRAIN_VAULT_PATH=/correct/path

# Verify configuration
brain config show
```

---

## Advanced Configuration

### Custom Embedding Models

```bash
# For Ollama (download specific model)
ollama pull nomic-embed-text
# Configure in .env
BRAIN_EMBEDDING_MODEL=nomic-embed-text
```

### Batch Indexing Settings

```bash
# For large vaults (1000+ notes)
BRAIN_BATCH_SIZE=64      # Larger = faster but uses more RAM
BRAIN_CHUNK_SIZE=1024    # Larger chunks = fewer embeddings
```

### Caching Configuration

```bash
# Query cache TTL (seconds)
BRAIN_CACHE_TTL=3600     # 1 hour default

# Max cache items
BRAIN_CACHE_MAX_SIZE=1000
```

### Rate Limiting Configuration

```bash
# Requests per hour (per IP)
BRAIN_RATE_LIMIT_SEARCH=100
BRAIN_RATE_LIMIT_ASK=50
BRAIN_RATE_LIMIT_STATS=1000
```

### Web UI Configuration

```bash
# Host and port
BRAIN_WEB_HOST=0.0.0.0      # Listen on all IPs
BRAIN_WEB_PORT=8000

# Enable/disable features
BRAIN_ENABLE_DOCS=true      # Swagger UI
BRAIN_ENABLE_REDOC=true     # ReDoc
```

---

## Database Management

### Reset Database
```bash
# Clear all indexed documents
brain db reset

# Confirm when prompted
# Note: This cannot be undone!
```

### Migrate to Different Provider
```bash
# When switching LLM providers (esp. Ollama → NVIDIA NIM)
# Different embedding dimensions require reset

# 1. Backup current database
cp -r data/chroma data/chroma.backup

# 2. Update .env with new provider
BRAIN_LLM_PROVIDER=nvidia-nim

# 3. Reset database
brain db reset

# 4. Re-index vault
brain ingest
```

### Optimize Database
```bash
# Compact ChromaDB
brain db optimize

# Removes duplicate entries and optimizes indexes
```

---

## Platform-Specific Notes

### macOS
```bash
# If using M1/M2 (Apple Silicon)
# Ensure Python is arm64 native
arch -arm64 python --version

# If using Ollama on Mac
# Ollama runs with GPU acceleration automatically
```

### Linux
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install python3.11 python3.11-venv

# For GPU support (NVIDIA)
# Install CUDA toolkit
```

### Windows (WSL2 Recommended)
```bash
# Install WSL2
wsl --install

# Inside WSL2, follow Linux instructions
# Or use native Windows:
python -m venv .venv
.venv\Scripts\activate.ps1
pip install -e .
```

---

## Docker Setup

### Dockerfile Example
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy code
COPY . .

# Install Python dependencies
RUN pip install -e .

# Expose web UI port
EXPOSE 8000

# Volume for vault
VOLUME ["/vault"]

# Default command
CMD ["brain", "serve", "--host", "0.0.0.0"]
```

### Docker Compose Example
```yaml
version: '3.8'

services:
  brain:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./vault:/vault
      - ./.env:/.env
    environment:
      BRAIN_VAULT_PATH: /vault
      BRAIN_WEB_HOST: 0.0.0.0
```

---

## Environment Variables Reference

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `BRAIN_VAULT_PATH` | `~/Obsidian` | Yes | Path to Obsidian vault |
| `BRAIN_LLM_PROVIDER` | `ollama` | No | LLM provider (ollama, groq, google, nvidia-nim) |
| `BRAIN_LLM_MODEL` | `llama2` | No | Provider-specific model name |
| `GROQ_API_KEY` | - | If using Groq | Groq API key |
| `GOOGLE_API_KEY` | - | If using Gemini | Google API key |
| `NVIDIA_NIM_API_KEY` | - | If using NIM | NVIDIA API key |
| `BRAIN_HYBRID_SEARCH` | `true` | No | Enable hybrid search |
| `BRAIN_TOP_K` | `5` | No | Default results count |
| `BRAIN_CHUNK_SIZE` | `512` | No | Document chunk size |
| `BRAIN_BATCH_SIZE` | `32` | No | Indexing batch size |
| `BRAIN_CACHE_TTL` | `3600` | No | Cache TTL (seconds) |
| `BRAIN_WEB_HOST` | `127.0.0.1` | No | Web UI host |
| `BRAIN_WEB_PORT` | `8000` | No | Web UI port |

---

## Next Steps

After installation, see:
- [COMMANDS.md](./COMMANDS.md) - All CLI commands
- [WORKFLOW.md](./WORKFLOW.md) - Usage examples
- [API.md](./API.md) - REST API reference
