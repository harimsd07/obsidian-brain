import chromadb
from chromadb.config import Settings
from brain.config import CHROMA_PATH, COLLECTION_NAME

_client = None
_collection = None

def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    global _collection
    if _collection is None:
        _collection = get_client().get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert_chunks(doc_ids: list[str], embeddings: list[list[float]], texts: list[str], metadatas: list[dict]):
    col = get_collection()
    col.upsert(
        ids=doc_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


def delete_by_file(file_path: str):
    """Remove all chunks belonging to a specific file."""
    col = get_collection()
    results = col.get(where={"file_path": file_path})
    if results and results["ids"]:
        col.delete(ids=results["ids"])


def query(embedding: list[float], n_results: int, where: dict | None = None) -> dict:
    col = get_collection()
    kwargs = {"query_embeddings": [embedding], "n_results": n_results, "include": ["documents", "metadatas", "distances"]}
    if where:
        kwargs["where"] = where
    return col.query(**kwargs)


def collection_stats() -> dict:
    col = get_collection()
    count = col.count()
    return {"total_chunks": count, "collection": COLLECTION_NAME, "path": str(CHROMA_PATH)}
