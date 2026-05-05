"""
brain/commands/tag.py
Auto-tag untagged notes using LLM + similar note context.
"""

import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box
import frontmatter

from brain.config import VAULT_PATH
from brain import db
from brain.llm import generate
from brain.retriever import retrieve
from brain.exceptions import BrainError

console = Console()

TAG_PROMPT = """You are a note tagging assistant. Your job is to suggest concise, useful tags for an Obsidian note.

Rules:
- Suggest exactly 3-5 tags
- Tags must be lowercase, no spaces (use hyphens for multi-word: e.g. arch-linux)
- Tags should reflect the main topic, tools, concepts, and context of the note
- Look at the related notes tags for inspiration — use consistent tags where relevant
- Return ONLY a YAML list of tags, nothing else. No explanation, no preamble.

Example output:
- arch-linux
- package-manager
- terminal
- system-config

NOTE TITLE: {title}

NOTE CONTENT:
{content}

RELATED NOTES AND THEIR TAGS:
{related_tags}

Return ONLY the YAML list:"""


def _get_untagged_notes(vault_path: Path) -> list:
    """
    Scan vault for .md files with no tags in frontmatter.
    Returns list of (file_path_str, absolute_path) tuples.
    """
    col = db.get_collection()
    results = col.get(include=["metadatas"])
    metas = results.get("metadatas", [])

    # Get indexed notes with no tags
    seen = {}
    for meta in metas:
        fp = meta.get("file_path", "")
        tags = meta.get("tags", "")
        if fp and fp not in seen:
            seen[fp] = tags.strip() if tags else ""

    untagged = []
    for fp, tags in seen.items():
        if not tags:  # empty tags string means no tags
            abs_path = vault_path / fp
            if abs_path.exists():
                untagged.append((fp, abs_path))

    return sorted(untagged)


def _get_chunks_for_file(file_path: str) -> list:
    """Python-side filter for chunks of a specific note."""
    col = db.get_collection()
    results = col.get(include=["documents", "metadatas"])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    return [
        doc for doc, meta in zip(docs, metas)
        if meta.get("file_path", "") == file_path
    ]


def _get_related_tags(file_path: str, content: str) -> str:
    """
    Retrieve similar notes and their existing tags for context.
    Returns formatted string of related note titles + tags.
    """
    try:
        chunks = retrieve(content[:500], n=5)
        lines = []
        for chunk in chunks:
            if chunk.file_path == file_path:
                continue
            col = db.get_collection()
            results = col.get(
                include=["metadatas"],
            )
            metas = results.get("metadatas", [])
            tags = ""
            for meta in metas:
                if meta.get("file_path") == chunk.file_path:
                    tags = meta.get("tags", "")
                    break
            if tags:
                lines.append(f"- {chunk.note_title}: [{tags}]")
        return "\n".join(lines) if lines else "No related tagged notes found."
    except Exception:
        return "Could not retrieve related notes."


def _parse_tags(llm_output: str) -> list:
    """
    Parse LLM YAML list output into a clean list of tags.
    Handles variations in LLM output format.
    """
    tags = []
    for line in llm_output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip YAML list marker
        line = re.sub(r"^[-*]\s*", "", line)
        # Strip quotes
        line = line.strip("\"'`")
        # Lowercase, replace spaces with hyphens
        line = line.lower().replace(" ", "-")
        # Remove any non-alphanumeric except hyphens
        line = re.sub(r"[^a-z0-9\-]", "", line)
        if line:
            tags.append(line)
    return tags[:5]  # cap at 5


def _write_tags_to_note(abs_path: Path, tags: list) -> bool:
    """Write tags into note frontmatter. Returns True on success."""
    try:
        post = frontmatter.load(str(abs_path))
        post["tags"] = tags
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))
        return True
    except Exception as e:
        console.print(f"  [red]Failed to write tags:[/] {e}")
        return False


def _suggest_tags_for_note(file_path: str, abs_path: Path) -> list:
    """Generate tag suggestions for a single note using LLM."""
    chunks = _get_chunks_for_file(file_path)
    if not chunks:
        return []

    content = "\n\n".join(chunks[:3])
    title = Path(file_path).stem
    related_tags = _get_related_tags(file_path, content)

    prompt = TAG_PROMPT.format(
        title=title,
        content=content[:2000],  # cap content to avoid token limits
        related_tags=related_tags,
    )

    full_response = ""
    for delta in generate(
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    ):
        full_response += delta if isinstance(delta, str) else ""

    # generate() with stream=False returns a string via the generator
    if not full_response:
        # Fallback: collect from stream
        for delta in generate(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        ):
            full_response += delta

    return _parse_tags(full_response)


