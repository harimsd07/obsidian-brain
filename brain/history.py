"""
brain/history.py
Persistent chat history — saves/loads sessions to ~/.brain/history/
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ~/.brain/history/
HISTORY_DIR = Path.home() / ".brain" / "history"


def _ensure_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    return HISTORY_DIR / f"{session_id}.jsonl"


def new_session_id() -> str:
    """Generate a session ID based on current timestamp."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_message(session_id: str, role: str, content: str):
    """Append a single message to the session file."""
    _ensure_dir()
    record = {
        "role": role,
        "content": content,
        "timestamp": time.time(),
    }
    with open(_session_path(session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_session(session_id: str) -> list:
    """Load all messages from a session. Returns list of {role, content} dicts."""
    path = _session_path(session_id)
    if not path.exists():
        return []
    messages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                messages.append({
                    "role": record["role"],
                    "content": record["content"],
                    "timestamp": record.get("timestamp", 0.0),
                })
            except (json.JSONDecodeError, KeyError):
                continue
    return messages


def list_sessions(limit: int = 20) -> list:
    """
    List recent sessions sorted by most recent first.
    Returns list of dicts: {session_id, date, message_count, first_question}
    """
    _ensure_dir()
    sessions = []

    for path in sorted(HISTORY_DIR.glob("*.jsonl"), reverse=True)[:limit]:
        session_id = path.stem
        messages = load_session(session_id)
        if not messages:
            continue

        # Find first user question
        first_question = ""
        for msg in messages:
            if msg["role"] == "user":
                first_question = msg["content"][:80]
                if len(msg["content"]) > 80:
                    first_question += "..."
                break

        # Parse date from session_id
        try:
            dt = datetime.strptime(session_id, "%Y-%m-%d_%H-%M-%S")
            date_label = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            date_label = session_id

        user_count = sum(1 for m in messages if m["role"] == "user")

        sessions.append({
            "session_id": session_id,
            "date": date_label,
            "message_count": user_count,
            "first_question": first_question,
            "path": str(path),
        })

    return sessions


def get_latest_session_id() -> Optional[str]:
    """Return the most recent session ID, or None if no history."""
    _ensure_dir()
    files = sorted(HISTORY_DIR.glob("*.jsonl"), reverse=True)
    if not files:
        return None
    return files[0].stem


def search_sessions(keyword: str, limit: int = 10) -> list:
    """
    Search session content for a keyword.
    Returns matching sessions with the matching message excerpt.
    """
    _ensure_dir()
    keyword_lower = keyword.lower()
    results = []

    for path in sorted(HISTORY_DIR.glob("*.jsonl"), reverse=True):
        session_id = path.stem
        messages = load_session(session_id)

        for msg in messages:
            if keyword_lower in msg["content"].lower():
                try:
                    dt = datetime.strptime(session_id, "%Y-%m-%d_%H-%M-%S")
                    date_label = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    date_label = session_id

                # Extract excerpt around the keyword
                content = msg["content"]
                idx = content.lower().find(keyword_lower)
                start = max(0, idx - 40)
                end = min(len(content), idx + 80)
                excerpt = content[start:end].strip()
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(content):
                    excerpt = excerpt + "..."

                results.append({
                    "session_id": session_id,
                    "date": date_label,
                    "role": msg["role"],
                    "excerpt": excerpt,
                })
                break  # one match per session

        if len(results) >= limit:
            break

    return results


def delete_session(session_id: str) -> bool:
    """Delete a session file. Returns True if deleted."""
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False


def clear_all_history() -> int:
    """Delete all session files. Returns count deleted."""
    _ensure_dir()
    count = 0
    for path in HISTORY_DIR.glob("*.jsonl"):
        path.unlink()
        count += 1
    return count
