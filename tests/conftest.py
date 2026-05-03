"""
tests/conftest.py — shared fixtures for all tests
"""
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def tmp_vault(tmp_path):
    """Create a temporary Obsidian-like vault with sample notes."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()

    # Note 1 — with frontmatter
    (vault / "Projects.md").write_text(
        "---\ntags: [projects, work]\naliases: [my projects]\n---\n"
        "# Projects\n\nThis is my projects note.\n\n## BankPrep\n\nA React PWA for banking exams.\n"
    )

    # Note 2 — plain note
    (vault / "Ideas.md").write_text(
        "# Ideas\n\nRandom ideas go here.\n\n## RAG System\n\nBuild a local RAG for Obsidian.\n"
    )

    # Note 3 — with wikilinks
    (vault / "Links.md").write_text(
        "# Links\n\nSee [[Projects]] and [[Ideas]] for more.\n"
        "Also check [[Projects|my work]] page.\n"
    )

    # Note 4 — empty note (should be skipped gracefully)
    (vault / "Empty.md").write_text("")

    # Subfolder note
    sub = vault / "Daily"
    sub.mkdir()
    (sub / "2024-01-01.md").write_text(
        "---\ntags: [daily]\n---\n# 2024-01-01\n\nToday I worked on the RAG system.\n"
    )

    # Should be ignored
    obsidian_dir = vault / ".obsidian"
    (obsidian_dir / "config.json").write_text("{}")

    return vault


@pytest.fixture
def sample_markdown():
    return """---
tags: [python, ai]
aliases: [ml notes]
---
# Machine Learning

Introduction to ML concepts.

## Supervised Learning

Learning from labeled data.

## Unsupervised Learning

Finding patterns without labels.

### Clustering

K-means and DBSCAN.
"""


@pytest.fixture
def sample_chunks():
    """Pre-built chunks for retriever tests."""
    from brain.retriever import RetrievedChunk
    return [
        RetrievedChunk(
            doc_id="Projects.md::0",
            file_path="Projects.md",
            note_title="Projects",
            heading="__intro__",
            text="This is my projects note.",
            score=0.12,
        ),
        RetrievedChunk(
            doc_id="Ideas.md::0",
            file_path="Ideas.md",
            note_title="Ideas",
            heading="RAG System",
            text="Build a local RAG for Obsidian.",
            score=0.23,
        ),
    ]
