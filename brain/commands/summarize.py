"""
brain/commands/summarize.py
Summarize a single note or an entire folder using retrieval + LLM.
"""

import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from brain.config import VAULT_PATH
from brain import db
from brain.llm import generate
from brain.exceptions import BrainError

console = Console()

# ── Prompts ────────────────────────────────────────────────────────────────

NOTE_SUMMARY_PROMPT = """You are summarizing a personal Obsidian note.

Produce a structured summary with these sections:
**Key Points** — 3-5 bullet points of the most important ideas
**Decisions / Conclusions** — any decisions made or conclusions reached (skip if none)
**Open Questions** — unresolved questions or next steps (skip if none)
**Tags / Themes** — 3-5 thematic keywords

Be concise. Use only what is in the note — do not add outside knowledge.

NOTE CONTENT:
{content}"""

FOLDER_SUMMARY_PROMPT = """You are summarizing a collection of Obsidian notes from the folder: {folder}

Notes provided:
{notes_block}

Produce:
**Overview** — 2-3 sentences describing what this folder is about overall
**Key Themes** — the 3-5 most recurring ideas across all notes
**Notable Notes** — 2-3 standout notes worth reading first, with one line each explaining why
**Connections** — any interesting links or patterns between notes (skip if none)
**Open Threads** — unresolved questions or ideas that appear across notes (skip if none)

Be concise. Only use what is in the notes."""


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_since(since: str) -> float:
    """Convert '24h', '7d', '30d' to a Unix timestamp cutoff."""
    now = time.time()
    since = since.strip().lower()
    if since.endswith("h"):
        try:
            return now - int(since[:-1]) * 3600
        except ValueError:
            pass
    elif since.endswith("d"):
        try:
            return now - int(since[:-1]) * 86400
        except ValueError:
            pass
    elif since.endswith("w"):
        try:
            return now - int(since[:-1]) * 604800
        except ValueError:
            pass
    raise BrainError(
        message=f"Invalid --since value: '{since}'",
        fix="Use formats like: 24h, 7d, 2w, 30d",
    )


def _get_chunks_for_file(file_path: str) -> list:
    """Retrieve all stored chunks for a specific file from ChromaDB."""
    col = db.get_collection()
    results = col.get(
        where={"file_path": file_path},
        include=["documents"],
    )
    return results.get("documents", [])


def _get_chunks_for_folder(folder: str, since_ts: float = 0.0) -> dict:
    """
    Retrieve all chunks for notes inside a folder path prefix.
    Returns dict of {file_path: [chunks]}
    """
    col = db.get_collection()

    # Fetch everything and filter in Python — avoids ChromaDB version issues
    results = col.get(include=["documents", "metadatas"])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])

    folder_prefix = folder.rstrip("/").lower()
    grouped = {}

    for doc, meta in zip(docs, metas):
        fp = meta.get("file_path", "")
        # Match folder prefix (case-insensitive)
        if not fp.lower().startswith(folder_prefix):
            continue
        # Apply since filter if set
        if since_ts > 0:
            modified_at = meta.get("modified_at", 0.0)
            if modified_at < since_ts:
                continue
        grouped.setdefault(fp, []).append(doc)

    return grouped


def _stream_summary(prompt: str, title: str) -> str:
    """Stream LLM summary to terminal, return full text."""
    console.print()
    console.print(Rule(f"[dim]{title}[/dim]", style="dim green"))
    console.print()

    full = ""
    with Live(Markdown(""), console=console, refresh_per_second=15) as live:
        for delta in generate(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        ):
            full += delta
            live.update(Markdown(full))

    console.print()
    return full


def _resolve_note_path(note: str, vault_path: Path) -> str:
    """
    Resolve user-provided note path to a relative vault path.
    Accepts: relative paths, absolute paths, or just note names.
    """
    candidate = Path(note)
    if not candidate.suffix:
        candidate = candidate.with_suffix(".md")

    # Try as-is (relative path from vault root)
    col = db.get_collection()
    results = col.get(where={"file_path": str(candidate)}, include=["metadatas"])
    if results.get("metadatas"):
        return str(candidate)

    # Try stripping vault prefix if absolute path given
    try:
        rel = candidate.relative_to(vault_path)
        results = col.get(where={"file_path": str(rel)}, include=["metadatas"])
        if results.get("metadatas"):
            return str(rel)
    except ValueError:
        pass

    # Fuzzy match by filename stem
    all_results = col.get(include=["metadatas"])
    name = candidate.stem.lower()
    for meta in all_results.get("metadatas", []):
        fp = meta.get("file_path", "")
        if Path(fp).stem.lower() == name:
            return fp

    return str(candidate)


# ── Main entry points ──────────────────────────────────────────────────────

def summarize_note(note: str, vault_path: Path = VAULT_PATH):
    """Summarize a single note."""
    file_path = _resolve_note_path(note, vault_path)

    with console.status(f"[dim]Loading chunks for {file_path}...[/]", spinner="dots"):
        chunks = _get_chunks_for_file(file_path)

    if not chunks:
        console.print(Panel(
            f"[yellow]No indexed content found for:[/] [cyan]{file_path}[/]\n\n"
            f"[dim]Make sure the note exists and has been indexed.\n"
            f"Run: brain ingest[/]",
            border_style="yellow",
        ))
        return

    content = "\n\n".join(chunks)
    note_title = Path(file_path).stem

    console.print(Panel(
        f"[bold]Summarizing:[/] [cyan]{note_title}[/]\n"
        f"[dim]{file_path} · {len(chunks)} chunks[/]",
        border_style="dim",
    ))

    prompt = NOTE_SUMMARY_PROMPT.format(content=content)
    _stream_summary(prompt, title=f"Summary — {note_title}")


def summarize_folder(folder: str, since: str = None, vault_path: Path = VAULT_PATH):
    """Summarize all notes in a folder, optionally filtered by recency."""
    since_ts = 0.0
    since_label = ""

    if since:
        since_ts = _parse_since(since)
        since_label = f" · modified in last {since}"

    with console.status(f"[dim]Loading notes in {folder}...[/]", spinner="dots"):
        grouped = _get_chunks_for_folder(folder, since_ts)

    if not grouped:
        msg = f"No indexed notes found in folder: [cyan]{folder}[/]"
        if since:
            msg += f"\n[dim]with --since {since} filter[/]"
        msg += "\n\n[dim]Check the folder path matches your vault structure.[/]"
        console.print(Panel(msg, border_style="yellow"))
        return

    total_chunks = sum(len(v) for v in grouped.values())
    console.print(Panel(
        f"[bold]Summarizing folder:[/] [cyan]{folder}[/]\n"
        f"[dim]{len(grouped)} notes · {total_chunks} chunks{since_label}[/]",
        border_style="dim",
    ))

    # Show note list
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Note", style="cyan")
    table.add_column("Chunks", style="dim")
    for fp, chunks in sorted(grouped.items()):
        table.add_row(Path(fp).stem, f"{len(chunks)} chunks")
    console.print(table)

    # Build notes block (cap at 3 chunks per note to avoid context overflow)
    notes_block_parts = []
    for fp, chunks in sorted(grouped.items()):
        title = Path(fp).stem
        content = "\n".join(chunks[:3])
        notes_block_parts.append(f"### {title}\n{content}")

    notes_block = "\n\n---\n\n".join(notes_block_parts)
    prompt = FOLDER_SUMMARY_PROMPT.format(folder=folder, notes_block=notes_block)
    _stream_summary(prompt, title=f"Folder Summary — {folder}")
