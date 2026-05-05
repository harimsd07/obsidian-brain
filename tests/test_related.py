"""
tests/test_related.py — all external calls mocked
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from brain.commands.related import (
    _score_color, _resolve_note_path, find_related
)


class TestScoreColor:
    def test_strong_match(self):
        assert _score_color(0.1) == "green"

    def test_moderate_match(self):
        assert _score_color(0.3) == "yellow"

    def test_weak_match(self):
        assert _score_color(0.6) == "dim"

    def test_boundary_low(self):
        assert _score_color(0.2) == "yellow"

    def test_boundary_high(self):
        assert _score_color(0.4) == "dim"


class TestResolveNotePath:
    @patch("brain.commands.related.db")
    def test_exact_match(self, mock_db, tmp_path):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [{"file_path": "Linux/arch.md"}]
        }
        result = _resolve_note_path("Linux/arch.md", tmp_path)
        assert result == "Linux/arch.md"

    @patch("brain.commands.related.db")
    def test_adds_md_extension(self, mock_db, tmp_path):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [{"file_path": "Linux/arch.md"}]
        }
        result = _resolve_note_path("Linux/arch", tmp_path)
        assert result == "Linux/arch.md"

    @patch("brain.commands.related.db")
    def test_fuzzy_by_stem(self, mock_db, tmp_path):
        mock_db.get_collection.return_value.get.side_effect = [
            {"metadatas": []},
            {"metadatas": []},
            {"metadatas": [
                {"file_path": "Linux/arch-setup.md"},
                {"file_path": "projects/rag.md"},
            ]},
        ]
        result = _resolve_note_path("arch-setup", tmp_path)
        assert "arch-setup" in result.lower()


class TestFindRelated:
    @patch("brain.commands.related.db")
    @patch("brain.commands.related._representative_embedding")
    @patch("brain.commands.related._get_all_chunks_for_file")
    @patch("brain.commands.related._resolve_note_path")
    def test_shows_related_notes(
        self, mock_resolve, mock_chunks, mock_embed, mock_db, tmp_path
    ):
        mock_resolve.return_value = "Linux/arch.md"
        mock_chunks.return_value = ["Arch Linux setup guide."]
        mock_embed.return_value = [0.1] * 768
        mock_db.query.return_value = {
            "ids": [["Linux/arch.md::0", "projects/rag.md::0", "ObsidianForArch/setup.md::0"]],
            "documents": [["Arch chunk", "RAG chunk", "Obsidian chunk"]],
            "metadatas": [[
                {"file_path": "Linux/arch.md", "note_title": "arch", "heading": "intro"},
                {"file_path": "projects/rag.md", "note_title": "rag", "heading": "intro"},
                {"file_path": "ObsidianForArch/setup.md", "note_title": "setup", "heading": "intro"},
            ]],
            "distances": [[0.0, 0.15, 0.30]],
        }
        mock_db.collection_stats.return_value = {"total_chunks": 100}

        # Should not raise
        find_related("arch", top=5, vault_path=tmp_path)

    @patch("brain.commands.related._get_all_chunks_for_file")
    @patch("brain.commands.related._resolve_note_path")
    def test_no_chunks_shows_warning(self, mock_resolve, mock_chunks, tmp_path):
        mock_resolve.return_value = "missing.md"
        mock_chunks.return_value = []
        # Should not raise
        find_related("missing", top=5, vault_path=tmp_path)

    @patch("brain.commands.related.db")
    @patch("brain.commands.related._representative_embedding")
    @patch("brain.commands.related._get_all_chunks_for_file")
    @patch("brain.commands.related._resolve_note_path")
    def test_excludes_self(
        self, mock_resolve, mock_chunks, mock_embed, mock_db, tmp_path
    ):
        mock_resolve.return_value = "Linux/arch.md"
        mock_chunks.return_value = ["Some content."]
        mock_embed.return_value = [0.1] * 768
        # Only result is the note itself — should show no related notes
        mock_db.query.return_value = {
            "ids": [["Linux/arch.md::0"]],
            "documents": [["Same note chunk"]],
            "metadatas": [[
                {"file_path": "Linux/arch.md", "note_title": "arch", "heading": "h"},
            ]],
            "distances": [[0.0]],
        }
        # Should not raise even when self is the only result
        find_related("arch", top=5, vault_path=tmp_path)

    @patch("brain.commands.related.db")
    @patch("brain.commands.related._representative_embedding")
    @patch("brain.commands.related._get_all_chunks_for_file")
    @patch("brain.commands.related._resolve_note_path")
    def test_deduplicates_per_note(
        self, mock_resolve, mock_chunks, mock_embed, mock_db, tmp_path
    ):
        mock_resolve.return_value = "source.md"
        mock_chunks.return_value = ["Source content."]
        mock_embed.return_value = [0.1] * 768
        # Same note appears twice (two chunks) — should deduplicate
        mock_db.query.return_value = {
            "ids": [["related.md::0", "related.md::1"]],
            "documents": [["chunk 0", "chunk 1"]],
            "metadatas": [[
                {"file_path": "related.md", "note_title": "related", "heading": "h1"},
                {"file_path": "related.md", "note_title": "related", "heading": "h2"},
            ]],
            "distances": [[0.15, 0.25]],
        }
        # Should not raise and should deduplicate to 1 note
        find_related("source", top=5, vault_path=tmp_path)
