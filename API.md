# REST API Reference

Complete reference for the Obsidian Brain REST API with OpenAPI documentation.

---

## Overview

The REST API provides programmatic access to vault search, Q&A, and statistics. The API is fully documented with OpenAPI 3.0 specification and includes interactive documentation.

### Access Points

- **Web UI**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/api/docs (interactive)
- **ReDoc**: http://localhost:8000/api/redoc (reference)
- **OpenAPI Schema**: http://localhost:8000/api/openapi.json

### Start Web Server

```bash
brain serve --host 0.0.0.0 --port 8000
```

---

## Authentication

Currently, the API does not require authentication. Future versions will support API keys.

---

## Rate Limiting

API requests are rate-limited per IP address and endpoint.

### Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/search` | 100 requests | 1 hour |
| `/api/ask` | 50 requests | 1 hour |
| `/api/stats` | 1000 requests | 1 hour |

### Rate Limit Response

When limit exceeded, the API returns:

```json
HTTP/1.1 429 Too Many Requests
Retry-After: 3600

{
  "success": false,
  "error": "Rate limit exceeded. Try again in 1 hour"
}
```

---

## Caching

Identical requests are cached for 1 hour. The cache key is based on:
- Endpoint
- Query/question text
- Top K value
- Hybrid search flag

Cache hits are transparent to the client.

---

## Request Format

All requests use JSON format with `Content-Type: application/json`.

### Common Headers

```
Content-Type: application/json
Accept: application/json
```

### Request Validation

All requests are validated:
- **Queries/Questions**: 1-10,000 characters
- **Top K**: 1-1,000 (default: 5)
- **Invalid requests**: Return 422 (Unprocessable Entity)

---

## Response Format

All successful responses follow this format:

```json
{
  "success": true,
  "data": { /* endpoint-specific data */ }
}
```

Error responses:

```json
{
  "success": false,
  "error": "Error message"
}
```

---

## Endpoints

### 1. Search Endpoint

**Hybrid semantic + keyword search** of your vault.

#### Request

```
POST /api/search
Content-Type: application/json

{
  "query": "python decorators",
  "top_k": 5,
  "hybrid": true
}
```

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| query | string | Yes | - | Search query (1-10,000 chars) |
| top_k | integer | No | 5 | Number of results (1-1,000) |
| hybrid | boolean | No | true | Use hybrid search (semantic + keyword) |

#### Response (Success)

```json
{
  "success": true,
  "data": {
    "query": "python decorators",
    "count": 3,
    "results": [
      {
        "doc_id": "python/advanced.md",
        "title": "Decorators",
        "content": "Decorators are functions that modify other functions...",
        "score": 0.94,
        "metadata": {
          "source": "python/advanced.md",
          "line": 42,
          "chunk_index": 2
        }
      },
      {
        "doc_id": "patterns/functional.md",
        "title": "Functional Patterns",
        "content": "Common functional programming patterns including decorators...",
        "score": 0.87,
        "metadata": {
          "source": "patterns/functional.md",
          "line": 156,
          "chunk_index": 8
        }
      }
    ],
    "cached": false,
    "query_time_ms": 1567
  }
}
```

#### Response (Error)

```json
{
  "success": false,
  "error": "Query cannot be empty or whitespace"
}
```

#### Examples

```bash
# Basic search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning"}'

# Get 10 results
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Python", "top_k": 10}'

# Semantic search only
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "concepts", "hybrid": false}'
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| doc_id | string | Document identifier (file path) |
| title | string | Chunk title/heading |
| content | string | Text content of the chunk |
| score | number | Relevance score (0-1, higher is better) |
| metadata | object | Additional metadata (source, line, chunk_index) |
| cached | boolean | Whether result was from cache |
| query_time_ms | number | Query execution time in milliseconds |

---

### 2. Ask Endpoint

**AI-powered Q&A** with citations from your vault.

#### Request

```
POST /api/ask
Content-Type: application/json

