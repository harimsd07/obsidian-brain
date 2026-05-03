"""
tests/test_ingest.py — mocked Ollama and ChromaDB
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from brain.ingest import collect_notes, ingest_note


class TestCollectNotes:
    def test_finds_md_files(self, tmp_vault):
        notes = collect_notes(tmp_vault)
        names = [n.name for n in notes]
        assert "Projects.md" in names
        assert "Ideas.md" in names

    def test_skips_obsidian_dir(self, tmp_vault):
        notes = collect_notes(tmp_vault)
        paths = [str(n) for n in notes]
        assert not any(".obsidian" in p for p in paths)

    def test_finds_nested_notes(self, tmp_vault):
        notes = collect_notes(tmp_vault)
        names = [n.name for n in notes]
        assert "2024-01-01.md" in names

    def test_returns_sorted(self, tmp_vault):
        notes = collect_notes(tmp_vault)
        assert notes == sorted(notes)

    def test_empty_vault(self, tmp_path):
        empty = tmp_path / "empty_vault"
        empty.mkdir()
        (empty / ".obsidian").mkdir()
        notes = collect_notes(empty)
        assert notes == []

    def test_ignores_non_md(self, tmp_vault):
        # Add a non-md file
        (tmp_vault / "image.png").write_bytes(b"fakepng")
        notes = collect_notes(tmp_vault)
        assert all(n.suffix == ".md" for n in notes)


class TestIngestNote:
    @patch("brain.ingest.embed_batch")
    @patch("brain.ingest.db")
    def test_ingest_returns_chunk_count(self, mock_db, mock_embed, tmp_vault):
        mock_embed.return_value = [[0.1] * 768] * 10
        mock_db.delete_by_file.return_value = None
        mock_db.upsert_chunks.return_value = None

        note_path = tmp_vault / "Projects.md"
        n = ingest_note(note_path, tmp_vault, force=True)
        assert n > 0

    @patch("brain.ingest.embed_batch")
    @patch("brain.ingest.db")
    def test_skips_unchanged_file(self, mock_db, mock_embed, tmp_vault):
        mock_embed.return_value = [[0.1] * 768] * 10
        mock_db.delete_by_file.return_value = None
        mock_db.upsert_chunks.return_value = None

        note_path = tmp_vault / "Projects.md"
        # First ingest — should index
        n1 = ingest_note(note_path, tmp_vault, force=True)
        assert n1 > 0

        # Second ingest same file — should skip (hash unchanged)
        n2 = ingest_note(note_path, tmp_vault, force=False)
        assert n2 == 0

    @patch("brain.ingest.embed_batch")
    @patch("brain.ingest.db")
    def test_empty_note_returns_zero(self, mock_db, mock_embed, tmp_vault):
        mock_embed.return_value = []
        mock_db.delete_by_file.return_value = None

        empty_note = tmp_vault / "Empty.md"
        n = ingest_note(empty_note, tmp_vault, force=True)
        assert n == 0

    @patch("brain.ingest.embed_batch")
    @patch("brain.ingest.db")
    def test_force_reindexes(self, mock_db, mock_embed, tmp_vault):
        mock_embed.return_value = [[0.1] * 768] * 10
        mock_db.delete_by_file.return_value = None
        mock_db.upsert_chunks.return_value = None

        note_path = tmp_vault / "Ideas.md"
        n1 = ingest_note(note_path, tmp_vault, force=True)
        n2 = ingest_note(note_path, tmp_vault, force=True)  # force=True re-indexes
        assert n1 > 0
        assert n2 > 0
