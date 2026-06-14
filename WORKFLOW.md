# Usage Workflows & Examples

Practical examples and workflows for using Obsidian Brain in real-world scenarios.

---

## Scenario 1: Student Learning Management

**Goal**: Keep notes organized and quickly find relevant concepts for studying.

### Setup
```bash
# 1. Initialize with your vault
brain init
# Select: Ollama (free, works offline for studying)
# Model: mistral (better quality than llama2)

# 2. Index your course notes
brain ingest

# 3. Set up auto-indexing
brain watch  # In background terminal
```

### Daily Workflow

```bash
# Search for concept
$ brain ask "Explain the carbon cycle"

Answer: The carbon cycle is the process by which carbon moves through Earth's
biosphere, lithosphere, hydrosphere, and atmosphere...

Sources:
• Biology/Biogeochemistry.md (line 45)
• Chemistry/Elements.md (line 120)

# Get multiple related topics
$ brain ask "carbon cycle" -k 10

# Study session - interactive mode
$ brain chat

> /search quantum mechanics
Results: [5 relevant notes]

> /ask What are the postulates of quantum mechanics?
Answer: The fundamental postulates are...

> /exit
```

### Study Session Example
```bash
# Preparation: Find all related materials
$ brain search "mitochondria cellular respiration" -k 10

# Interactive review
$ brain chat

> /search photosynthesis
> /ask How does photosynthesis relate to cellular respiration?
> /ask What are the steps of photosynthesis?
> /top 15  # Need more detailed information
```

---

## Scenario 2: Professional Developer

**Goal**: Quickly reference coding patterns, solutions, and best practices from personal knowledge base.

### Setup
```bash
# 1. Use cloud provider for speed
brain init
# Select: Groq (free tier, very fast)
# API Key: [from console.groq.com]

# 2. Index code snippets and notes
brain ingest

# 3. Keep watching for new learnings
brain watch
```

### Common Workflow

```bash
# Quick pattern lookup during development
$ brain ask "How do I implement retry logic in Python?" -k 5

Answer: Here's the recommended retry pattern using decorators...

Sources:
• Python/Patterns.md (line 234)
• Projects/retry-handler.md (line 12)

# Find performance optimization tips
$ brain search "database query optimization" --top-k 10

# Interactive session for complex topics
$ brain chat

> /ask What are the best practices for async/await in Python?
Answer: [Detailed response with sources]

> /ask What about error handling with async?
[Continues conversation with same context]

> /exit
```

### Project-Specific Query
```bash
# Search your project notes
$ brain ask "GraphQL schema design best practices" -k 10

# Get specific implementation examples
$ brain search "GraphQL resolver examples" --semantic-only

# Store findings in your vault, then re-index
$ brain watch  # Auto-detects new files
```

---

## Scenario 3: Data Scientist / Researcher

**Goal**: Find relevant papers, methodologies, and code from accumulated research notes.

### Setup
```bash
# 1. Use high-quality LLM for complex queries
brain init
# Select: NVIDIA NIM (enterprise, best quality)
# API Key: [from build.nvidia.com]

# 2. Index all research documents
brain ingest --verbose

# 3. Monitor vault for new findings
brain watch
```

### Research Workflow

```bash
# Literature search
$ brain ask "What are the latest approaches to transfer learning?" -k 15

# Methodology comparison
$ brain search "machine learning evaluation metrics" --top-k 10

# Code reference
$ brain ask "How do I implement custom PyTorch loss functions?" -k 5

# Interactive research session
$ brain chat

> /search attention mechanisms transformer
> /ask What are the advantages of multi-head attention?
> /ask How is positional encoding implemented?
> /ask Show me the mathematical formulation
> /search BERT GPT comparison
> /exit
```

### Analysis Session
```bash
# Find all notes on a topic
$ brain search "neural architecture search NAS" -k 20

# Get comprehensive understanding
$ brain ask "What is NAS and why is it important?" \
  -k 10 \
  --thinking  # Show reasoning

# Detailed method explanations
$ brain ask "Explain the NASNet architecture step by step" -k 15
```

---

## Scenario 4: Content Creator / Writer

**Goal**: Quickly find references, examples, and inspiration from notes while writing.

### Setup
```bash
# 1. Easy setup with Google Gemini
brain init
# Select: Google Gemini (free, good quality)
# API Key: [from makersuite.google.com]

# 2. Index all writing references
brain ingest

# 3. Keep notes synced
brain watch
```

### Writing Workflow

