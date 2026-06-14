"""
Web UI server for Obsidian Brain.
Provides a simple web interface to search and query your vault.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
from pathlib import Path

from brain import db
from brain.config import VAULT_PATH, HYBRID_SEARCH
from brain.exceptions import VaultNotIndexed
from brain.retriever import retrieve, build_context, format_sources
from brain.llm import generate

app = FastAPI(title="Obsidian Brain", description="Chat with your Obsidian vault")

# ──────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=0, max_length=10000)
    top_k: int = Field(default=5, ge=1, le=1000)
    hybrid: bool = True


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=10000)
    thinking: bool = True
    top_k: int = Field(default=5, ge=1, le=1000)


class SearchResponse(BaseModel):
    success: bool
    chunks: list
    sources: list
    error: Optional[str] = None


class AskResponse(BaseModel):
    success: bool
    answer: str
    sources: list
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the web UI home page."""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🧠 Obsidian Brain</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }
            
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                border-bottom: 2px solid #eee;
            }
            
            .tab-btn {
                padding: 12px 20px;
                background: none;
                border: none;
                cursor: pointer;
                font-size: 1em;
                color: #666;
                border-bottom: 3px solid transparent;
                transition: all 0.3s;
            }
            
            .tab-btn.active {
                color: #667eea;
                border-bottom-color: #667eea;
            }
            
            .tab-btn:hover {
                color: #667eea;
            }
            
            .tab-content {
                display: none;
            }
            
            .tab-content.active {
                display: block;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 500;
            }
            
            input, textarea {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-family: inherit;
                font-size: 1em;
                resize: vertical;
            }
            
            input:focus, textarea:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .checkbox-group {
                display: flex;
                gap: 20px;
                align-items: center;
            }
            
            input[type="checkbox"] {
                width: auto;
            }
            
            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 6px;
                font-size: 1em;
                cursor: pointer;
                transition: transform 0.2s;
                font-weight: 600;
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }
            
            button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .results {
                margin-top: 30px;
                padding-top: 30px;
                border-top: 2px solid #eee;
            }
            
            .chunk {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                margin-bottom: 15px;
                border-left: 4px solid #667eea;
            }
            
            .chunk-header {
                font-weight: 600;
                color: #333;
                margin-bottom: 10px;
            }
            
            .chunk-text {
                color: #666;
                line-height: 1.6;
            }
            
            .sources {
                margin-top: 20px;
                padding: 15px;
                background: #f0f4ff;
                border-radius: 6px;
                border-left: 4px solid #667eea;
            }
            
            .sources h3 {
                color: #667eea;
                margin-bottom: 10px;
            }
            
            .source-item {
                color: #666;
                margin: 5px 0;
                padding-left: 20px;
            }
            
            .error {
                background: #fee;
                color: #c33;
                padding: 15px;
                border-radius: 6px;
                border-left: 4px solid #c33;
                margin: 20px 0;
            }
            
            .loading {
                text-align: center;
                color: #667eea;
                font-weight: 600;
            }
            
            .stats {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 6px;
                margin: 20px 0;
            }
            
            .stat-item {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #ddd;
            }
            
            .stat-item:last-child {
                border-bottom: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 Obsidian Brain</h1>
            <p class="subtitle">Search and ask questions about your notes</p>
            
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('search')">🔍 Search</button>
                <button class="tab-btn" onclick="switchTab('ask')">💬 Ask</button>
                <button class="tab-btn" onclick="switchTab('stats')">📊 Stats</button>
            </div>
            
            <!-- Search Tab -->
            <div id="search" class="tab-content active">
                <form onsubmit="handleSearch(event)">
                    <div class="form-group">
                        <label for="search-query">Search Query</label>
                        <input type="text" id="search-query" placeholder="e.g., How do I use RAG?" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="search-top-k">Results to Show</label>
                        <input type="number" id="search-top-k" value="5" min="1" max="20">
                    </div>
                    
                    <div class="form-group checkbox-group">
                        <input type="checkbox" id="search-hybrid" checked>
                        <label for="search-hybrid" style="margin: 0;">Use Hybrid Search (semantic + keyword)</label>
                    </div>
                    
                    <button type="submit">Search</button>
                </form>
                
                <div id="search-results" class="results" style="display: none;"></div>
            </div>
            
            <!-- Ask Tab -->
            <div id="ask" class="tab-content">
                <form onsubmit="handleAsk(event)">
                    <div class="form-group">
                        <label for="ask-question">Question</label>
                        <textarea id="ask-question" placeholder="Ask anything about your notes..." required></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="ask-top-k">Context Chunks</label>
                        <input type="number" id="ask-top-k" value="5" min="1" max="20">
                    </div>
                    
                    <div class="form-group checkbox-group">
                        <input type="checkbox" id="ask-thinking" checked>
                        <label for="ask-thinking" style="margin: 0;">Show LLM Reasoning</label>
                    </div>
                    
                    <button type="submit">Ask</button>
                </form>
                
                <div id="ask-results" class="results" style="display: none;"></div>
            </div>
            
            <!-- Stats Tab -->
            <div id="stats" class="tab-content">
                <button onclick="loadStats()" style="margin-bottom: 20px;">Load Stats</button>
                <div id="stats-content"></div>
            </div>
        </div>
        
        <script>
            function switchTab(tab) {
                // Hide all tabs
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                
                // Show selected tab
                document.getElementById(tab).classList.add('active');
                event.target.classList.add('active');
            }
            
            async function handleSearch(e) {
                e.preventDefault();
                const query = document.getElementById('search-query').value;
                const top_k = parseInt(document.getElementById('search-top-k').value);
                const hybrid = document.getElementById('search-hybrid').checked;
                
                const resultsDiv = document.getElementById('search-results');
                resultsDiv.innerHTML = '<p class="loading">Searching...</p>';
                resultsDiv.style.display = 'block';
                
                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({query, top_k, hybrid})
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        let html = '';
                        data.chunks.forEach((chunk, i) => {
                            html += `
                                <div class="chunk">
                                    <div class="chunk-header">${i+1}. ${chunk.note_title} › ${chunk.heading}</div>
                                    <div class="chunk-text">${escapeHtml(chunk.text)}</div>
                                </div>
                            `;
                        });
                        
                        html += '<div class="sources"><h3>Sources:</h3>';
                        data.sources.forEach(source => {
                            html += `<div class="source-item">📄 ${escapeHtml(source)}</div>`;
                        });
                        html += '</div>';
                        
                        resultsDiv.innerHTML = html;
                    } else {
                        resultsDiv.innerHTML = `<div class="error">${escapeHtml(data.error)}</div>`;
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
                }
            }
            
            async function handleAsk(e) {
                e.preventDefault();
                const question = document.getElementById('ask-question').value;
                const top_k = parseInt(document.getElementById('ask-top-k').value);
                const thinking = document.getElementById('ask-thinking').checked;
                
                const resultsDiv = document.getElementById('ask-results');
                resultsDiv.innerHTML = '<p class="loading">Thinking...</p>';
                resultsDiv.style.display = 'block';
                
                try {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question, thinking, top_k})
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        let html = `
                            <div class="chunk">
                                <div class="chunk-header">Answer</div>
                                <div class="chunk-text">${escapeHtml(data.answer)}</div>
                            </div>
                        `;
                        
                        html += '<div class="sources"><h3>Sources:</h3>';
                        data.sources.forEach(source => {
                            html += `<div class="source-item">📄 ${escapeHtml(source)}</div>`;
                        });
                        html += '</div>';
                        
                        resultsDiv.innerHTML = html;
                    } else {
                        resultsDiv.innerHTML = `<div class="error">${escapeHtml(data.error)}</div>`;
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
                }
            }
            
            async function loadStats() {
                const statsDiv = document.getElementById('stats-content');
                statsDiv.innerHTML = '<p class="loading">Loading...</p>';
                
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    if (data.success) {
                        let html = '<div class="stats">';
                        html += `<div class="stat-item"><strong>Total Chunks:</strong> ${data.stats.total_chunks}</div>`;
                        html += `<div class="stat-item"><strong>Vault Path:</strong> ${escapeHtml(data.stats.vault_path)}</div>`;
                        html += `<div class="stat-item"><strong>Hybrid Search:</strong> ${data.stats.hybrid_search ? 'Enabled' : 'Disabled'}</div>`;
                        html += '</div>';
                        statsDiv.innerHTML = html;
                    } else {
                        statsDiv.innerHTML = `<div class="error">${escapeHtml(data.error)}</div>`;
                    }
                } catch (error) {
                    statsDiv.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
                }
            }
            
            function escapeHtml(text) {
                const map = {
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                };
                return text.replace(/[&<>"']/g, m => map[m]);
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.post("/api/search", response_model=SearchResponse)
async def api_search(request: SearchRequest):
    """Search the vault semantically."""
    try:
        stats = db.collection_stats()
        if stats["total_chunks"] == 0:
            raise VaultNotIndexed()
        
        chunks = retrieve(request.query, n=request.top_k, hybrid=request.hybrid)
        
        if not chunks:
            return SearchResponse(success=True, chunks=[], sources=[])
        
        chunk_dicts = [
            {
                "note_title": c.note_title,
                "heading": c.heading,
                "file_path": c.file_path,
                "text": c.text,
                "score": c.score
            }
            for c in chunks
        ]
        
        sources = list(dict.fromkeys(
            f"{c.note_title} ({c.file_path})" for c in chunks
        ))
        
        return SearchResponse(success=True, chunks=chunk_dicts, sources=sources)
    
    except Exception as e:
        return SearchResponse(success=False, chunks=[], sources=[], error=str(e))


@app.post("/api/ask", response_model=AskResponse)
async def api_ask(request: AskRequest):
    """Ask a question about the vault."""
    try:
        stats = db.collection_stats()
        if stats["total_chunks"] == 0:
            raise VaultNotIndexed()
        
        chunks = retrieve(request.question, n=request.top_k, hybrid=HYBRID_SEARCH)
        
        if not chunks:
            raise ValueError("No relevant notes found.")
        
        context = build_context(chunks)
        sources = list(dict.fromkeys(
            f"{c.note_title} ({c.file_path})" for c in chunks
        ))
        
        system_prompt = """You are a knowledgeable assistant with access to the user's Obsidian notes.
Answer using ONLY the provided notes. Be specific and cite sources.
If notes don't contain enough information, say so."""
        
        if request.thinking:
            system_prompt += "\nWrap reasoning in <think>...</think> tags."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Notes:\n\n{context}\n\nQuestion: {request.question}"
            }
        ]
        
        # Collect LLM response
        answer = ""
        for delta in generate(messages, stream=True):
            answer += delta
        
        # Clean up thinking tags from answer if present
        if "<think>" in answer:
            parts = answer.split("<think>")
            answer = parts[0]
            for part in parts[1:]:
                if "</think>" in part:
                    answer += part.split("</think>", 1)[1]
        
        return AskResponse(success=True, answer=answer.strip(), sources=sources)
    
    except Exception as e:
        return AskResponse(success=False, answer="", sources=[], error=str(e))


@app.get("/api/stats")
async def api_stats():
    """Get vault statistics."""
    try:
        stats = db.collection_stats()
        return {
            "success": True,
            "stats": {
                "total_chunks": stats["total_chunks"],
                "vault_path": str(VAULT_PATH),
                "hybrid_search": HYBRID_SEARCH
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# Server startup
# ──────────────────────────────────────────────────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the web UI server."""
    import uvicorn
    print(f"✓ Obsidian Brain web UI running at http://{host}:{port}")
    print(f"  Open your browser and navigate to http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
