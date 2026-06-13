from dataclasses import dataclass
from typing import Optional
from brain.llm import embed
from brain import db
from brain.config import TOP_K


@dataclass
class RetrievedChunk:
    doc_id: str
    file_path: str
    note_title: str
    heading: str
    text: str
    score: float        # cosine distance — lower = more similar
    semantic_score: Optional[float] = None  # for hybrid search
    keyword_score: Optional[float] = None   # for hybrid search


def _semantic_retrieve(query: str, n: int = TOP_K, where=None) -> list[RetrievedChunk]:
    """Retrieve chunks using semantic similarity (vector search)."""
    query_embedding = embed(query)

    try:
        results = db.query(query_embedding, n_results=n, where=where)
    except Exception as e:
        return []

    chunks = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc_id, text, meta, dist in zip(ids, docs, metas, distances):
        chunks.append(RetrievedChunk(
            doc_id=doc_id,
            file_path=meta.get("file_path", ""),
            note_title=meta.get("note_title", ""),
            heading=meta.get("heading", ""),
            text=text,
            score=round(dist, 4),
            semantic_score=round(dist, 4),
        ))

    return chunks


def _keyword_retrieve(query: str, n: int = TOP_K, where=None) -> list[RetrievedChunk]:
    """Retrieve chunks using BM25 keyword matching."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return []

    # Get all chunks (we'll filter by BM25)
    try:
        col = db.get_collection()
        # Fetch all documents with metadata
        all_results = col.get(include=["documents", "metadatas"])
    except Exception:
        return []

    if not all_results.get("documents"):
        return []

    docs = all_results.get("documents", [])
    metas = all_results.get("metadatas", [])
    ids = all_results.get("ids", [])

    if not docs or len(docs) == 0:
        return []

    # Tokenize documents for BM25
    tokenized_docs = [doc.lower().split() for doc in docs]
    
    # Skip if all documents are empty
    if not any(tokenized_docs):
        return []
    
    try:
        bm25 = BM25Okapi(tokenized_docs)
    except Exception:
        # BM25 initialization failed (e.g., empty corpus)
        return []

    # Score query
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    # Get top-n
    scored = [
        (score, idx, doc_id, doc, meta)
        for idx, (score, doc_id, doc, meta) in enumerate(zip(scores, ids, docs, metas))
        if score > 0
    ]
    scored.sort(reverse=True)
    top_results = scored[:n]

    chunks = []
    for score, idx, doc_id, text, meta in top_results:
        chunks.append(RetrievedChunk(
            doc_id=doc_id,
            file_path=meta.get("file_path", ""),
            note_title=meta.get("note_title", ""),
            heading=meta.get("heading", ""),
            text=text,
            score=round(score, 4),
            keyword_score=round(score, 4),
        ))

    return chunks


def retrieve(query: str, n: int = TOP_K, where=None, hybrid: bool = True) -> list[RetrievedChunk]:
    """
    Retrieve chunks using semantic search, keyword search, or hybrid (both).
    
    Args:
        query: Search query
        n: Number of results to return
        where: ChromaDB filter (semantic only)
        hybrid: If True, combine semantic and keyword results. If False, semantic only.
    
    Returns:
        List of RetrievedChunk sorted by combined score
    """
    if not hybrid:
        return _semantic_retrieve(query, n, where)
    
    # Hybrid search: combine semantic and keyword results
    semantic_results = _semantic_retrieve(query, n=n*2, where=where)  # Get more for merging
    keyword_results = _keyword_retrieve(query, n=n*2, where=where)
    
    # Create a dictionary to merge results by doc_id
    merged = {}
    
    # Add semantic results (weighted: 0.7)
    for chunk in semantic_results:
        normalized_semantic = 1 - chunk.semantic_score  # Convert distance to similarity
        merged[chunk.doc_id] = {
            "chunk": chunk,
            "score": normalized_semantic * 0.7,
        }
    
    # Add/merge keyword results (weighted: 0.3)
    for chunk in keyword_results:
        normalized_keyword = chunk.keyword_score / 100.0  # Normalize BM25 score
        if chunk.doc_id in merged:
            merged[chunk.doc_id]["score"] += normalized_keyword * 0.3
        else:
            merged[chunk.doc_id] = {
                "chunk": chunk,
                "score": normalized_keyword * 0.3,
            }
    
    # Sort by combined score and return top-n
    sorted_results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:n]
    
    result_chunks = []
    for item in sorted_results:
        chunk = item["chunk"]
        chunk.score = round(item["score"], 4)
        result_chunks.append(chunk)
    
    return result_chunks


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a context block for the LLM prompt."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[{i}] Note: {chunk.note_title}"
        if chunk.heading and chunk.heading != "__intro__":
            header += f" › {chunk.heading}"
        header += f"\nPath: {chunk.file_path}"
        parts.append(f"{header}\n\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def format_sources(chunks: list[RetrievedChunk]) -> list[str]:
    """Return deduplicated source paths with titles for display."""
    seen = set()
    sources = []
    for chunk in chunks:
        key = chunk.file_path
        if key not in seen:
            seen.add(key)
            label = f"{chunk.note_title}  [dim]({chunk.file_path})[/dim]"
            sources.append(label)
    return sources