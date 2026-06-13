"""
brain/commands/chat.py
Interactive Q&A REPL with thinking phase and persistent history.
"""

import re
import time
import ollama
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.live import Live
from rich.text import Text
from rich.markdown import Markdown

from brain.retriever import retrieve, build_context, format_sources
from brain.config import TOP_K, LLM_MODEL, EMBED_MODEL
from brain.llm import generate
from brain.history import (
    new_session_id, save_message, load_session,
    get_latest_session_id, list_sessions,
)

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
[bold cyan]Obsidian Brain — Chat Commands[/]

[bold]Navigation[/]
  [cyan]/help[/]        Show this help
  [cyan]/exit[/]        Quit the chat

[bold]Search & Retrieval[/]
  [cyan]/top N[/]       Set number of chunks retrieved per query (default: 5)
  [cyan]/sources[/]     Show all source notes from the last answer

[bold]Display[/]
  [cyan]/thinking[/]    Toggle thinking phase on/off
  [cyan]/model[/]       Show active LLM provider, model, and settings

[bold]Session[/]
  [cyan]/clear[/]       Clear conversation history and start fresh
  [cyan]/save[/]        Show current session ID and history file path
  [cyan]/sessions[/]    List recent past sessions


  [cyan]/history[/]    Show messages from current session

[bold]Examples[/]
  [dim]what are my notes about RAG systems?[/]
  [dim]summarize my ideas on Arch Linux[/]
  [dim]what did I write about project goose?[/]
  [dim]/top 10[/]       [dim]← retrieve more context for complex questions[/]
