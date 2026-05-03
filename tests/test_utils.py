"""
tests/test_utils.py
"""
import pytest
from pathlib import Path
from brain.utils import (
    parse_note, resolve_wikilinks, note_title_from_path,
    relative_path, file_hash, NoteChunk,
)


class TestResolveWikilinks:
    def test_simple_wikilink(self):
        assert resolve_wikilinks("See [[Projects]] for more.") == "See Projects for more."

    def test_aliased_wikilink(self):
        assert resolve_wikilinks("See [[Projects|my work]] here.") == "See my work here."

    def test_multiple_wikilinks(self):
        text = "[[Note A]] and [[Note B|alias B]]"
        result = resolve_wikilinks(text)
        assert "Note A" in result
        assert "alias B" in result
        assert "[[" not in result

    def test_no_wikilinks(self):
        text = "Plain text with no links."
        assert resolve_wikilinks(text) == text

    def test_empty_string(self):
        assert resolve_wikilinks("") == ""


class TestNoteTitleFromPath:
    def test_simple_filename(self, tmp_path):
        path = tmp_path / "MyNote.md"
        path.touch()
        assert note_title_from_path(path, tmp_path) == "MyNote"

    def test_filename_with_spaces(self, tmp_path):
        path = tmp_path / "My Project Note.md"
        path.touch()
        assert note_title_from_path(path, tmp_path) == "My Project Note"

    def test_nested_path(self, tmp_path):
        sub = tmp_path / "Projects"
        sub.mkdir()
        path = sub / "BankPrep.md"
        path.touch()
        assert note_title_from_path(path, tmp_path) == "BankPrep"


class TestRelativePath:
    def test_direct_child(self, tmp_path):
        path = tmp_path / "note.md"
        path.touch()
        assert relative_path(path, tmp_path) == "note.md"

    def test_nested(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        path = sub / "note.md"
        path.touch()
        result = relative_path(path, tmp_path)
        assert result == "sub/note.md"


class TestParseNote:
    def test_frontmatter_tags_list(self, tmp_path):
        note = tmp_path / "test.md"
        note.write_text("---\ntags: [ai, python]\n---\n# Title\n\nContent here.")
        _, meta, sections = parse_note(note, tmp_path)
        assert "ai" in meta["tags"]
        assert "python" in meta["tags"]

    def test_frontmatter_tags_string(self, tmp_path):
        note = tmp_path / "test.md"
        note.write_text("---\ntags: ai python\n---\n# Title\n\nContent.")
        _, meta, sections = parse_note(note, tmp_path)
        assert isinstance(meta["tags"], list)

    def test_no_frontmatter(self, tmp_path):
        note = tmp_path / "test.md"
        note.write_text("# Title\n\nJust content, no frontmatter.")
        _, meta, sections = parse_note(note, tmp_path)
        assert meta["tags"] == []
        assert meta["aliases"] == []

    def test_sections_by_heading(self, tmp_path, sample_markdown):
        note = tmp_path / "test.md"
        note.write_text(sample_markdown)
        _, _, sections = parse_note(note, tmp_path)
        headings = [h for h, _ in sections]
        assert "Machine Learning" in headings
        assert "Supervised Learning" in headings
        assert "Unsupervised Learning" in headings

    def test_note_without_headings(self, tmp_path):
        note = tmp_path / "test.md"
        note.write_text("Just a plain note with no headings at all.")
        _, _, sections = parse_note(note, tmp_path)
        assert len(sections) == 1
        assert sections[0][0] == "__intro__"

    def test_aliases_list(self, tmp_path):
        note = tmp_path / "test.md"
        note.write_text("---\naliases: [alias1, alias2]\n---\n# Title\n")
        _, meta, _ = parse_note(note, tmp_path)
        assert "alias1" in meta["aliases"]

    def test_tag_hash_stripped(self, tmp_path):
        note = tmp_path / "test.md"
        note.write_text("---\ntags: ['#ai', '#python']\n---\n# T\n")
        _, meta, _ = parse_note(note, tmp_path)
        assert "ai" in meta["tags"]
        assert "python" in meta["tags"]


class TestFileHash:
    def test_same_content_same_hash(self, tmp_path):
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("same content")
        f2.write_text("same content")
        assert file_hash(f1) == file_hash(f2)

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("content a")
        f2.write_text("content b")
        assert file_hash(f1) != file_hash(f2)

    def test_hash_changes_on_edit(self, tmp_path):
        f = tmp_path / "note.md"
        f.write_text("original")
        h1 = file_hash(f)
        f.write_text("modified")
        h2 = file_hash(f)
        assert h1 != h2
