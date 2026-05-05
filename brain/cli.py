import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from brain.exceptions import BrainError

app = typer.Typer(
    name="brain",
    help="Obsidian Second Brain — chat with your notes locally.",
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
def chat():
    """Start an interactive Q&A session with your notes."""
    try:
        from brain.commands.chat import run_chat
        from brain import db
        from brain.exceptions import VaultNotIndexed

        stats = db.collection_stats()
        if stats["total_chunks"] == 0:
            raise VaultNotIndexed()
        run_chat()
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


if __name__ == "__main__":
    app()
