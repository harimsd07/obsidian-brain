"""
tests/test_summarize.py — all external calls mocked
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from brain.commands.summarize import (
    _parse_since, _resolve_note_path, summarize_note, summarize_folder
)
from brain.exceptions import BrainError
from pathlib import Path


class TestParseSince:
    def test_hours(self):
        before = time.time()
        ts = _parse_since("24h")
        assert before - 24 * 3600 - 1 < ts < before

    def test_days(self):
        before = time.time()
        ts = _parse_since("7d")
        assert before - 7 * 86400 - 1 < ts < before

    def test_weeks(self):
        before = time.time()
        ts = _parse_since("2w")
        assert before - 2 * 604800 - 1 < ts < before

    def test_invalid_raises(self):
        with pytest.raises(BrainError):
            _parse_since("invalid")

    def test_invalid_unit(self):
        with pytest.raises((BrainError, ValueError)):
            _parse_since("5m")


class TestResolveNotePath:
    @patch("brain.commands.summarize.db")
    def test_exact_match(self, mock_db, tmp_path):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [{"file_path": "Projects/BankPrep.md"}]
        }
        result = _resolve_note_path("Projects/BankPrep.md", tmp_path)
        assert result == "Projects/BankPrep.md"

    @patch("brain.commands.summarize.db")
    def test_adds_md_extension(self, mock_db, tmp_path):
        # First call returns a match (simulating DB hit after adding .md)
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [{"file_path": "Projects/BankPrep.md"}]
        }
        result = _resolve_note_path("Projects/BankPrep", tmp_path)
        assert result == "Projects/BankPrep.md"

    @patch("brain.commands.summarize.db")
    def test_fuzzy_match_by_stem(self, mock_db, tmp_path):
        # First call misses, fuzzy scan finds it
        mock_db.get_collection.return_value.get.side_effect = [
            {"metadatas": []},   # exact match miss
            {"metadatas": []},   # vault-relative miss
            {"metadatas": [      # fuzzy scan
                {"file_path": "Projects/BankPrep.md"},
                {"file_path": "Ideas/RAG.md"},
            ]},
        ]
        result = _resolve_note_path("bankprep", tmp_path)
        assert "bankprep" in result.lower()


class TestSummarizeNote:
    @patch("brain.commands.summarize._stream_summary")
    @patch("brain.commands.summarize._resolve_note_path")
    @patch("brain.commands.summarize._get_chunks_for_file")
    def test_calls_stream_with_content(self, mock_chunks, mock_resolve, mock_stream, tmp_path):
        mock_resolve.return_value = "Projects/BankPrep.md"
        mock_chunks.return_value = ["Chunk one.", "Chunk two."]
        mock_stream.return_value = "Summary text"

        summarize_note("BankPrep", vault_path=tmp_path)

        mock_stream.assert_called_once()
        prompt_arg = mock_stream.call_args[0][0]
        assert "Chunk one." in prompt_arg
        assert "Chunk two." in prompt_arg

    @patch("brain.commands.summarize._resolve_note_path")
    @patch("brain.commands.summarize._get_chunks_for_file")
    def test_no_chunks_prints_warning(self, mock_chunks, mock_resolve, tmp_path, capsys):
        mock_resolve.return_value = "Missing.md"
        mock_chunks.return_value = []

        # Should not raise, just print a warning panel
        summarize_note("Missing", vault_path=tmp_path)


class TestSummarizeFolder:
    @patch("brain.commands.summarize._stream_summary")
    @patch("brain.commands.summarize._get_chunks_for_folder")
    def test_calls_stream_with_notes(self, mock_grouped, mock_stream, tmp_path):
        mock_grouped.return_value = {
            "Projects/BankPrep.md": ["BankPrep chunk one.", "BankPrep chunk two."],
            "Projects/RAG.md": ["RAG chunk one."],
        }
        mock_stream.return_value = "Folder summary"

        summarize_folder("Projects/", vault_path=tmp_path)

        mock_stream.assert_called_once()
        prompt_arg = mock_stream.call_args[0][0]
        assert "BankPrep" in prompt_arg
        assert "RAG" in prompt_arg

    @patch("brain.commands.summarize._get_chunks_for_folder")
    def test_empty_folder_prints_warning(self, mock_grouped, tmp_path):
        mock_grouped.return_value = {}
        # Should not raise
        summarize_folder("EmptyFolder/", vault_path=tmp_path)

    @patch("brain.commands.summarize._stream_summary")
    @patch("brain.commands.summarize._get_chunks_for_folder")
    def test_since_passed_to_getter(self, mock_grouped, mock_stream, tmp_path):
        mock_grouped.return_value = {
            "Daily/2024-01-01.md": ["Daily note content."]
        }
        mock_stream.return_value = "Digest"

        summarize_folder("Daily/", since="7d", vault_path=tmp_path)

        # Verify since_ts was non-zero (passed correctly)
        call_args = mock_grouped.call_args
        since_ts = call_args[0][1] if call_args[0] else call_args[1].get("since_ts", 0)
        assert since_ts > 0

    @patch("brain.commands.summarize._stream_summary")
    @patch("brain.commands.summarize._get_chunks_for_folder")
    def test_caps_chunks_per_note(self, mock_grouped, mock_stream, tmp_path):
        # Note with 10 chunks — only first 3 should go into prompt
        mock_grouped.return_value = {
            "BigNote.md": [f"chunk {i}" for i in range(10)]
        }
        mock_stream.return_value = "Summary"

        summarize_folder("Projects/", vault_path=tmp_path)

        prompt_arg = mock_stream.call_args[0][0]
        # chunk 0,1,2 should be present; chunk 3+ should not
        assert "chunk 0" in prompt_arg
        assert "chunk 2" in prompt_arg
        assert "chunk 3" not in prompt_arg
