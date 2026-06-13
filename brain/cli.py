import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from brain.exceptions import BrainError

app = typer.Typer(
    name="brain",
    help="""
\b
Obsidian Brain — Chat with your notes locally using RAG + LLMs.

QUICK START:
  brain init          First-time setup wizard
  brain ingest        Index your vault
  brain chat          Start chatting with your notes
  brain ask "..."     One-shot question — no REPL needed

EXPLORE:
  brain ask           One-shot Q&A (pipe-friendly with --raw)
  brain summarize     Summarize a note or folder
  brain related       Find semantically related notes
  brain tag           Auto-tag untagged notes
  brain digest        Daily digest of recent notes

MANAGE:
  brain watch         File watcher — auto re-index on save
  brain stats         Index stats + provider health check
  brain history       Browse and search past chat sessions
  brain list-notes    List all indexed notes
""",
    add_completion=False,
    pretty_exceptions_enable=False,   # we handle our own errors
)
console = Console()


def _handle_error(e: BrainError):
    """Print a clean, human-readable error panel — no traceback."""
    lines = f"[red bold]✗[/]  {e.message}"
    if e.fix:
        lines += f"\n\n[dim]{e.fix}[/]"
    console.print(Panel(lines, border_style="red", padding=(0, 2)))
    raise typer.Exit(1)


# --- Version ---
def _version_callback(value: bool):
    if value:
        console.print("obsidian-brain [cyan]0.1.0[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    )
):
    pass


# --- Commands ---

@app.command()
def init():
    """First-time setup wizard — configure vault, provider, and API keys."""
    from brain.commands.init import run_init
    run_init()


@app.command()
def ingest(
    vault: str = typer.Option(None, "--vault", "-v", help="Override vault path"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-index all notes even if unchanged"),
):
    """Index your entire Obsidian vault into ChromaDB."""
    try:
        from brain.ingest import run_full_ingest
        from brain.config import VAULT_PATH
        from brain.exceptions import VaultNotFound

        vault_path = Path(vault).expanduser() if vault else VAULT_PATH
        if not vault_path.exists():
            raise VaultNotFound(str(vault_path))
        run_full_ingest(vault_path=vault_path, force=force)
    except BrainError as e:
        _handle_error(e)


@app.command()
def watch(
    vault: str = typer.Option(None, "--vault", "-v", help="Override vault path"),
):
    """Start the file watcher for incremental re-indexing."""
    try:
        from brain.watcher import start_watcher
        from brain.config import VAULT_PATH
        from brain.exceptions import VaultNotFound

        vault_path = Path(vault).expanduser() if vault else VAULT_PATH
        if not vault_path.exists():
            raise VaultNotFound(str(vault_path))
        start_watcher(vault_path=vault_path)
    except BrainError as e:
        _handle_error(e)


@app.command()
def stats():
    """Show vault index statistics."""
    try:
        from brain import db
        from brain.llm import check_ollama_models
        from brain.config import LLM_PROVIDER, GROQ_API_KEY, GEMINI_API_KEY

        # Index stats
        s = db.collection_stats()
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="dim")
        table.add_column("Value", style="cyan")
        table.add_row("Total chunks", str(s["total_chunks"]))
        table.add_row("Collection", s["collection"])
        table.add_row("DB path", s["path"])
        console.print("\n[bold]Index stats[/]")
        console.print(table)

        # Ollama models
        models = check_ollama_models()
        console.print("\n[bold]Ollama models[/]")
        if models.get("ok"):
            console.print("  [green]✓[/] All required models available")
        else:
            missing = models.get("missing", [])
            if missing:
                console.print(f"  [red]✗[/] Missing: {', '.join(missing)}")
                console.print(f"  Run: [cyan]ollama pull {' '.join(missing)}[/]")
            else:
                err = models.get("error", "unknown error")
                console.print(f"  [yellow]![/] Ollama unreachable — {err}")
                console.print("  Start with: [cyan]ollama serve[/]")

        # Active provider
        console.print("\n[bold]Active LLM provider[/]")
        if LLM_PROVIDER == "groq":
            status = "[green]✓ key set[/]" if GROQ_API_KEY else "[red]✗ GROQ_API_KEY missing[/]"
            console.print(f"  groq  {status}")
        elif LLM_PROVIDER == "gemini":
            status = "[green]✓ key set[/]" if GEMINI_API_KEY else "[red]✗ GEMINI_API_KEY missing[/]"
            console.print(f"  gemini  {status}")
        else:
            console.print("  [cyan]ollama[/]  [dim](local)[/]")

        # Hint if vault not indexed
        if s["total_chunks"] == 0:
            console.print("\n[yellow]![/] Vault not indexed yet. Run: [cyan]brain ingest[/]")

        console.print()

    except BrainError as e:
        _handle_error(e)


