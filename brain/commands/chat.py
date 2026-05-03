import re
import time
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown

from brain.llm import generate
from brain.config import LLM_PROVIDER

from brain.retriever import retrieve, build_context, format_sources
from brain.config import TOP_K, LLM_MODEL, EMBED_MODEL

console = Console()

SYSTEM_PROMPT = """You are a second brain assistant. Your job is to answer questions using ONLY the notes provided in the context below.

Before giving your final answer, think step by step inside <think>...</think> tags. Use this space to:
- Identify which notes are most relevant
- Reason through any connections between notes
- Plan what to include in your answer

After </think>, write your final answer clearly.

Rules:
- Answer only from the provided context. Do not use outside knowledge.
- If the context doesn't contain enough information, say so clearly.
- Always cite which note(s) your answer comes from using [Note Title] inline.
- Be concise but complete. Use bullet points for lists."""

HELP_TEXT = """
[bold]Commands:[/]
  [cyan]/sources[/]     Show sources from the last answer
  [cyan]/thinking[/]    Toggle thinking phase on/off (default: on)
  [cyan]/clear[/]       Clear conversation history
  [cyan]/top N[/]       Change number of chunks retrieved (default: 5)
  [cyan]/model[/]       Show current models
  [cyan]/help[/]        Show this help
  [cyan]/exit[/]        Quit

[dim]Just type your question and press Enter.[/]
"""


def build_messages(question: str, context: str, history: list[dict]) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-8:]:
        messages.append(msg)
    messages.append({"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"})
    return messages


def stream_with_thinking(messages: list[dict]) -> tuple[str, str]:
    """
    Stream LLM response, separating <think>...</think> from the final answer.
    Returns (thinking_text, answer_text).
    """
    full_text = ""
    thinking_buf = ""
    answer_buf = ""
    in_think = False
    think_done = False

    # Live display for thinking panel
    think_live_text = Text()
    answer_live_text = Text()

    console.print()
    console.print(Rule("[dim]thinking[/dim]", style="dim yellow"))

    with Live(Panel(Text(""), border_style="yellow dim", padding=(0, 1)),
              console=console, refresh_per_second=15) as live:

        for delta in generate(messages, stream=True):
            if not delta:
                continue
            full_text += delta

            if not think_done:
                thinking_buf += delta

                # Detect end of thinking block
                if "</think>" in thinking_buf:
                    think_done = True
                    parts = thinking_buf.split("</think>", 1)
                    clean_think = parts[0].replace("<think>", "").strip()
                    answer_buf = parts[1] if len(parts) > 1 else ""
                    live.update(Panel(
                        Markdown(clean_think),
                        title="[yellow]thinking[/yellow]",
                        border_style="yellow dim",
                        padding=(0, 1)
                    ))
                else:
                    # Still accumulating think block — show live
                    display = thinking_buf.replace("<think>", "").strip()
                    live.update(Panel(
                        Text(display, style="dim"),
                        title="[yellow]thinking[/yellow]",
                        border_style="yellow dim",
                        padding=(0, 1)
                    ))
            else:
                answer_buf += delta

    # Extract clean thinking text
    think_match = re.search(r"<think>(.*?)</think>", full_text, re.DOTALL)
    thinking_text = think_match.group(1).strip() if think_match else ""
    answer_text = re.sub(r"<think>.*?</think>", "", full_text, flags=re.DOTALL).strip()

    # Stream final answer
    console.print()
    console.print(Rule("[dim]answer[/dim]", style="dim green"))
    console.print()

    with Live(Markdown(""), console=console, refresh_per_second=15) as live:
        displayed = ""
        # Simulate streaming the already-buffered answer for smooth display
        for i in range(0, len(answer_text), 8):
            displayed = answer_text[: i + 8]
            live.update(Markdown(displayed))
            time.sleep(0.01)
        live.update(Markdown(answer_text))

    console.print()
    return thinking_text, answer_text


def stream_answer_only(messages: list[dict]) -> str:
    """Stream response without thinking phase (when thinking is toggled off)."""
    full_response = ""
    console.print()
    console.print(Rule("[dim]answer[/dim]", style="dim green"))
    console.print()

    with Live(Markdown(""), console=console, refresh_per_second=15) as live:
        for delta in generate(messages, stream=True):
            if delta:
                full_response += delta
                live.update(Markdown(full_response))

    console.print()
    return full_response


def run_chat():
    """Main chat REPL loop."""
    console.print(Panel(
        f"[bold]Obsidian Brain — Chat[/]\n"
        f"[dim]LLM:[/] [cyan]{LLM_MODEL}[/]  "
        f"[dim]Embed:[/] [cyan]{EMBED_MODEL}[/]  "
        f"[dim]Top-K:[/] [cyan]{TOP_K}[/]  "
        f"[dim]Thinking:[/] [green]on[/]\n\n"
        f"Type your question or [cyan]/help[/] for commands. [cyan]/exit[/] to quit.",
        border_style="dim"
    ))

    history: list[dict] = []
    last_sources: list[str] = []
    top_k = TOP_K
    thinking_enabled = True

    while True:
        try:
            console.print()
            query = console.input("[bold cyan]you[/] › ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye.[/]")
            break

        if not query:
            continue

        # --- Commands ---
        if query == "/exit":
            console.print("[dim]Bye.[/]")
            break

        if query == "/help":
            console.print(HELP_TEXT)
            continue

        if query == "/clear":
            history.clear()
            last_sources.clear()
            console.print("[dim]Conversation cleared.[/]")
            continue

        if query == "/sources":
            if last_sources:
                console.print("\n[bold]Sources from last answer:[/]")
                for s in last_sources:
                    console.print(f"  • {s}")
            else:
                console.print("[dim]No sources yet — ask a question first.[/]")
            continue

        if query == "/thinking":
            thinking_enabled = not thinking_enabled
            state = "[green]on[/]" if thinking_enabled else "[red]off[/]"
            console.print(f"[dim]Thinking phase:[/] {state}")
            continue

        if query == "/model":
            state = "[green]on[/]" if thinking_enabled else "[red]off[/]"
            console.print(f"  LLM: [cyan]{LLM_MODEL}[/]  Embed: [cyan]{EMBED_MODEL}[/]  Top-K: [cyan]{top_k}[/]  Thinking: {state}")
            continue

        if query.startswith("/top "):
            try:
                top_k = int(query.split()[1])
                console.print(f"[dim]Top-K set to {top_k}[/]")
            except (IndexError, ValueError):
                console.print("[red]Usage: /top 5[/]")
            continue

        if query.startswith("/"):
            console.print(f"[red]Unknown command.[/] Type [cyan]/help[/] for options.")
            continue

        # --- Retrieval ---
        with console.status("[dim]Searching your notes...[/]", spinner="dots"):
            chunks = retrieve(query, n=top_k)

        if not chunks:
            console.print("[yellow]No relevant notes found. Try rephrasing.[/]")
            continue

        last_sources = format_sources(chunks)
        context = build_context(chunks)
        messages = build_messages(query, context, history)

        # --- Generation ---
        if thinking_enabled:
            thinking, answer = stream_with_thinking(messages)
        else:
            thinking = ""
            answer = stream_answer_only(messages)

        # --- Sources footer ---
        console.print(Rule(style="dim"))
        console.print("[dim]Sources:[/] ", end="")
        console.print("  ".join(f"[cyan]{s}[/]" for s in last_sources[:3]))
        if len(last_sources) > 3:
            console.print(f"[dim]  +{len(last_sources) - 3} more — /sources to see all[/]")

        # --- Update history (store clean answer only) ---
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})