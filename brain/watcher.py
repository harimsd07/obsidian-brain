import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileDeletedEvent
from rich.console import Console

from brain.config import VAULT_PATH, IGNORE_DIRS, IGNORE_EXTENSIONS
from brain.utils import relative_path
from brain.ingest import ingest_note
from brain import db

console = Console()


class VaultEventHandler(FileSystemEventHandler):
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    def _is_relevant(self, path_str: str) -> bool:
        path = Path(path_str)
        if path.suffix.lower() != ".md":
            return False
        if any(part in IGNORE_DIRS for part in path.parts):
            return False
        if path.suffix.lower() in IGNORE_EXTENSIONS:
            return False
        return True

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and self._is_relevant(event.src_path):
            path = Path(event.src_path)
            rel = relative_path(path, self.vault_path)
            console.print(f"[green]+[/] New note detected: [cyan]{rel}[/]")
            try:
                n = ingest_note(path, self.vault_path, force=True)
                console.print(f"  [dim]→ {n} chunks indexed[/]")
            except Exception as e:
                console.print(f"  [red]Error:[/] {e}")

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and self._is_relevant(event.src_path):
            path = Path(event.src_path)
            rel = relative_path(path, self.vault_path)
            console.print(f"[yellow]~[/] Note changed: [cyan]{rel}[/]")
            try:
                n = ingest_note(path, self.vault_path, force=False)
                if n > 0:
                    console.print(f"  [dim]→ {n} chunks re-indexed[/]")
                else:
                    console.print(f"  [dim]→ unchanged, skipped[/]")
            except Exception as e:
                console.print(f"  [red]Error:[/] {e}")

    def on_deleted(self, event):
        if isinstance(event, FileDeletedEvent) and self._is_relevant(event.src_path):
            path = Path(event.src_path)
            rel = relative_path(path, self.vault_path)
            console.print(f"[red]-[/] Note deleted: [cyan]{rel}[/]")
            try:
                db.delete_by_file(rel)
                console.print(f"  [dim]→ chunks removed from DB[/]")
            except Exception as e:
                console.print(f"  [red]Error:[/] {e}")


def start_watcher(vault_path: Path = VAULT_PATH):
    """Start the file watcher. Blocks until KeyboardInterrupt."""
    if not vault_path.exists():
        console.print(f"[red]Vault not found:[/] {vault_path}")
        return

    handler = VaultEventHandler(vault_path)
    observer = Observer()
    observer.schedule(handler, str(vault_path), recursive=True)
    observer.start()

    console.print(f"\n[bold]Brain watcher running[/] — watching [dim]{vault_path}[/]")
    console.print("[dim]Press Ctrl+C to stop.[/]\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[dim]Watcher stopped.[/]")
    observer.join()