@app.command()
def chat(
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume the last session"),
):
    """Start an interactive Q&A session with your notes.

    \b
    Examples:
      brain chat            # start a new session
      brain chat --resume   # continue your last session
    """
    try:
        from brain.commands.chat import run_chat
        from brain import db
        from brain.exceptions import VaultNotIndexed

        stats = db.collection_stats()
        if stats["total_chunks"] == 0:
            raise VaultNotIndexed()
        run_chat(resume=resume)
    except BrainError as e:
        _handle_error(e)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask your notes"),
    top: int = typer.Option(10, "--top", "-k", help="Number of chunks to retrieve (default: 10)"),
    thinking: bool = typer.Option(True, "--thinking/--no-thinking", help="Show reasoning phase"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Plain text output — good for piping to files"),
    hybrid: bool = typer.Option(True, "--hybrid/--semantic-only", help="Use hybrid search (semantic + BM25 keyword)"),
):
    """Ask a single question and get an answer without entering chat mode.

    \b
    Examples:
      brain ask "what is in my outreach folder?"
      brain ask "summarize my agent project" --no-thinking
      brain ask "what is clinic outreach strategy?" --top 15
      brain ask "what are my notes on RAG?" --raw >> notes.md
      brain ask "query" --semantic-only    # Use only semantic search
    """
    try:
        from brain.commands.ask import run_ask
        run_ask(question=question, top_k=top, thinking=thinking, raw=raw, hybrid=hybrid)
    except BrainError as e:
        _handle_error(e)
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/]")


