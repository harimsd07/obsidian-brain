"""
brain ask — one-shot Q&A against your Obsidian vault.
Runs a single query, prints the answer, and exits.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from brain import db
from brain.config import LLM_MODEL, EMBED_MODEL, LLM_PROVIDER, VAULT_PATH
from brain.exceptions import BrainError, VaultNotIndexed
from brain.llm import generate
from brain.retriever import retrieve, build_context

console = Console()

# ──────────────────────────────────────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a knowledgeable assistant with access to the user's personal Obsidian notes.
Answer the user's question using ONLY the notes provided. Be specific and cite which note each fact comes from.
If the notes do not contain enough information, say so clearly — do not hallucinate.
Keep your answer concise and well-structured."""

SYSTEM_PROMPT_THINKING = """You are a knowledgeable assistant with access to the user's personal Obsidian notes.
First, reason through which notes are most relevant and how to best answer the question.
Wrap your thinking in <think>...</think> tags.
Then give a clear, concise answer using ONLY the information from those notes.
Cite which note each fact comes from. If the notes do not contain enough information, say so."""


# ──────────────────────────────────────────────────────────────────────────────
# Core ask function
# ──────────────────────────────────────────────────────────────────────────────

def run_ask(
    question: str,
    top_k: int = 10,
    thinking: bool = True,
    raw: bool = False,
    hybrid: bool = True,
) -> None:
    """
    Ask a single question and stream the answer to stdout.

    Args:
        question:  The question to ask.
        top_k:     Number of chunks to retrieve as context.
        thinking:  Whether to show the thinking phase.
        raw:       If True, print plain text only (no Rich formatting). Useful for piping.
        hybrid:    If True, use hybrid search (semantic + BM25). If False, use semantic only.
    """
    stats = db.collection_stats()
    if stats["total_chunks"] == 0:
        raise VaultNotIndexed()

    # ── Retrieve relevant chunks ──────────────────────────────────────────────
    if not raw:
        with console.status("[dim]Searching vault...[/]", spinner="dots"):
            chunks = retrieve(question, top_k=top_k, hybrid=hybrid)
    else:
        chunks = retrieve(question, top_k=top_k, hybrid=hybrid)

    if not chunks:
        if raw:
            print("No relevant notes found for your question.")
        else:
            console.print("\n[yellow]No relevant notes found.[/] Try rephrasing or increasing --top.\n")
        return

    context = build_context(chunks)
    sources = list(dict.fromkeys(
        f"{c.note_title} ({c.file_path})" for c in chunks
    ))

    system = SYSTEM_PROMPT_THINKING if thinking else SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Here are my Obsidian notes:\n\n{context}\n\n"
                f"Question: {question}"
            ),
        },
    ]

    # ── Stream response ───────────────────────────────────────────────────────
    if raw:
        _stream_raw(messages, thinking)
    else:
        _stream_rich(messages, thinking, sources, question, top_k)


# ──────────────────────────────────────────────────────────────────────────────
# Output renderers
# ──────────────────────────────────────────────────────────────────────────────

def _stream_rich(
    messages: list[dict],
    thinking: bool,
    sources: list[str],
    question: str,
    top_k: int,
) -> None:
    """Render answer with Rich panels — for interactive terminal use."""

    header = (
        f"[dim]Provider:[/] [cyan]{LLM_PROVIDER}[/]  "
        f"[dim]Top-K:[/] [cyan]{top_k}[/]"
    )
    console.print()
    console.rule(f"[bold]brain ask[/]  [dim]{question[:60]}{'...' if len(question) > 60 else ''}[/]")
    console.print()

    buffer = ""
    in_think = False
    think_buf = ""
    answer_buf = ""
    think_done = False

    if thinking:
        think_text = Text("", style="dim yellow")
        think_panel = Panel(think_text, title="[yellow]thinking[/]", border_style="yellow", padding=(0, 1))

        with Live(think_panel, console=console, refresh_per_second=12) as live:
            for delta in generate(messages, stream=True):
                buffer += delta

                if not think_done:
                    if "<think>" in buffer and not in_think:
                        in_think = True
                        buffer = buffer.split("<think>", 1)[1]

                    if in_think:
                        if "</think>" in buffer:
                            think_part, rest = buffer.split("</think>", 1)
                            think_buf += think_part
                            buffer = rest
                            in_think = False
                            think_done = True
                            think_text.plain = think_buf.strip()
                            live.update(Panel(
                                think_text,
                                title="[yellow]thinking[/]",
                                border_style="yellow",
                                padding=(0, 1),
                            ))
                        else:
                            think_buf = buffer
                            think_text.plain = think_buf.strip()
                            live.update(Panel(
                                think_text,
                                title="[yellow]thinking[/]",
                                border_style="yellow",
                                padding=(0, 1),
                            ))
                    else:
                        answer_buf += delta
                else:
                    answer_buf += delta

        console.print()
    else:
        # No thinking — collect full answer first for cleaner panel display
        for delta in generate(messages, stream=True):
            # Strip any accidental think tags
            if "<think>" in delta or "</think>" in delta:
                continue
            answer_buf += delta

    # ── Print answer ──────────────────────────────────────────────────────────
    clean_answer = answer_buf.strip()
    # Remove any leftover think tags
    if "<think>" in clean_answer:
        parts = clean_answer.split("<think>")
        cleaned = parts[0]
        for part in parts[1:]:
            if "</think>" in part:
                cleaned += part.split("</think>", 1)[1]
        clean_answer = cleaned.strip()

    console.print(Panel(
        clean_answer,
        title="[green]answer[/]",
        border_style="green",
        padding=(1, 2),
    ))

    # ── Print sources ─────────────────────────────────────────────────────────
    if sources:
        console.print("\n[dim]Sources:[/]")
        for s in sources[:5]:
            console.print(f"  [dim]•[/] {s}")
        if len(sources) > 5:
            console.print(f"  [dim]...and {len(sources) - 5} more[/]")
    console.print()


def _stream_raw(messages: list[dict], thinking: bool) -> None:
    """Print plain text — for piping to files or other commands."""
    buffer = ""
    in_think = False
    think_done = not thinking

    for delta in generate(messages, stream=True):
        buffer += delta

        if not think_done:
            if "<think>" in buffer and not in_think:
                in_think = True
                buffer = buffer.split("<think>", 1)[1]
                continue

            if in_think:
                if "</think>" in buffer:
                    _, rest = buffer.split("</think>", 1)
                    buffer = rest
                    in_think = False
                    think_done = True
                    print(buffer, end="", flush=True)
                # else: still in think block, suppress
            else:
                print(delta, end="", flush=True)
        else:
            # Clean stray think tags
            if "<think>" not in delta and "</think>" not in delta:
                print(delta, end="", flush=True)

    print()  # trailing newline