def run_tag(
    note: str = None,
    dry_run: bool = True,
    vault_path: Path = VAULT_PATH,
):
    """Main entry point for brain tag command."""

    if note:
        # Tag a specific note
        _run_tag_single(note, dry_run, vault_path)
    else:
        # Tag all untagged notes
        _run_tag_all(dry_run, vault_path)


def _run_tag_single(note: str, dry_run: bool, vault_path: Path):
    """Tag a single specific note."""
    # Resolve path
    candidate = Path(note)
    if not candidate.suffix:
        candidate = candidate.with_suffix(".md")

    col = db.get_collection()
    all_results = col.get(include=["metadatas"])
    all_fps = sorted(set(
        m.get("file_path", "") for m in all_results.get("metadatas", [])
    ))

    note_lower = str(candidate).lower()
    file_path = None

    # Match by partial path or stem
    for fp in all_fps:
        if note_lower in fp.lower() or Path(fp).stem.lower() == candidate.stem.lower():
            file_path = fp
            break

    if not file_path:
        console.print(Panel(
            f"[yellow]Note not found in index:[/] [cyan]{note}[/]\n"
            f"[dim]Run: brain list-notes --search \"{note}\" to find it[/]",
            border_style="yellow",
        ))
        return

    abs_path = vault_path / file_path
    title = Path(file_path).stem

    mode = "[yellow]DRY RUN[/]" if dry_run else "[green]APPLY[/]"
    console.print(Panel(
        f"[bold]Tagging:[/] [cyan]{title}[/]  {mode}\n"
        f"[dim]{file_path}[/]",
        border_style="dim",
    ))

    with console.status("[dim]Generating tags...[/]", spinner="dots"):
        tags = _suggest_tags_for_note(file_path, abs_path)

    if not tags:
        console.print("[yellow]Could not generate tags for this note.[/]")
        return

    console.print(f"\n  Suggested tags: ", end="")
    console.print("  ".join(f"[cyan]#{t}[/]" for t in tags))

    if not dry_run:
        if _write_tags_to_note(abs_path, tags):
            console.print(f"  [green]✓[/] Tags written to frontmatter")
    else:
        console.print(f"\n  [dim]Run with --apply to write these tags to the note.[/]")


def _run_tag_all(dry_run: bool, vault_path: Path):
    """Tag all untagged notes in the vault."""

    with console.status("[dim]Scanning for untagged notes...[/]", spinner="dots"):
        untagged = _get_untagged_notes(vault_path)

    if not untagged:
        console.print(Panel(
            "[green]✓[/] All indexed notes already have tags!",
            border_style="green",
        ))
        return

    mode = "[yellow]DRY RUN[/]" if dry_run else "[green]APPLY[/]"
    console.print(Panel(
        f"[bold]Auto-tagging untagged notes[/]  {mode}\n"
        f"[dim]{len(untagged)} notes without tags[/]",
        border_style="dim",
    ))

    # Preview table
    results_table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold dim",
        padding=(0, 1),
    )
    results_table.add_column("Note", style="cyan")
    results_table.add_column("Suggested Tags")
    results_table.add_column("Status", justify="right", width=10)

    success = 0
    failed = 0

    for i, (file_path, abs_path) in enumerate(untagged, 1):
        title = Path(file_path).stem
        console.print(
            f"[dim]({i}/{len(untagged)})[/] Processing [cyan]{title}[/]...",
            end="\r"
        )

        try:
            tags = _suggest_tags_for_note(file_path, abs_path)
            if not tags:
                results_table.add_row(title, "[dim]no tags generated[/]", "[yellow]skip[/]")
                failed += 1
                continue

            tags_display = "  ".join(f"#{t}" for t in tags)

            if dry_run:
                results_table.add_row(title, tags_display, "[yellow]preview[/]")
            else:
                wrote = _write_tags_to_note(abs_path, tags)
                status = "[green]✓ done[/]" if wrote else "[red]✗ failed[/]"
                results_table.add_row(title, tags_display, status)
                if wrote:
                    success += 1
                else:
                    failed += 1

        except Exception as e:
            results_table.add_row(title, f"[red]error: {e}[/]", "[red]✗[/]")
            failed += 1

    console.print(" " * 60, end="\r")  # clear progress line
    console.print()
    console.print(results_table)
    console.print(Rule(style="dim"))

    if dry_run:
        console.print(
            f"\n[dim]Previewed {len(untagged)} notes. "
            f"Run with [cyan]--apply[/] to write tags to frontmatter.[/]\n"
        )
    else:
        console.print(
            f"\n[green]✓[/] {success} notes tagged  "
            f"[dim]{failed} skipped/failed[/]\n"
        )
