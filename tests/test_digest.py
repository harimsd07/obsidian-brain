"""
tests/test_digest.py — all external calls mocked
"""
import time
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from brain.commands.digest import _parse_since, _build_notes_block, run_digest
from brain.exceptions import BrainError


class TestParseSince:
    def test_hours(self):
        ts, label = _parse_since("24h")
        assert "24" in label or "hour" in label
        assert time.time() - ts - 24 * 3600 < 2

    def test_days(self):
        ts, label = _parse_since("7d")
        assert "7" in label or "day" in label
        assert time.time() - ts - 7 * 86400 < 2

    def test_weeks(self):
        ts, label = _parse_since("2w")
        assert "2" in label or "week" in label
        assert time.time() - ts - 2 * 604800 < 2

    def test_singular_label(self):
        _, label = _parse_since("1d")
        assert "day" in label
        assert "days" not in label

    def test_plural_label(self):
        _, label = _parse_since("7d")
        assert "days" in label

    def test_invalid_raises(self):
        with pytest.raises(BrainError):
            _parse_since("invalid")

    def test_invalid_unit_raises(self):
        with pytest.raises(BrainError):
            _parse_since("5m")


class TestBuildNotesBlock:
    def test_basic_structure(self):
        grouped = {
            "Projects/BankPrep.md": {
                "chunks": ["BankPrep chunk one.", "BankPrep chunk two."],
                "modified_at": time.time(),
            },
            "Ideas/RAG.md": {
                "chunks": ["RAG chunk one."],
                "modified_at": time.time() - 3600,
            },
        }
        block = _build_notes_block(grouped)
        assert "BankPrep" in block
        assert "RAG" in block

    def test_caps_at_max_notes(self):
        now = time.time()
        grouped = {
            f"note{i}.md": {"chunks": [f"content {i}"], "modified_at": now - i}
            for i in range(20)
        }
        block = _build_notes_block(grouped, max_notes=5)
        # Only 5 notes should appear
        assert block.count("###") <= 5

    def test_sorts_by_most_recent(self):
        now = time.time()
        grouped = {
            "old.md": {"chunks": ["old content"], "modified_at": now - 7200},
            "new.md": {"chunks": ["new content"], "modified_at": now - 100},
        }
        block = _build_notes_block(grouped)
        # new.md should appear before old.md
        assert block.index("new") < block.index("old")

    def test_caps_total_chars(self):
        now = time.time()
        grouped = {
            f"note{i}.md": {
                "chunks": ["x" * 1000],
                "modified_at": now - i,
            }
            for i in range(20)
        }
        block = _build_notes_block(grouped)
        assert len(block) < 8000  # stays within safe limit

    def test_empty_grouped(self):
        block = _build_notes_block({})
        assert block == ""


class TestRunDigest:
    @patch("brain.commands.digest.generate")
    @patch("brain.commands.digest._get_recent_notes")
    def test_generates_digest(self, mock_recent, mock_generate, tmp_path):
        mock_recent.return_value = {
            "Projects.md": {
                "chunks": ["Working on BankPrep PWA."],
                "modified_at": time.time(),
            }
        }
        mock_generate.return_value = iter(["Today ", "you worked ", "on BankPrep."])

        run_digest(since="24h", save=False, vault_path=tmp_path)
        mock_generate.assert_called_once()

    @patch("brain.commands.digest.generate")
    @patch("brain.commands.digest._get_recent_notes")
    def test_save_creates_file(self, mock_recent, mock_generate, tmp_path):
        mock_recent.return_value = {
            "Projects.md": {
                "chunks": ["Working on BankPrep."],
                "modified_at": time.time(),
            }
        }
        mock_generate.return_value = iter(["Great day of work!"])

        run_digest(since="24h", save=True, vault_path=tmp_path)

        digest_dir = tmp_path / "Digests"
        assert digest_dir.exists()
        files = list(digest_dir.glob("Digest-*.md"))
        assert len(files) == 1

    @patch("brain.commands.digest.generate")
    @patch("brain.commands.digest._get_recent_notes")
    def test_saved_file_has_frontmatter(self, mock_recent, mock_generate, tmp_path):
        mock_recent.return_value = {
            "note.md": {"chunks": ["content"], "modified_at": time.time()}
        }
        mock_generate.return_value = iter(["Digest content here."])

        run_digest(since="7d", save=True, vault_path=tmp_path)

        files = list((tmp_path / "Digests").glob("*.md"))
        content = files[0].read_text()
        assert "tags:" in content
        assert "digest" in content
        assert "auto-generated" in content

    @patch("brain.commands.digest._get_recent_notes")
    def test_no_recent_notes_shows_warning(self, mock_recent, tmp_path):
        mock_recent.return_value = {}
        # Should not raise
        run_digest(since="24h", save=False, vault_path=tmp_path)

    @patch("brain.commands.digest.generate")
    @patch("brain.commands.digest._get_recent_notes")
    def test_weekly_digest(self, mock_recent, mock_generate, tmp_path):
        mock_recent.return_value = {
            f"note{i}.md": {
                "chunks": [f"content {i}"],
                "modified_at": time.time() - i * 86400,
            }
            for i in range(5)
        }
        mock_generate.return_value = iter(["Weekly summary here."])
        run_digest(since="7d", save=False, vault_path=tmp_path)
        mock_generate.assert_called_once()
