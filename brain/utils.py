import re
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import frontmatter


@dataclass
class NoteChunk:
    """A single chunk of text extracted from a note."""
    doc_id: str                  # unique: filepath + chunk index
    file_path: str               # relative path from vault root
    note_title: str
    heading: str                 # nearest heading above this chunk
    text: str                    # actual chunk content
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    modified_at: float = 0.0
    file_hash: str = ""


def file_hash(path: Path) -> str:
    """MD5 hash of file contents — used to skip unchanged files."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def parse_note(path: Path, vault_root: Path) -> tuple[str, dict, list[tuple[str, str]]]:
    """
    Parse a markdown note.
    Returns: (body_text, metadata_dict, sections)
    sections = list of (heading, text) tuples split by H1/H2/H3
    """
    try:
        post = frontmatter.load(str(path))
    except Exception:
        # Fallback: treat entire file as plain text with no frontmatter
        post = frontmatter.Post(path.read_text(encoding="utf-8", errors="replace"))

    body = post.content
    metadata = dict(post.metadata)

    # Resolve tags — Obsidian supports tags as list or space-separated string
    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        tags = tags.split()
    tags = [str(t).lstrip("#") for t in tags]

    aliases = metadata.get("aliases", [])
    if isinstance(aliases, str):
        aliases = [aliases]
    aliases = [str(a) for a in aliases]

    metadata["tags"] = tags
    metadata["aliases"] = aliases

    # Split body by headings (H1, H2, H3)
    sections = _split_by_headings(body)

    return body, metadata, sections


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """
    Split markdown text into (heading, content) pairs.
    Content before the first heading gets heading = '__intro__'.
    """
    pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    if not matches:
        return [("__intro__", text.strip())]

    sections = []

    # Text before first heading
    intro = text[: matches[0].start()].strip()
    if intro:
        sections.append(("__intro__", intro))

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections.append((heading, content))

    return sections


def resolve_wikilinks(text: str) -> str:
    """Replace [[Note Name]] and [[Note Name|alias]] with plain text for embedding."""
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)   # [[note|alias]] → alias
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)               # [[note]] → note
    return text


def note_title_from_path(path: Path, vault_root: Path) -> str:
    """Use filename without extension as note title."""
    return path.stem


def relative_path(path: Path, vault_root: Path) -> str:
    try:
        return str(path.relative_to(vault_root))
    except ValueError:
        return str(path)