```bash
# Quick fact-checking
$ brain ask "What was the date of the moon landing?" -k 3

# Find relevant examples
$ brain search "product design case studies" -k 10

# Organize research during writing
$ brain chat

> /search machine learning applications
> /ask What are 5 real-world ML applications in healthcare?
> /ask Can you provide implementation examples?
> /search AI ethics considerations
> /ask What ethical concerns should be addressed?
> /exit
```

### Content Creation Session
```bash
# Outline creation
$ brain ask "Create an outline for an article on AI in healthcare" \
  -k 10 \
  --top-k 20

# Supporting research
$ brain search "deep learning medical imaging" -k 10

# Examples and case studies
$ brain ask "What are notable examples of AI in radiology?" -k 5
```

---

## Scenario 5: Team Lead / Manager

**Goal**: Ensure team has quick access to company knowledge, processes, and decisions.

### Setup
```bash
# 1. Host on server (rate-limited for team)
brain init
# Select: Groq (handles team traffic)

# 2. Index company knowledge base
brain ingest

# 3. Start web server
brain serve --host 0.0.0.0 --port 8000

# 4. Share URL with team
# http://your-server:8000
```

### Team Access

```bash
# Your team can now:

# 1. Search decision logs
$ brain ask "What was our decision on microservices architecture?"

# 2. Find processes
$ brain search "onboarding process" -k 5

# 3. Look up standards
$ brain ask "What is our code style guide?"

# 4. Reference history
$ brain ask "Why did we choose React over Vue?"

# 5. Check procedures
$ brain search "deployment checklist" -k 3
```

### Team Dashboard
```bash
# View API documentation
# Visit: http://your-server:8000/api/docs

# Teams can make API calls
curl -X POST http://your-server:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I set up development environment?",
    "top_k": 5
  }'

# Web UI for non-technical team members
# Visit: http://your-server:8000
# Simple interface to search and ask questions
```

---

## Scenario 6: Telegram Bot for Mobile Access

**Goal**: Access your knowledge base from anywhere via Telegram.

### Setup
```bash
# 1. Create Telegram bot via @BotFather
# Copy token and add to .env
echo "TELEGRAM_BOT_TOKEN=your_token_here" >> .env

# 2. Start bot
brain telegram

# 3. Message your bot
# /start
# /ask What is my favorite programming language?
# /search Python tutorials
# /stats
```

### Mobile Usage

```
You: /ask What are the best Python practices?

Bot: Python best practices include:
1. Follow PEP 8 style guide
2. Use type hints...

[Automatically splits long responses due to Telegram limits]

You: /search machine learning frameworks

Bot: Found 5 results:
1. TensorFlow guide
2. PyTorch tutorial
3. Scikit-learn reference
4. Keras documentation
5. JAX overview

You: /stats

Bot: Vault Statistics
Files: 350
Words: 145,230
Size: 12.4 MB
```

---

## Scenario 7: API Integration

**Goal**: Integrate Obsidian Brain with other tools and workflows.

### Setup
```bash
# 1. Start web server
brain serve --port 8000

# 2. Access API (documented at localhost:8000/api/docs)
```

### Search API Example
```bash
# Python example
import requests

response = requests.post(
    "http://localhost:8000/api/search",
    json={
        "query": "python decorators",
        "top_k": 5,
        "hybrid": True
    }
)

results = response.json()
for result in results['results']:
    print(f"{result['title']}: {result['score']:.2f}")
```

### Ask API Example
```bash
# Python example
response = requests.post(
    "http://localhost:8000/api/ask",
    json={
        "question": "How do Python decorators work?",
        "top_k": 5,
        "thinking": True
    }
)

answer = response.json()
print(answer['answer'])
print("Sources:", answer['sources'])
```

### JavaScript Integration
```javascript
// Fetch data for your app
async function searchVault(query) {
  const response = await fetch(
    'http://localhost:8000/api/search',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        top_k: 5,
        hybrid: true
      })
    }
  );
  return response.json();
}

// Use in your application
const results = await searchVault('machine learning');
results.results.forEach(r => console.log(r.title));
```

### cURL Examples
```bash
# Search endpoint
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python",
    "top_k": 5
  }'

# Ask endpoint
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Best practices?",
    "top_k": 5
  }'

# Stats endpoint
curl http://localhost:8000/api/stats
```

---

## Scenario 8: Performance Optimization

**Goal**: Improve search and query speed for production use.

### Tips & Tricks

