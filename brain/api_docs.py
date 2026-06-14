"""
API Documentation and OpenAPI schema customization.
"""

from fastapi.openapi.utils import get_openapi

def get_openapi_schema(app):
    """Generate comprehensive OpenAPI schema for the API."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Obsidian Brain API",
        version="1.0.0",
        description="""
## Welcome to Obsidian Brain API

A powerful API for searching and querying your Obsidian vault using semantic search, keyword matching, and AI.

### Features
- **Hybrid Search**: Combines semantic similarity (70%) and keyword matching (30%)
- **Rate Limiting**: Protects servers with configurable limits per endpoint
- **Query Caching**: Caches frequent queries for better performance
- **Monitoring**: Built-in metrics tracking and logging

### Getting Started
1. Ensure your vault is indexed: `brain ingest` 
2. Start the web UI: `brain serve`
3. Use the API endpoints below to search and query your vault

### Rate Limits
- **Search**: 100 requests/hour per IP
- **Ask**: 50 requests/hour per IP  
- **Stats**: 1000 requests/hour per IP

### Response Format
All successful responses return JSON with `success: true` and endpoint-specific data.
Errors return `success: false` with an error message.

### Caching
Identical queries within 1 hour return cached results instantly for better performance.
        """,
        routes=app.routes
    )
    
    # Add tags metadata separately
    if "tags" not in openapi_schema:
        openapi_schema["tags"] = [
            {
                "name": "Search",
                "description": "Search your vault using semantic and keyword-based retrieval"
            },
            {
                "name": "Ask",
                "description": "Ask questions about your vault with AI-powered answers"
            },
            {
                "name": "Monitor",
                "description": "Get vault statistics and server metrics"
            }
        ]
    
    # Add server information
    if "servers" not in openapi_schema:
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "Local development server"
            }
        ]
    
    # Add security schemes if needed
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema.get("components", {}):
        openapi_schema["components"]["securitySchemes"] = {
            "apiKey": {
                "type": "apiKey",
                "name": "X-API-Key",
                "in": "header",
                "description": "Optional API key for future authentication"
            }
        }
    
    # Enhance endpoint schemas
    if "/api/search" in openapi_schema["paths"]:
        openapi_schema["paths"]["/api/search"]["post"]["tags"] = ["Search"]
        openapi_schema["paths"]["/api/search"]["post"]["summary"] = "Search vault"
        openapi_schema["paths"]["/api/search"]["post"]["description"] = """
Search your Obsidian vault using hybrid search (semantic + keyword-based).

**Rate Limit**: 100 requests/hour

**Caching**: Identical queries are cached for 1 hour
        """
    
    if "/api/ask" in openapi_schema["paths"]:
        openapi_schema["paths"]["/api/ask"]["post"]["tags"] = ["Ask"]
        openapi_schema["paths"]["/api/ask"]["post"]["summary"] = "Ask a question"
        openapi_schema["paths"]["/api/ask"]["post"]["description"] = """
Ask a question about your vault and get an AI-powered answer with citations.

**Rate Limit**: 50 requests/hour

**Caching**: Identical questions are cached for 1 hour

**Note**: Thinking mode adds reasoning steps wrapped in <think>...</think> tags
        """
    
    if "/api/stats" in openapi_schema["paths"]:
        openapi_schema["paths"]["/api/stats"]["get"]["tags"] = ["Monitor"]
        openapi_schema["paths"]["/api/stats"]["get"]["summary"] = "Get vault statistics"
        openapi_schema["paths"]["/api/stats"]["get"]["description"] = """
Get vault statistics and server metrics.

**Rate Limit**: 1000 requests/hour

**Metrics Included**:
- Total chunks indexed
- Vault path location
- Hybrid search enabled status
- Server uptime
- Request counts
- Cache statistics
        """
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Example responses for documentation
SEARCH_RESPONSE_EXAMPLE = {
    "success": True,
    "chunks": [
        {
            "note_title": "Python Basics",
            "heading": "Functions",
            "file_path": "Programming/Python/Basics.md",
            "text": "Functions are reusable blocks of code...",
            "score": 0.89
        }
    ],
    "sources": [
        "Python Basics (Programming/Python/Basics.md)"
    ]
}

ASK_RESPONSE_EXAMPLE = {
    "success": True,
    "answer": "Python functions are reusable blocks of code that perform specific tasks...",
    "sources": [
        "Python Basics (Programming/Python/Basics.md)",
        "Advanced Patterns (Programming/Python/Patterns.md)"
    ]
}

STATS_RESPONSE_EXAMPLE = {
    "success": True,
    "stats": {
        "total_chunks": 7751,
        "vault_path": "/home/user/Obsidian",
        "hybrid_search": True
    },
    "metrics": {
        "uptime_seconds": 3600,
        "total_requests": 150,
        "search_requests": 100,
        "ask_requests": 30,
        "stats_requests": 20,
        "cache_stats": {
            "size": 45,
            "maxsize": 1000,
            "ttl": 3600
        }
    }
}

ERROR_RESPONSE_EXAMPLE = {
    "success": False,
    "error": "No relevant notes found. Try rephrasing your query."
}

RATE_LIMIT_RESPONSE_EXAMPLE = {
    "success": False,
    "error": "Rate limit exceeded (100 searches/hour)"
}