@app.command()
def history(
    search: str = typer.Option(None, "--search", "-s", help="Search sessions by keyword"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of sessions to show"),
    clear: bool = typer.Option(False, "--clear", help="Delete all chat history"),
):
    """Browse and search past chat sessions.

    \b
    Examples:
      brain history                    # list recent sessions
      brain history --search "RAG"     # find sessions mentioning RAG
      brain history --clear            # delete all history
    """
    try:
        from brain.history import list_sessions, search_sessions, clear_all_history
        from rich.table import Table
        from rich import box
        from rich.prompt import Confirm

        if clear:
            if Confirm.ask("[yellow]Delete all chat history?[/]"):
                count = clear_all_history()
                console.print(f"[green]✓[/] Deleted {count} session(s).")
            return

        if search:
            results = search_sessions(search, limit=limit)
            if not results:
                console.print(f"[yellow]No sessions found containing:[/] [cyan]{search}[/]")
                return
            console.print(f"\n[bold]Sessions matching[/] [cyan]{search}[/]\n")
            for r in results:
                role_color = "cyan" if r["role"] == "user" else "dim"
                console.print(
                    f"  [dim]{r['date']}[/]  [{role_color}]{r['role']}[/]  {r['excerpt']}"
                )
            return

        sessions = list_sessions(limit=limit)
        if not sessions:
            console.print("\n[dim]No chat history found.[/]")
            console.print("[dim]Start a session with: brain chat[/]\n")
            return

        console.print(f"\n[bold]Recent sessions[/] [dim]({len(sessions)} shown)[/]\n")
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("Date", style="cyan")
        table.add_column("Questions", width=10, justify="right")
        table.add_column("First question", style="dim")

        for i, s in enumerate(sessions, 1):
            table.add_row(
                str(i),
                s["date"],
                str(s["message_count"]),
                s["first_question"],
            )
        console.print(table)
        console.print(
            "\n[dim]Resume last session:[/] [cyan]brain chat --resume[/]\n"
        )

    except BrainError as e:
        _handle_error(e)


@app.command()
def summarize(
    note: str = typer.Option(None, "--note", "-n", help="Path to a specific note (e.g. Projects/BankPrep.md)"),
    folder: str = typer.Option(None, "--folder", "-f", help="Folder to summarize (e.g. Projects/)"),
    since: str = typer.Option(None, "--since", "-s", help="Filter by recency: 24h, 7d, 30d (folder only)"),
):
    """Summarize a note or an entire folder of notes."""
    try:
        from brain.commands.summarize import summarize_note, summarize_folder
        from brain.config import VAULT_PATH
        from brain.exceptions import VaultNotIndexed
        from brain import db

        if db.collection_stats()["total_chunks"] == 0:
            raise VaultNotIndexed()

        if note:
            summarize_note(note, vault_path=VAULT_PATH)
        elif folder:
            summarize_folder(folder, since=since, vault_path=VAULT_PATH)
        else:
            console.print(
                "\n[yellow]![/] Provide [cyan]--note[/] or [cyan]--folder[/]\n"
                "  Example: [dim]brain summarize --note Projects/BankPrep.md[/]\n"
                "  Example: [dim]brain summarize --folder Projects/[/]\n"
                "  Example: [dim]brain summarize --folder 'Daily Notes/' --since 7d[/]\n"
            )
    except BrainError as e:
        _handle_error(e)


@app.command()
def related(
    note: str = typer.Argument(..., help="Note name or path (e.g. 'Linux/arch-setup' or just 'arch-setup')"),
    top: int = typer.Option(5, "--top", "-k", help="Number of related notes to return"),
):
    """Find semantically related notes for any given note."""
    try:
        from brain.commands.related import find_related
        from brain.config import VAULT_PATH
        from brain.exceptions import VaultNotIndexed
        from brain import db

        if db.collection_stats()["total_chunks"] == 0:
            raise VaultNotIndexed()
        find_related(note, top=top, vault_path=VAULT_PATH)
    except BrainError as e:
        _handle_error(e)


@app.command()
def tag(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Preview tags (dry-run) or write to frontmatter (apply)"),
    note: str = typer.Option(None, "--note", "-n", help="Tag a specific note only"),
):
    """Auto-tag untagged notes using the LLM.

    \b
    Examples:
      brain tag                              # preview tags for all untagged notes
      brain tag --apply                      # write tags to frontmatter
      brain tag --note "Linux/VIm text editor"  # tag a specific note
      brain tag --note "VIm" --apply         # tag and write immediately
    """
    try:
        from brain.commands.tag import run_tag
        from brain.config import VAULT_PATH
        from brain.exceptions import VaultNotIndexed
        from brain import db

        if db.collection_stats()["total_chunks"] == 0:
            raise VaultNotIndexed()
        run_tag(note=note, dry_run=dry_run, vault_path=VAULT_PATH)
    except BrainError as e:
        _handle_error(e)


@app.command()
def digest(
    since: str = typer.Option("24h", "--since", "-s", help="Time window: 24h, 7d, 2w, 30d"),
    save: bool = typer.Option(False, "--save", help="Save digest as a new note in vault"),
):
    """Generate a digest of recently modified notes.

    \b
    Examples:
      brain digest                  # notes from last 24 hours
      brain digest --since 7d       # weekly digest
      brain digest --since 7d --save  # save as new note in vault
    """
    try:
        from brain.commands.digest import run_digest
        from brain.config import VAULT_PATH
        from brain.exceptions import VaultNotIndexed
        from brain import db

        if db.collection_stats()["total_chunks"] == 0:
            raise VaultNotIndexed()
        run_digest(since=since, save=save, vault_path=VAULT_PATH)
    except BrainError as e:
        _handle_error(e)


@app.command(name="list-notes")
def list_notes(
    folder: str = typer.Option(None, "--folder", "-f", help="Filter by folder name"),
    search: str = typer.Option(None, "--search", "-s", help="Filter by note name keyword"),
):
    """List all indexed notes grouped by folder.

    \b
    Examples:
      brain list-notes                          # show everything
      brain list-notes --folder "Linux"         # filter by folder
      brain list-notes --search "agent"         # filter by note name
      brain list-notes --folder "ObsidianForArch" --search "rudratic"
    """
    try:
        from brain import db
        from rich.table import Table
        from rich import box

        col = db.get_collection()
        results = col.get(include=["metadatas"])
        metas = results.get("metadatas", [])

        # Deduplicate by file_path
        seen = {}
        for meta in metas:
            fp = meta.get("file_path", "")
            if fp and fp not in seen:
                seen[fp] = meta

        notes = sorted(seen.keys())

        if not notes:
            console.print(
                "\n[yellow]![/] No notes indexed yet. Run: [cyan]brain ingest[/]\n"
            )
            return

        # Apply filters
        if folder:
            notes = [n for n in notes if folder.lower() in n.lower()]
        if search:
            notes = [n for n in notes if search.lower() in Path(n).stem.lower()]

        if not notes:
            console.print("[yellow]No notes found matching your filters.[/]")
            return

        # Group by top-level folder
        grouped: dict[str, list[str]] = {}
        for fp in notes:
            parts = Path(fp).parts
            top = parts[0] if len(parts) > 1 else "/"
            grouped.setdefault(top, []).append(fp)

        console.print(f"\n[bold]Indexed notes[/] [dim]({len(notes)} total)[/]\n")

        for folder_name, fps in sorted(grouped.items()):
            console.print(
                f"[bold cyan]{folder_name}/[/]  [dim]{len(fps)} note{'s' if len(fps) != 1 else ''}[/]"
            )
            t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
            t.add_column("Note", style="white")
            t.add_column("Path", style="dim")
            for fp in sorted(fps):
                t.add_row(Path(fp).stem, fp)
            console.print(t)

    except BrainError as e:
        _handle_error(e)


if __name__ == "__main__":
    app()