"""


def build_messages(question: str, context: str, history: list) -> list:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history[-8:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"
    })
    return messages


def stream_with_thinking(messages: list) -> tuple:
    """Stream LLM response separating <think> from answer."""
    full_text = ""
    thinking_buf = ""
    answer_buf = ""
    think_done = False

    console.print()
    console.print(Rule("[dim]thinking[/dim]", style="dim yellow"))

    with Live(
        Panel(Text(""), border_style="yellow dim", padding=(0, 1)),
        console=console,
        refresh_per_second=15,
    ) as live:
        for delta in generate(messages=messages, stream=True):
            if not delta:
                continue
            full_text += delta

            if not think_done:
                thinking_buf += delta
                if "</think>" in thinking_buf:
                    think_done = True
                    parts = thinking_buf.split("</think>", 1)
                    clean_think = parts[0].replace("<think>", "").strip()
                    answer_buf = parts[1] if len(parts) > 1 else ""
                    live.update(Panel(
                        Markdown(clean_think),
                        title="[yellow]thinking[/yellow]",
                        border_style="yellow dim",
                        padding=(0, 1),
                    ))
                else:
                    display = thinking_buf.replace("<think>", "").strip()
                    live.update(Panel(
                        Text(display, style="dim"),
                        title="[yellow]thinking[/yellow]",
                        border_style="yellow dim",
                        padding=(0, 1),
                    ))
            else:
                answer_buf += delta

    think_match = re.search(r"<think>(.*?)</think>", full_text, re.DOTALL)
    thinking_text = think_match.group(1).strip() if think_match else ""
    answer_text = re.sub(r"<think>.*?</think>", "", full_text, flags=re.DOTALL).strip()

    console.print()
    console.print(Rule("[dim]answer[/dim]", style="dim green"))
    console.print()

    with Live(Markdown(""), console=console, refresh_per_second=15) as live:
        displayed = ""
        for i in range(0, len(answer_text), 8):
            displayed = answer_text[: i + 8]
            live.update(Markdown(displayed))
            time.sleep(0.01)
        live.update(Markdown(answer_text))

    console.print()
    return thinking_text, answer_text


def stream_answer_only(messages: list) -> str:
    """Stream response without thinking phase."""
    full_response = ""
    console.print()
    console.print(Rule("[dim]answer[/dim]", style="dim green"))
    console.print()

    with Live(Markdown(""), console=console, refresh_per_second=15) as live:
        for delta in generate(messages=messages, stream=True):
            if delta:
                full_response += delta
                live.update(Markdown(full_response))

    console.print()
    return full_response


def run_chat(resume: bool = False):
    """Main chat REPL loop with persistent history."""
    from brain.history import save_message, load_session, get_latest_session_id

    # Session setup
    if resume:
        session_id = get_latest_session_id()
        if session_id:
            loaded = load_session(session_id)
            # Strip timestamps for LLM history
            history = [{"role": m["role"], "content": m["content"]} for m in loaded]
            console.print(f"\n[dim]Resumed session:[/] [cyan]{session_id}[/] ({len([m for m in loaded if m['role']=='user'])} previous messages)\n")
        else:
            session_id = new_session_id()
            history = []
            console.print(f"\n[dim]No previous session found. Starting new session.[/]\n")
    else:
        session_id = new_session_id()
        history = []

    thinking_enabled = True
    last_sources: list = []
    top_k = TOP_K

    console.print(Panel(
        f"[bold]Obsidian Brain — Chat[/]\n"
        f"[dim]LLM:[/] [cyan]{LLM_MODEL}[/]  "
        f"[dim]Embed:[/] [cyan]{EMBED_MODEL}[/]  "
        f"[dim]Top-K:[/] [cyan]{top_k}[/]  "
        f"[dim]Thinking:[/] [green]on[/]\n"
        f"[dim]Session:[/] [cyan]{session_id}[/]\n\n"
        f"Type your question or [cyan]/help[/] for commands. [cyan]/exit[/] to quit.",
        border_style="dim",
    ))

    while True:
        try:
            console.print()
            query = console.input("[bold cyan]you[/] › ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[dim]Session saved: {session_id}[/]")
            break

        if not query:
            continue

        # --- Commands ---
        if query == "/exit":
            console.print(f"[dim]Session saved: {session_id}[/]")
            break

        if query == "/help":
            console.print(HELP_TEXT)
            continue

        if query == "/clear":
            history.clear()
            last_sources.clear()
            session_id = new_session_id()
            console.print(f"[dim]History cleared. New session: {session_id}[/]")
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
            console.print(
                f"  LLM: [cyan]{LLM_MODEL}[/]  "
                f"Embed: [cyan]{EMBED_MODEL}[/]  "
                f"Top-K: [cyan]{top_k}[/]  "
                f"Thinking: {state}"
            )
            continue

        if query == "/save":
            console.print(
                f"  Session ID: [cyan]{session_id}[/]\n"
                f"  File: [dim]{Path.home() / '.brain' / 'history' / (session_id + '.jsonl')}[/]"
            )
            continue

        if query == "/sessions":
            sessions = list_sessions(limit=10)
            if not sessions:
                console.print("[dim]No past sessions found.[/]")
            else:
                console.print("\n[bold]Recent sessions:[/]")
                from rich.table import Table
                from rich import box
                table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", padding=(0,1))
                table.add_column("#", style="dim", width=3)
                table.add_column("Date", style="cyan")
                table.add_column("Msgs", width=5)
                table.add_column("First question", style="dim")
                for i, s in enumerate(sessions, 1):
                    table.add_row(
                        str(i),
                        s["date"],
                        str(s["message_count"]),
                        s["first_question"],
                    )
                console.print(table)
            continue

        if query == "/history":
            console.print("\n[bold]Current session history:[/]\n")
            if not history:
                console.print("[dim]No messages yet in this session.[/]")
            else:
                for msg in history:
                    role_label = "[bold cyan]you[/]" if msg["role"] == "user" else "[bold green]brain[/]"
                    console.print(f"{role_label} › {msg['content'][:200]}")
                    if len(msg["content"]) > 200:
                        console.print(f"  [dim]...({len(msg['content'])} chars total)[/]")
                    console.print()
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

        # --- Save to history ---
        save_message(session_id, "user", query)
        save_message(session_id, "assistant", answer)

        # --- Update in-memory history ---
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
