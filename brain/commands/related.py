"""
brain/commands/related.py
Find semantically related notes for any given note.
"""

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from brain.config import VAULT_PATH, TOP_K
from brain import db
from brain.llm import embed
from brain.exceptions import BrainError

console = Console()


def _get_all_chunks_for_file(file_path: str) -> list:
    """Get all stored chunks for a specific note — Python-side filter."""
    col = db.get_collection()
    results = col.get(include=["documents", "metadatas"])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    return [
        doc for doc, meta in zip(docs, metas)
        if meta.get("file_path", "") == file_path
    ]


def _resolve_note_path(note: str, vault_path: Path) -> str:
    """
    Resolve note name/path to the indexed file_path.
    Tries: exact → with .md → partial path match → stem fuzzy match.
    """
    candidate = Path(note)
    if not candidate.suffix:
        candidate = candidate.with_suffix(".md")

    col = db.get_collection()
    all_results = col.get(include=["metadatas"])
    all_fps = [m.get("file_path", "") for m in all_results.get("metadatas", [])]
    unique_fps = sorted(set(all_fps))

    note_str = str(candidate)
    note_lower = note_str.lower()

    # 1. Exact match
    if note_str in unique_fps:
        return note_str

    # 2. Case-insensitive exact match
    for fp in unique_fps:
        if fp.lower() == note_lower:
            return fp

    # 3. Partial path match — note string appears anywhere in the path
    matches = [fp for fp in unique_fps if note_lower in fp.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer shortest path (most specific match)
        return sorted(matches, key=len)[0]

    # 4. Stem-only fuzzy match
    stem = candidate.stem.lower()
    stem_matches = [fp for fp in unique_fps if Path(fp).stem.lower() == stem]
    if stem_matches:
        return stem_matches[0]

    return str(candidate)


def _representative_embedding(chunks: list) -> list:
    """
    Generate a single representative embedding for a note.
    Uses the first 3 chunks joined — captures the note's main ideas
    without exceeding embedding context limits.
    """
    representative_text = "\n\n".join(chunks[:3])
    return embed(representative_text)


def _score_color(score: float) -> str:
    """Return a rich color based on similarity score (lower = more similar)."""
    if score < 0.2:
        return "green"
    elif score < 0.4:
        return "yellow"
    else:
        return "dim"


def find_related(note: str, top: int = TOP_K, vault_path: Path = VAULT_PATH):
    """Find semantically related notes for a given note."""

    file_path = _resolve_note_path(note, vault_path)

    # Load source note chunks
    with console.status(f"[dim]Loading {file_path}...[/]", spinner="dots"):
        chunks = _get_all_chunks_for_file(file_path)

    if not chunks:
        console.print(Panel(
            f"[yellow]No indexed content found for:[/] [cyan]{file_path}[/]\n\n"
            f"[dim]Make sure the note exists and has been indexed.\n"
            f"Run: brain ingest[/]",
            border_style="yellow",
        ))
        return

    note_title = Path(file_path).stem

    console.print(Panel(
        f"[bold]Finding notes related to:[/] [cyan]{note_title}[/]\n"
        f"[dim]{file_path} · {len(chunks)} chunks · top {top} results[/]",
        border_style="dim",
    ))

    # Embed the source note
    with console.status("[dim]Embedding source note...[/]", spinner="dots"):
        query_embedding = _representative_embedding(chunks)

    # Query ChromaDB — fetch more than needed to filter out self-matches
    with console.status("[dim]Searching vault...[/]", spinner="dots"):
        results = db.query(query_embedding, n_results=min(top * 4, 50))

    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    # Group by note, exclude the source note itself
    seen_notes: dict[str, dict] = {}
    for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
        fp = meta.get("file_path", "")
        if fp == file_path:
            continue  # skip self
        if fp in seen_notes:
            # Keep the best (lowest distance) chunk per note
            if dist < seen_notes[fp]["score"]:
                seen_notes[fp]["score"] = dist
                seen_notes[fp]["excerpt"] = doc
        else:
            seen_notes[fp] = {
                "title": meta.get("note_title", Path(fp).stem),
                "score": dist,
                "excerpt": doc,
                "heading": meta.get("heading", ""),
            }

    if not seen_notes:
        console.print("[yellow]No related notes found.[/]")
        return

    # Sort by score and take top N
    ranked = sorted(seen_notes.items(), key=lambda x: x[1]["score"])[:top]

    # Display results table
    console.print()
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold dim",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Note", style="bold")
    table.add_column("Path", style="dim")
    table.add_column("Score", justify="right", width=7)

    for i, (fp, info) in enumerate(ranked, 1):
        color = _score_color(info["score"])
        score_str = f"[{color}]{info['score']:.3f}[/]"
        table.add_row(
            str(i),
            info["title"],
            fp,
            score_str,
        )

    console.print(table)

    # Show excerpts for top 3
    console.print("\n[bold dim]Top match excerpts:[/]\n")
    for i, (fp, info) in enumerate(ranked[:3], 1):
        excerpt = info["excerpt"][:200].strip()
        if len(info["excerpt"]) > 200:
            excerpt += "..."
        heading = f" › {info['heading']}" if info["heading"] and info["heading"] != "__intro__" else ""
        console.print(
            f"[cyan]{i}. {info['title']}[/][dim]{heading}[/]\n"
            f"   [dim]{excerpt}[/]\n"
        )

    console.print(
        f"[dim]Similarity score: lower = more related · "
        f"[green]< 0.2 strong[/] · [yellow]0.2–0.4 moderate[/] · dim = weak[/]\n"
    )
