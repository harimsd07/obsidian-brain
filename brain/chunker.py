import tiktoken
from brain.config import CHUNK_SIZE, CHUNK_OVERLAP

_enc = tiktoken.get_encoding("cl100k_base")


def token_count(text: str) -> int:
    return len(_enc.encode(text))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping token-based chunks.
    Used as fallback when a heading section exceeds chunk_size.
    """
    tokens = _enc.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(_enc.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += chunk_size - overlap

    return chunks


def split_sections_into_chunks(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    Takes (heading, text) pairs and returns (heading, chunk) pairs.
    Sections that fit within chunk_size are kept as-is.
    Sections that exceed chunk_size are split with sliding window.
    """
    result = []
    for heading, text in sections:
        if not text.strip():
            continue
        if token_count(text) <= CHUNK_SIZE:
            result.append((heading, text))
        else:
            for sub_chunk in chunk_text(text):
                result.append((heading, sub_chunk))
    return result
