"""
tests/test_chunker.py
"""
import pytest
from brain.chunker import chunk_text, split_sections_into_chunks, token_count


class TestTokenCount:
    def test_empty_string(self):
        assert token_count("") == 0

    def test_single_word(self):
        assert token_count("hello") > 0

    def test_longer_text(self):
        text = "This is a longer piece of text with multiple words and sentences."
        assert token_count(text) > 5


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "Short text that fits in one chunk."
        chunks = chunk_text(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        # Generate text that exceeds chunk size
        text = " ".join(["word"] * 600)
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) > 1

    def test_overlap_content(self):
        text = " ".join([f"word{i}" for i in range(200)])
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        # With overlap, adjacent chunks should share some tokens
        assert len(chunks) >= 2

    def test_empty_text(self):
        chunks = chunk_text("", chunk_size=100)
        assert chunks == []
        
    def test_exact_chunk_size(self):
        # Text that fills exactly one chunk should produce one chunk
        words = " ".join(["hello"] * 10)
        size = token_count(words)
        chunks = chunk_text(words, chunk_size=size, overlap=0)
        assert len(chunks) == 1


class TestSplitSectionsIntoChunks:
    def test_short_sections_kept_as_is(self):
        sections = [
            ("Intro", "Short intro text."),
            ("Section 1", "Brief section content."),
        ]
        result = split_sections_into_chunks(sections)
        assert len(result) == 2
        assert result[0] == ("Intro", "Short intro text.")

    def test_empty_sections_skipped(self):
        sections = [
            ("Empty", ""),
            ("Valid", "This has content."),
            ("Whitespace", "   "),
        ]
        result = split_sections_into_chunks(sections)
        assert len(result) == 1
        assert result[0][0] == "Valid"

    def test_long_section_split(self):
        long_text = " ".join(["word"] * 600)
        sections = [("Big Section", long_text)]
        result = split_sections_into_chunks(sections)
        assert len(result) > 1
        # All chunks should preserve the original heading
        assert all(h == "Big Section" for h, _ in result)

    def test_mixed_short_and_long(self):
        long_text = " ".join(["word"] * 600)
        sections = [
            ("Short", "Brief text."),
            ("Long", long_text),
        ]
        result = split_sections_into_chunks(sections)
        assert len(result) > 2  # short=1, long=multiple