{
  "question": "How do decorators work in Python?",
  "top_k": 5,
  "thinking": false
}
```

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| question | string | Yes | - | Question to ask (1-10,000 chars) |
| top_k | integer | No | 5 | Number of context docs (1-1,000) |
| thinking | boolean | No | false | Show LLM reasoning process |

#### Response (Success)

```json
{
  "success": true,
  "data": {
    "question": "How do decorators work in Python?",
    "answer": "Decorators in Python are functions that take another function as input and extend its behavior without permanently modifying it. They use the @syntax as syntactic sugar...",
    "sources": [
      {
        "doc_id": "python/advanced.md",
        "title": "Decorators",
        "score": 0.94,
        "content": "Decorators are functions that modify other functions..."
      },
      {
        "doc_id": "patterns/functional.md",
        "title": "Functional Patterns",
        "score": 0.87,
        "content": "Common functional programming patterns..."
      }
    ],
    "thinking": null,
    "cached": false,
    "query_time_ms": 3245
  }
}
```

#### Response with Thinking

```json
{
  "success": true,
  "data": {
    "question": "How do decorators work in Python?",
    "thinking": "The user is asking about Python decorators. This is a technical question about a programming concept. I should find relevant information about decorators in the vault and explain the concept clearly.",
    "answer": "Decorators in Python are...",
    "sources": [...],
    "cached": false,
    "query_time_ms": 3567
  }
}
```

#### Examples

```bash
# Basic question
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is machine learning?"}'

# With more context
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Best practices?", "top_k": 15}'

# Show reasoning
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain quantum computing", "thinking": true}'
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| question | string | The question asked |
| answer | string | AI-generated answer |
| sources | array | Source documents used for answer |
| thinking | string | LLM reasoning (if thinking=true) |
| cached | boolean | Whether result was from cache |
| query_time_ms | number | Query execution time in milliseconds |

---

### 3. Stats Endpoint

**Get vault statistics** and server metrics.

#### Request

```
GET /api/stats
```

#### Response (Success)

```json
{
  "success": true,
  "data": {
    "vault": {
      "total_documents": 350,
      "total_chunks": 7250,
      "vector_dimension": 768,
      "database_size_mb": 42.5,
      "last_updated": "2024-01-15T14:32:10Z"
    },
    "metrics": {
      "uptime_seconds": 3600,
      "total_requests": 245,
      "search_requests": 120,
      "ask_requests": 95,
      "stats_requests": 30
    },
    "cache": {
      "size": 45,
      "max_size": 1000,
      "hit_rate": 0.35,
      "ttl_seconds": 3600
    }
  }
}
```

#### Examples

```bash
# Get stats
curl http://localhost:8000/api/stats

# Formatted output
curl http://localhost:8000/api/stats | jq '.'
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| vault.total_documents | integer | Total indexed documents |
| vault.total_chunks | integer | Total text chunks |
| vault.vector_dimension | integer | Embedding dimension |
| vault.database_size_mb | number | Database size in MB |
| metrics.uptime_seconds | integer | Server uptime |
| metrics.total_requests | integer | Total requests received |
| cache.size | integer | Current cache items |
| cache.max_size | integer | Maximum cache items |
| cache.hit_rate | number | Cache hit percentage |

---

### 4. Documentation Endpoints

#### Interactive Swagger UI

```
GET /api/docs
```

Provides interactive API documentation where you can test requests directly.

#### ReDoc Documentation

```
GET /api/redoc
```

Provides reference documentation with organized endpoint details.

#### OpenAPI Schema

```
GET /api/openapi.json
```

Returns the full OpenAPI 3.0 specification in JSON format.

---

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "success": false,
  "error": "Invalid request format"
}
```

#### 422 Unprocessable Entity
```json
{
  "success": false,
  "error": "Query must be between 1 and 10000 characters. Got 10001 characters"
}
```

#### 429 Too Many Requests
```json
{
  "success": false,
  "error": "Rate limit exceeded. Limit: 100/hour. Try again in 3600 seconds"
}
```

#### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Internal server error. Please try again later"
}
```

---

## Usage Examples

### Python

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# Search
response = requests.post(
    f"{BASE_URL}/api/search",
    json={
        "query": "python decorators",
        "top_k": 5
    }
)
results = response.json()
print(results["data"]["results"])

# Ask
response = requests.post(
    f"{BASE_URL}/api/ask",
    json={
        "question": "How do decorators work?",
        "top_k": 5,
        "thinking": True
    }
)
answer = response.json()
print(answer["data"]["answer"])
print("Sources:", answer["data"]["sources"])

# Stats
response = requests.get(f"{BASE_URL}/api/stats")
stats = response.json()
print(f"Vault has {stats['data']['vault']['total_documents']} documents")
```

### JavaScript / Node.js

```javascript
const BASE_URL = 'http://localhost:8000';

// Search
async function search(query, topK = 5) {
  const response = await fetch(`${BASE_URL}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      top_k: topK,
      hybrid: true
    })
  });
  return response.json();
}