```bash
# 1. Increase batch size for faster indexing
brain ingest --batch-size 64

# 2. Configure caching (1 hour default)
# .env: BRAIN_CACHE_TTL=3600

# 3. Use Groq/NIM for faster responses
brain init  # Switch to faster provider

# 4. Monitor with web UI
brain serve
# Visit http://localhost:8000/api/stats

# 5. Optimize database
brain db optimize

# 6. Scale to multiple workers
brain serve --workers 4

# 7. Clear old cache
brain cache clear
```

### Performance Monitoring
```bash
# Check stats
$ brain stats

Total Documents: 350
Query Cache Size: 245 / 1000
Average Query Time: 1.2s
Cache Hit Rate: 45%

# Optimize if needed
$ brain db optimize
✓ Database optimized
✓ Query speed improved 5-10%
```

---

## Scenario 9: Multi-Provider Testing

**Goal**: Compare different LLM providers for your use case.

### Setup & Testing

```bash
# 1. Start with Ollama (free baseline)
brain init
# Select: Ollama

# 2. Test search performance
$ time brain ask "Python" -k 5
# Real time: 1.234s

# 3. Switch to Groq
# Edit .env: BRAIN_LLM_PROVIDER=groq
# Add GROQ_API_KEY

$ time brain ask "Python" -k 5
# Real time: 0.567s (2x faster)

# 4. Compare response quality
$ brain ask "Explain decorators in Python"
# Save output to compare

# 5. Test with Gemini
# Switch in .env

# 6. Final decision based on:
# - Speed
# - Quality
# - Cost
# - Privacy
```

---

## Scenario 10: Automated Knowledge Extraction

**Goal**: Automatically extract and organize insights from vault.

### Workflow

```bash
# 1. Index vault
brain ingest

# 2. Extract statistics
$ brain stats --json > vault_stats.json

# 3. Generate report
$ brain ask "Summarize the 5 most important topics in my vault" -k 20

# 4. Find gaps
$ brain ask "What topics do I have incomplete notes on?"

# 5. Organize findings
$ brain search "TODO incomplete notes" -k 100

# 6. Create action items
$ brain ask "Based on my notes, what should I learn next?" -k 15
```

---

## Best Practices

### Effective Searching

```bash
# ✓ Good: Specific queries
brain ask "Python async/await patterns"

# ✗ Avoid: Too vague
brain ask "stuff"

# ✓ Good: Use full context
brain ask "How do I implement a retry decorator in Python?"

# ✗ Avoid: Fragmentary
brain ask "retry decorator"

# ✓ Good: Related concepts
brain ask "GraphQL vs REST API design patterns"

# ✗ Avoid: Unrelated topics
brain ask "How do I cook pasta and write Python code?"
```

### Maintaining Knowledge Base

```bash
# Regular indexing
brain watch  # Keep running in background

# Monitor growth
brain stats

# Archive old notes
# Move to Archive/ folder if inactive

# Add metadata to important notes
# Use tags: #important, #frequently-used

# Review and update
# Update outdated information
```

### Performance Tips

```bash
# Use semantic search for concepts
brain ask "What is machine learning?" --semantic-only

# Use hybrid for specific things
brain search "function definition syntax"

# Increase results for complex queries
brain ask "Advanced topic" -k 20

# Use exact phrases in quotes
brain search "exact phrase here"
```

---

## Troubleshooting Common Issues

### Slow Searches

```bash
# 1. Check provider performance
brain config test

# 2. Enable caching
# .env: BRAIN_CACHE_TTL=3600

# 3. Switch to faster provider
brain init

# 4. Optimize database
brain db optimize

# 5. Check rate limits
brain stats
```

### Poor Search Results

```bash
# 1. Add more context to query
brain ask "Your detailed question here" -k 10

# 2. Try semantic search
brain ask "topic" --semantic-only

# 3. Get more results
brain ask "topic" -k 20

# 4. Re-index vault
brain ingest --force

# 5. Update notes to be more comprehensive
```

### API Rate Limiting

```bash
# 1. Check current limits
brain config show

# 2. Increase limits in .env
BRAIN_RATE_LIMIT_SEARCH=1000
BRAIN_RATE_LIMIT_ASK=500

# 3. Use caching to reduce requests
# .env: BRAIN_CACHE_TTL=3600

# 4. Scale to multiple instances
brain serve --workers 4
```

---

## See Also

- [COMMANDS.md](./COMMANDS.md) - Complete command reference
- [API.md](./API.md) - REST API documentation
- [INSTALLATION.md](./INSTALLATION.md) - Setup guide
