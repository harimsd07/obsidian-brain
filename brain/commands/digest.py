"""
brain/commands/digest.py
Generate a digest of recently modified notes.
"""

import time
from datetime import datetime
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

DIGEST_PROMPT = """You are summarizing a person's recent note-taking activity to help them reflect on what they've been working on.

Notes modified recently:
{notes_block}

Write a short, friendly digest with these sections:

**What you worked on**
2-3 sentences covering the main topics and themes across all notes.

**Key ideas captured**
3-5 bullet points of the most interesting or important ideas found across the notes.

**Threads to pick up**
2-3 things that seem unfinished, have open questions, or might be worth revisiting.

Keep it concise, warm, and useful — like a smart assistant summarizing your day.
Do not just list note titles. Synthesize the content."""


def _parse_since(since: str) -> tuple:
    """
    Parse since string into (timestamp, label).
    Returns (cutoff_timestamp, human_label).
    """
    now = time.time()
    since = since.strip().lower()
    try:
        if since.endswith("h"):
            n = int(since[:-1])
            return now - n * 3600, f"last {n} hour{'s' if n > 1 else ''}"
        elif since.endswith("d"):
            n = int(since[:-1])
            return now - n * 86400, f"last {n} day{'s' if n > 1 else ''}"
        elif since.endswith("w"):
            n = int(since[:-1])
            return now - n * 604800, f"last {n} week{'s' if n > 1 else ''}"
    except ValueError:
        pass
    raise BrainError(
        message=f"Invalid --since value: '{since}'",
        fix="Use formats like: 24h, 7d, 2w, 30d",
    )


def _get_recent_notes(since_ts: float) -> dict:
    """
    Fetch notes modified after since_ts.
    Returns dict of {file_path: {"chunks": [], "modified_at": float}}
    """
    col = db.get_collection()
    results = col.get(include=["documents", "metadatas"])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])

    grouped = {}
    for doc, meta in zip(docs, metas):
        fp = meta.get("file_path", "")
        modified_at = meta.get("modified_at", 0.0)
        if not fp or modified_at < since_ts:
            continue
        if fp not in grouped:
            grouped[fp] = {"chunks": [], "modified_at": modified_at}
        grouped[fp]["chunks"].append(doc)

    return grouped


def _build_notes_block(grouped: dict, max_notes: int = 15) -> str:
    """Build the notes block for the LLM prompt."""
    # Sort by most recently modified first
    sorted_notes = sorted(
        grouped.items(),
        key=lambda x: x[1]["modified_at"],
        reverse=True,
    )[:max_notes]

    parts = []
    total_chars = 0
    MAX_CHARS = 6000  # safe for all providers

    for fp, data in sorted_notes:
        title = Path(fp).stem
        content = "\n".join(data["chunks"][:2])  # first 2 chunks per note
        modified = datetime.fromtimestamp(data["modified_at"]).strftime("%Y-%m-%d %H:%M")
        entry = f"### {title}\n_Modified: {modified}_\n\n{content}"

        if total_chars + len(entry) > MAX_CHARS:
            parts.append(f"### {title}\n_Modified: {modified}_\n[content truncated]")
            break

        parts.append(entry)
        total_chars += len(entry)

    return "\n\n---\n\n".join(parts)


def _save_digest(digest_text: str, since_label: str, vault_path: Path) -> Path:
    """Save digest as a new note in the vault."""
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"Digest-{today}.md"

    # Save to a Digests folder in vault root
    digest_dir = vault_path / "Digests"
    digest_dir.mkdir(exist_ok=True)
    output_path = digest_dir / filename

    note_content = (
        f"---\n"
        f"tags: [digest, auto-generated]\n"
        f"date: {today}\n"
        f"period: {since_label}\n"
        f"---\n\n"
        f"# Brain Digest — {today}\n\n"
        f"_{since_label.capitalize()} summary_\n\n"
        f"{digest_text}\n"
    )

    output_path.write_text(note_content, encoding="utf-8")
    return output_path


def run_digest(since: str = "24h", save: bool = False, vault_path: Path = VAULT_PATH):
    """Main entry point for brain digest command."""

    # Parse time window
    since_ts, since_label = _parse_since(since)

    # Fetch recent notes
    with console.status(f"[dim]Finding notes from {since_label}...[/]", spinner="dots"):
        grouped = _get_recent_notes(since_ts)

    if not grouped:
        console.print(Panel(
            f"[yellow]No notes modified in the {since_label}.[/]\n\n"
            f"[dim]Try a wider window:  brain digest --since 7d[/]",
            border_style="yellow",
        ))
        return

    # Show what was found
    sorted_notes = sorted(
        grouped.items(),
        key=lambda x: x[1]["modified_at"],
        reverse=True,
    )

    console.print(Panel(
        f"[bold]Brain Digest[/] — {since_label}\n"
        f"[dim]{len(grouped)} notes modified[/]",
        border_style="dim",
    ))

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Note", style="cyan")
    table.add_column("Modified", style="dim")
    table.add_column("Chunks", style="dim", justify="right")

    for fp, data in sorted_notes[:10]:
        modified = datetime.fromtimestamp(data["modified_at"]).strftime("%Y-%m-%d %H:%M")
        table.add_row(Path(fp).stem, modified, str(len(data["chunks"])))

    if len(sorted_notes) > 10:
        table.add_row(f"[dim]...and {len(sorted_notes) - 10} more[/]", "", "")

    console.print(table)

    # Build prompt and generate digest
    notes_block = _build_notes_block(grouped)
    prompt = DIGEST_PROMPT.format(notes_block=notes_block)

    console.print()
    console.print(Rule("[dim]digest[/dim]", style="dim green"))
    console.print()

    full_digest = ""
    with Live(Markdown(""), console=console, refresh_per_second=15) as live:
        for delta in generate(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        ):
            full_digest += delta
            live.update(Markdown(full_digest))

    console.print()

    # Save if requested
    if save:
        saved_path = _save_digest(full_digest, since_label, vault_path)
        console.print(Panel(
            f"[green]✓[/] Digest saved to vault:\n[cyan]{saved_path}[/]\n\n"
            f"[dim]Run brain ingest to index it.[/]",
            border_style="green",
        ))