// Ask
async function ask(question, topK = 5) {
  const response = await fetch(`${BASE_URL}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      top_k: topK,
      thinking: false
    })
  });
  return response.json();
}

// Usage
const results = await search('python');
console.log(results.data.results);

const answer = await ask('How do decorators work?');
console.log(answer.data.answer);
```

### cURL

```bash
# Search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "top_k": 5
  }'

# Ask
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "top_k": 5
  }'

# Stats
curl http://localhost:8000/api/stats

# Pretty print
curl -s http://localhost:8000/api/stats | jq '.'
```

### Bash Script

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

# Function to search
search() {
  local query=$1
  curl -s -X POST "$BASE_URL/api/search" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$query\", \"top_k\": 5}" | jq '.data.results'
}

# Function to ask
ask() {
  local question=$1
  curl -s -X POST "$BASE_URL/api/ask" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"$question\", \"top_k\": 5}" | jq '.data.answer'
}

# Usage
search "python"
ask "How does Python work?"
```

---

## Integration Examples

### Integration with Discord Bot

```python
import discord
import requests

client = discord.Client()
BASE_URL = "http://localhost:8000"

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith('!ask '):
        question = message.content[5:]
        response = requests.post(
            f"{BASE_URL}/api/ask",
            json={"question": question, "top_k": 5}
        )
        data = response.json()
        await message.channel.send(data["data"]["answer"])
```

### Integration with Slack Bot

```python
from slack_bolt import App
import requests

app = App()
BASE_URL = "http://localhost:8000"

@app.message("ask")
def handle_ask(message, say):
    question = message.get("text", "")
    response = requests.post(
        f"{BASE_URL}/api/ask",
        json={"question": question, "top_k": 5}
    )
    data = response.json()
    say(data["data"]["answer"])

app.start(port=3000)
```

---

## Performance Tips

### Caching Strategy

```python
# Identical requests return cached results within 1 hour
# Cache key: endpoint + query + top_k + hybrid

# Make the same request twice
result1 = requests.post(f"{BASE_URL}/api/search",
    json={"query": "python", "top_k": 5})
# Takes ~1.5 seconds

result2 = requests.post(f"{BASE_URL}/api/search",
    json={"query": "python", "top_k": 5})
# Takes <1ms (from cache)

print(result1.json()["data"]["cached"])  # False
print(result2.json()["data"]["cached"])  # True
```

### Batch Requests

```python
import concurrent.futures

queries = ["python", "javascript", "rust", "go", "ruby"]

def search(query):
    return requests.post(
        f"{BASE_URL}/api/search",
        json={"query": query, "top_k": 3}
    )

# Parallel requests
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(search, queries))
```

### Query Optimization

```python
# ✓ Efficient: Specific query
{"query": "Python async patterns", "top_k": 5}

# ✗ Inefficient: Too vague
{"query": "stuff", "top_k": 100}

# ✓ Efficient: Reasonable top_k
{"query": "decorators", "top_k": 10}

# ✗ Inefficient: Excessive results
{"query": "decorators", "top_k": 500}
```

---

## Rate Limiting Strategy

### Optimal Request Distribution

```python
# ✓ Good: Spread requests over time
import time

for query in queries:
    result = requests.post(f"{BASE_URL}/api/search",
        json={"query": query})
    time.sleep(0.5)  # 1 request per 0.5 seconds

# ✗ Avoid: Burst requests (will hit rate limit)
for query in queries:
    result = requests.post(f"{BASE_URL}/api/search",
        json={"query": query})
    # No delay between requests
```

### Handle Rate Limiting

```python
import time
import requests

def safe_request(url, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json=data)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 3600))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

---

## Best Practices

1. **Use caching**: Don't repeat identical queries
2. **Batch similar requests**: Use thread pools for parallel requests
3. **Handle rate limiting**: Implement exponential backoff
4. **Validate input**: Check query length and top_k values
5. **Monitor performance**: Track query_time_ms in responses
6. **Error handling**: Handle all HTTP status codes
7. **Retry logic**: Implement for transient errors (500, 503)

---

## API Status & Health Check

```bash
# Check if API is running
curl -s http://localhost:8000/api/stats | jq '.success'

# Returns true if API is healthy
```

---

## See Also

- [INSTALLATION.md](./INSTALLATION.md) - Setup guide
- [COMMANDS.md](./COMMANDS.md) - CLI reference
- [WORKFLOW.md](./WORKFLOW.md) - Usage examples
