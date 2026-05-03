from dataclasses import dataclass
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


def retrieve(query: str, n: int = TOP_K, where=None) -> list[RetrievedChunk]:
    """Embed query and return top-n most relevant chunks from ChromaDB."""
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
        ))

    return chunks


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