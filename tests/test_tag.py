"""
tests/test_tag.py — all external calls mocked
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from brain.commands.tag import _parse_tags, _get_untagged_notes, run_tag


class TestParseTags:
    def test_standard_yaml_list(self):
        output = "- arch-linux\n- package-manager\n- terminal"
        tags = _parse_tags(output)
        assert tags == ["arch-linux", "package-manager", "terminal"]

    def test_strips_quotes(self):
        output = '- "arch-linux"\n- \'terminal\''
        tags = _parse_tags(output)
        assert "arch-linux" in tags
        assert "terminal" in tags

    def test_lowercases_tags(self):
        output = "- Arch-Linux\n- TERMINAL"
        tags = _parse_tags(output)
        assert "arch-linux" in tags
        assert "terminal" in tags

    def test_replaces_spaces_with_hyphens(self):
        output = "- arch linux\n- package manager"
        tags = _parse_tags(output)
        assert "arch-linux" in tags
        assert "package-manager" in tags

    def test_caps_at_five(self):
        output = "- a\n- b\n- c\n- d\n- e\n- f\n- g"
        tags = _parse_tags(output)
        assert len(tags) <= 5

    def test_removes_special_chars(self):
        output = "- arch@linux!\n- term#inal"
        tags = _parse_tags(output)
        assert all(t.replace("-", "").isalnum() for t in tags)

    def test_empty_output(self):
        assert _parse_tags("") == []

    def test_asterisk_marker(self):
        output = "* arch-linux\n* terminal"
        tags = _parse_tags(output)
        assert "arch-linux" in tags

    def test_skips_empty_lines(self):
        output = "- arch-linux\n\n- terminal\n\n"
        tags = _parse_tags(output)
        assert len(tags) == 2


class TestGetUntaggedNotes:
    @patch("brain.commands.tag.db")
    def test_returns_untagged(self, mock_db, tmp_vault):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [
                {"file_path": "Projects.md", "tags": ""},
                {"file_path": "Ideas.md", "tags": "ai python"},
            ]
        }
        untagged = _get_untagged_notes(tmp_vault)
        fps = [fp for fp, _ in untagged]
        assert "Projects.md" in fps
        assert "Ideas.md" not in fps

    @patch("brain.commands.tag.db")
    def test_skips_nonexistent_files(self, mock_db, tmp_vault):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [
                {"file_path": "ghost/note.md", "tags": ""},
            ]
        }
        untagged = _get_untagged_notes(tmp_vault)
        # ghost/note.md doesn't exist in tmp_vault — should be skipped
        assert len(untagged) == 0

    @patch("brain.commands.tag.db")
    def test_all_tagged_returns_empty(self, mock_db, tmp_vault):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [
                {"file_path": "Projects.md", "tags": "projects work"},
                {"file_path": "Ideas.md", "tags": "ai"},
            ]
        }
        untagged = _get_untagged_notes(tmp_vault)
        assert untagged == []


class TestRunTag:
    @patch("brain.commands.tag._suggest_tags_for_note")
    @patch("brain.commands.tag._get_untagged_notes")
    def test_dry_run_does_not_write(self, mock_untagged, mock_suggest, tmp_vault):
        mock_untagged.return_value = [("Projects.md", tmp_vault / "Projects.md")]
        mock_suggest.return_value = ["projects", "work", "python"]

        with patch("brain.commands.tag._write_tags_to_note") as mock_write:
            run_tag(dry_run=True, vault_path=tmp_vault)
            mock_write.assert_not_called()

    @patch("brain.commands.tag._suggest_tags_for_note")
    @patch("brain.commands.tag._get_untagged_notes")
    def test_apply_writes_tags(self, mock_untagged, mock_suggest, tmp_vault):
        mock_untagged.return_value = [("Projects.md", tmp_vault / "Projects.md")]
        mock_suggest.return_value = ["projects", "work", "python"]

        with patch("brain.commands.tag._write_tags_to_note") as mock_write:
            mock_write.return_value = True
            run_tag(dry_run=False, vault_path=tmp_vault)
            mock_write.assert_called_once()

    @patch("brain.commands.tag._suggest_tags_for_note")
    @patch("brain.commands.tag._get_untagged_notes")
    def test_no_untagged_notes(self, mock_untagged, mock_suggest, tmp_vault):
        mock_untagged.return_value = []
        run_tag(dry_run=True, vault_path=tmp_vault)
        mock_suggest.assert_not_called()

    @patch("brain.commands.tag.db")
    @patch("brain.commands.tag._suggest_tags_for_note")
    def test_single_note_dry_run(self, mock_suggest, mock_db, tmp_vault):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [{"file_path": "Projects.md"}]
        }
        mock_suggest.return_value = ["projects", "python", "work"]

        with patch("brain.commands.tag._write_tags_to_note") as mock_write:
            run_tag(note="Projects", dry_run=True, vault_path=tmp_vault)
            mock_write.assert_not_called()

    @patch("brain.commands.tag.db")
    @patch("brain.commands.tag._suggest_tags_for_note")
    def test_single_note_apply(self, mock_suggest, mock_db, tmp_vault):
        mock_db.get_collection.return_value.get.return_value = {
            "metadatas": [{"file_path": "Projects.md"}]
        }
        mock_suggest.return_value = ["projects", "python", "work"]

        with patch("brain.commands.tag._write_tags_to_note") as mock_write:
            mock_write.return_value = True
            run_tag(note="Projects", dry_run=False, vault_path=tmp_vault)
            mock_write.assert_called_once()
