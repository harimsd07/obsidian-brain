import time
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from brain.config import VAULT_PATH, IGNORE_DIRS, IGNORE_EXTENSIONS
from brain.utils import (
    NoteChunk, file_hash, parse_note, resolve_wikilinks,
    note_title_from_path, relative_path,
)
from brain.chunker import split_sections_into_chunks
from brain.llm import embed_batch
from brain import db

console = Console()

# Simple file → hash cache to skip unchanged files
_hash_cache: dict[str, str] = {}


def _load_hash_cache():
    """Load previously stored hashes from ChromaDB metadata."""
    global _hash_cache
    try:
        col = db.get_collection()
        results = col.get(include=["metadatas"])
        for meta in results.get("metadatas", []):
            if meta and "file_path" in meta and "file_hash" in meta:
                _hash_cache[meta["file_path"]] = meta["file_hash"]
    except Exception:
        pass


def collect_notes(vault_path: Path) -> list[Path]:
    """Walk vault and return all .md files, skipping ignored dirs and extensions."""
    notes = []
    for path in vault_path.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in IGNORE_EXTENSIONS:
            continue
        if path.suffix.lower() == ".md" and path.is_file():
            notes.append(path)
    return sorted(notes)


def ingest_note(path: Path, vault_root: Path, force: bool = False) -> int:
    """
    Ingest a single note into ChromaDB.
    Returns number of chunks upserted (0 if skipped due to no change).
    """
    rel = relative_path(path, vault_root)
    fhash = file_hash(path)

    # Skip if unchanged
    if not force and _hash_cache.get(rel) == fhash:
        return 0

    try:
        _, metadata, sections = parse_note(path, vault_root)
    except Exception as e:
        console.print(f"[yellow]  skip[/] {rel}: parse error — {e}")
        return 0

    chunks_raw = split_sections_into_chunks(sections)
    if not chunks_raw:
        return 0

    title = note_title_from_path(path, vault_root)
    tags = metadata.get("tags", [])
    aliases = metadata.get("aliases", [])
    modified_at = path.stat().st_mtime

    # Build NoteChunk objects
    chunks: list[NoteChunk] = []
    for i, (heading, text) in enumerate(chunks_raw):
        clean_text = resolve_wikilinks(text)
        embed_text = f"Note: {title}\nSection: {heading}\n\n{clean_text}"
        chunks.append(NoteChunk(
            doc_id=f"{rel}::{i}",
            file_path=rel,
            note_title=title,
            heading=heading,
            text=clean_text,
            tags=tags,
            aliases=aliases,
            modified_at=modified_at,
            file_hash=fhash,
        ))

    # Delete old chunks for this file before upserting new ones
    db.delete_by_file(rel)

    # Embed all chunks
    texts_to_embed = [
        f"Note: {c.note_title}\nSection: {c.heading}\n\n{c.text}"
        for c in chunks
    ]
    embeddings = embed_batch(texts_to_embed)

    # Upsert into ChromaDB
    db.upsert_chunks(
        doc_ids=[c.doc_id for c in chunks],
        embeddings=embeddings,
        texts=[c.text for c in chunks],
        metadatas=[{
            "file_path": c.file_path,
            "note_title": c.note_title,
            "heading": c.heading,
            "tags": ",".join(c.tags),
            "aliases": ",".join(c.aliases),
            "modified_at": c.modified_at,
            "file_hash": c.file_hash,
        } for c in chunks],
    )

    _hash_cache[rel] = fhash
    return len(chunks)


def run_full_ingest(vault_path: Path = VAULT_PATH, force: bool = False) -> dict:
    """
    Run full vault ingestion.
    Returns summary stats.
    """
    if not vault_path.exists():
        console.print(f"[red]Vault not found:[/] {vault_path}")
        return {}

    _load_hash_cache()
    notes = collect_notes(vault_path)
    total_notes = len(notes)
    total_chunks = 0
    skipped = 0
    failed = 0

    console.print(f"\n[bold]Obsidian Brain[/] — ingesting [cyan]{total_notes}[/] notes from [dim]{vault_path}[/]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing notes...", total=total_notes)

        for path in notes:
            rel = relative_path(path, vault_path)
            try:
                n = ingest_note(path, vault_path, force=force)
                if n == 0:
                    skipped += 1
                else:
                    total_chunks += n
            except Exception as e:
                console.print(f"[red]  error[/] {rel}: {e}")
                failed += 1
            progress.advance(task)

    stats = db.collection_stats()
    console.print(f"\n[green]Done.[/] {total_notes - skipped - failed} notes indexed · {total_chunks} chunks upserted · {skipped} unchanged · {failed} failed")
    console.print(f"[dim]Total chunks in DB: {stats['total_chunks']}[/]\n")
    return {"notes": total_notes, "chunks": total_chunks, "skipped": skipped, "failed": failed}
