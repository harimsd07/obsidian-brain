import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="brain",
    help="Obsidian Second Brain — chat with your notes locally.",
    add_completion=False,
)
console = Console()


@app.command()
def ingest(
    vault: str = typer.Option(None, "--vault", "-v", help="Override vault path"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-index all notes even if unchanged"),
):
    """Index your entire Obsidian vault into ChromaDB."""
    from brain.ingest import run_full_ingest
    from brain.config import VAULT_PATH

    vault_path = Path(vault).expanduser() if vault else VAULT_PATH
    run_full_ingest(vault_path=vault_path, force=force)


@app.command()
def watch(
    vault: str = typer.Option(None, "--vault", "-v", help="Override vault path"),
):
    """Start the file watcher for incremental re-indexing."""
    from brain.watcher import start_watcher
    from brain.config import VAULT_PATH

    vault_path = Path(vault).expanduser() if vault else VAULT_PATH
    start_watcher(vault_path=vault_path)


@app.command()
def stats():
    """Show vault index statistics."""
    from brain import db
    from brain.llm import check_ollama_models

    s = db.collection_stats()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="cyan")
    table.add_row("Total chunks", str(s["total_chunks"]))
    table.add_row("Collection", s["collection"])
    table.add_row("DB path", s["path"])

    console.print("\n[bold]Index stats[/]")
    console.print(table)

    models = check_ollama_models()
    console.print("\n[bold]Ollama models[/]")
    if models["ok"]:
        console.print(f"  [green]✓[/] All required models available")
    else:
        console.print(f"  [red]✗[/] Missing models: {', '.join(models['missing'])}")
        console.print(f"  Run: [cyan]ollama pull {' '.join(models['missing'])}[/]")

    console.print()


@app.command()
def chat():
    """Start an interactive Q&A session with your notes. (Phase 3 — coming soon)"""
    console.print("\n[yellow]chat[/] command coming in Phase 3. Run [cyan]brain ingest[/] first.\n")


@app.command()
def summarize(
    note: str = typer.Option(None, "--note", "-n", help="Path to a specific note"),
    folder: str = typer.Option(None, "--folder", "-f", help="Folder to summarize"),
):
    """Summarize a note or folder. (Phase 4 — coming soon)"""
    console.print("\n[yellow]summarize[/] command coming in Phase 4.\n")


@app.command()
def related(
    note: str = typer.Argument(..., help="Note path to find related notes for"),
    top: int = typer.Option(5, "--top", "-k", help="Number of related notes to return"),
):
    """Find semantically related notes. (Phase 5 — coming soon)"""
    console.print("\n[yellow]related[/] command coming in Phase 5.\n")


@app.command()
def tag(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Preview or apply tags"),
    note: str = typer.Option(None, "--note", "-n", help="Tag a specific note only"),
):
    """Auto-tag untagged notes using the LLM. (Phase 6 — coming soon)"""
    console.print("\n[yellow]tag[/] command coming in Phase 6.\n")


@app.command()
def digest(
    since: str = typer.Option("24h", "--since", "-s", help="Time window: 24h, 7d, 30d"),
    save: bool = typer.Option(False, "--save", help="Save digest as a new note in vault"),
):
    """Generate a digest of recently modified notes. (Phase 7 — coming soon)"""
    console.print("\n[yellow]digest[/] command coming in Phase 7.\n")


if __name__ == "__main__":
    app()
