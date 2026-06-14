"""
MCP Server for Obsidian Brain.
Allows using your Obsidian vault with Claude Desktop or Cursor IDE.
"""

from typing import Any
import json
from pathlib import Path

from mcp.server import Server
from mcp.types import (
    Tool, TextContent, ToolResultContent, ListToolsResult,
    CallToolResult, ListResourcesResult, Resource, ReadResourceResult
)

from brain import db
from brain.config import VAULT_PATH, HYBRID_SEARCH
from brain.exceptions import BrainError, VaultNotIndexed
from brain.retriever import retrieve, build_context, format_sources
from brain.llm import generate

# Initialize MCP Server
server = Server("obsidian-brain")


# ──────────────────────────────────────────────────────────────────────────────
# Tools: Available to Claude/Cursor
# ──────────────────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List all available tools."""
    return ListToolsResult(tools=[
        Tool(
            name="search_vault",
            description="Search your Obsidian vault semantically. Returns relevant note chunks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Your search query"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    },
                    "hybrid": {
                        "type": "boolean",
                        "description": "Use hybrid search (semantic + BM25)?",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="ask_vault",
            description="Ask a question about your notes. Returns LLM-generated answer with sources.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Your question"
                    },
                    "thinking": {
                        "type": "boolean",
                        "description": "Show LLM reasoning?",
                        "default": True
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of note chunks to consider",
                        "default": 5
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="get_vault_stats",
            description="Get statistics about your indexed vault.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ])


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls from Claude/Cursor."""
    try:
        if name == "search_vault":
            return await _search_vault(arguments)
        elif name == "ask_vault":
            return await _ask_vault(arguments)
        elif name == "get_vault_stats":
            return await _get_vault_stats(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True
        )


async def _search_vault(args: dict[str, Any]) -> CallToolResult:
    """Search vault semantically."""
    query = args.get("query", "")
    top_k = args.get("top_k", 5)
    hybrid = args.get("hybrid", True)

    if not query:
        return CallToolResult(
            content=[TextContent(type="text", text="Query cannot be empty")],
            isError=True
        )

    # Check if vault is indexed
    stats = db.collection_stats()
    if stats["total_chunks"] == 0:
        return CallToolResult(
            content=[TextContent(type="text", text="Vault not indexed. Run 'brain ingest' first.")],
            isError=True
        )

    # Retrieve chunks
    chunks = retrieve(query, n=top_k, hybrid=hybrid)

    if not chunks:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="No relevant notes found for your query. Try rephrasing."
            )],
        )

    # Format response
    context = build_context(chunks)
    sources = format_sources(chunks)
    
    response = f"**Found {len(chunks)} relevant chunks:**\n\n{context}\n\n**Sources:**\n"
    for source in sources:
        response += f"- {source}\n"

    return CallToolResult(
        content=[TextContent(type="text", text=response)],
    )


async def _ask_vault(args: dict[str, Any]) -> CallToolResult:
    """Ask a question about the vault."""
    question = args.get("question", "")
    thinking = args.get("thinking", True)
    top_k = args.get("top_k", 5)

    if not question:
        return CallToolResult(
            content=[TextContent(type="text", text="Question cannot be empty")],
            isError=True
        )

    # Check if vault is indexed
    stats = db.collection_stats()
    if stats["total_chunks"] == 0:
        return CallToolResult(
            content=[TextContent(type="text", text="Vault not indexed. Run 'brain ingest' first.")],
            isError=True
        )

    # Retrieve chunks
    chunks = retrieve(question, n=top_k, hybrid=HYBRID_SEARCH)

    if not chunks:
        return CallToolResult(
            content=[TextContent(type="text", text="No relevant notes found.")],
        )

    # Build context and generate answer
    context = build_context(chunks)
    sources = format_sources(chunks)

    system_prompt = """You are a knowledgeable assistant with access to the user's Obsidian notes.
Answer using ONLY the provided notes. Be specific and cite sources.
If notes don't contain enough info, say so clearly."""

    if thinking:
        system_prompt += "\nWrap reasoning in <think>...</think> tags before answering."

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Here are my Obsidian notes:\n\n{context}\n\nQuestion: {question}"
        }
    ]

    # Stream and collect response
    answer = ""
    for delta in generate(messages, stream=True):
        answer += delta

    # Format response
    response = f"**Answer:**\n\n{answer}\n\n**Sources:**\n"
    for source in sources:
        response += f"- {source}\n"

    return CallToolResult(
        content=[TextContent(type="text", text=response)],
    )


async def _get_vault_stats(args: dict[str, Any]) -> CallToolResult:
    """Get vault statistics."""
    stats = db.collection_stats()
    
    response = f"""**Vault Statistics:**

- **Total Chunks**: {stats['total_chunks']}
- **Collection**: {stats['collection']}
- **Database Path**: {stats['path']}
- **Vault Path**: {VAULT_PATH}
- **Hybrid Search**: {'Enabled' if HYBRID_SEARCH else 'Disabled'}
"""
    
    return CallToolResult(
        content=[TextContent(type="text", text=response)],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Resources: Available files/data
# ──────────────────────────────────────────────────────────────────────────────

@server.list_resources()
async def list_resources() -> ListResourcesResult:
    """List available resources (indexed notes)."""
    try:
        col = db.get_collection()
        results = col.get(include=["metadatas"])
        
        # Deduplicate by file_path
        files = set()
        for meta in results.get("metadatas", []):
            if meta and "file_path" in meta:
                files.add(meta["file_path"])
        
        resources = [
            Resource(
                uri=f"obsidian://note/{fp}",
                name=fp,
                mimeType="text/markdown"
            )
            for fp in sorted(files)
        ]
        
        return ListResourcesResult(resources=resources)
    except Exception as e:
        return ListResourcesResult(resources=[])


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read a specific note."""
    try:
        # Parse URI: obsidian://note/{file_path}
        if not uri.startswith("obsidian://note/"):
            raise ValueError(f"Invalid URI: {uri}")
        
        file_path = uri.replace("obsidian://note/", "")
        full_path = VAULT_PATH / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {file_path}")
        
        content = full_path.read_text(encoding="utf-8")
        return ReadResourceResult(contents=content)
    except Exception as e:
        raise ValueError(f"Cannot read resource: {str(e)}")


# ──────────────────────────────────────────────────────────────────────────────
# Startup
# ──────────────────────────────────────────────────────────────────────────────

async def run():
    """Run the MCP server."""
    async with server:
        print("✓ Obsidian Brain MCP server started")
        print("  Available for Claude Desktop and Cursor IDE")
        await server.main()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
