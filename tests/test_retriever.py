"""
tests/test_retriever.py — all external calls mocked
"""
import pytest
from unittest.mock import patch, MagicMock
from brain.retriever import build_context, format_sources, RetrievedChunk


class TestBuildContext:
    def test_single_chunk(self, sample_chunks):
        ctx = build_context([sample_chunks[0]])
        assert "Projects" in ctx
        assert "projects note" in ctx

    def test_multiple_chunks_separated(self, sample_chunks):
        ctx = build_context(sample_chunks)
        assert "---" in ctx  # separator between chunks
        assert "Projects" in ctx
        assert "Ideas" in ctx

    def test_heading_included(self, sample_chunks):
        chunk = RetrievedChunk(
            doc_id="test::0",
            file_path="test.md",
            note_title="Test",
            heading="My Section",
            text="Content here.",
            score=0.1,
        )
        ctx = build_context([chunk])
        assert "My Section" in ctx

    def test_intro_heading_excluded(self):
        chunk = RetrievedChunk(
            doc_id="test::0",
            file_path="test.md",
            note_title="Test",
            heading="__intro__",
            text="Intro content.",
            score=0.1,
        )
        ctx = build_context([chunk])
        assert "__intro__" not in ctx

    def test_empty_chunks(self):
        ctx = build_context([])
        assert ctx == ""


class TestFormatSources:
    def test_deduplication(self):
        chunks = [
            RetrievedChunk("a::0", "a.md", "Note A", "h1", "text", 0.1),
            RetrievedChunk("a::1", "a.md", "Note A", "h2", "text", 0.2),
            RetrievedChunk("b::0", "b.md", "Note B", "h1", "text", 0.3),
        ]
        sources = format_sources(chunks)
        assert len(sources) == 2  # a.md deduplicated

    def test_order_preserved(self):
        chunks = [
            RetrievedChunk("a::0", "a.md", "Alpha", "h", "t", 0.1),
            RetrievedChunk("b::0", "b.md", "Beta", "h", "t", 0.2),
        ]
        sources = format_sources(chunks)
        assert "Alpha" in sources[0]
        assert "Beta" in sources[1]

    def test_empty_chunks(self):
        assert format_sources([]) == []


class TestRetrieve:
    @patch("brain.retriever.embed")
    @patch("brain.retriever.db")
    def test_returns_chunks(self, mock_db, mock_embed):
        mock_embed.return_value = [0.1] * 768
        mock_db.query.return_value = {
            "ids": [["note.md::0"]],
            "documents": [["Some content"]],
            "metadatas": [[{
                "file_path": "note.md",
                "note_title": "Note",
                "heading": "Intro",
            }]],
            "distances": [[0.15]],
        }

        from brain.retriever import retrieve
        chunks = retrieve("test query", n=1)
        assert len(chunks) == 1
        assert chunks[0].file_path == "note.md"
        assert chunks[0].score == 0.15

    @patch("brain.retriever.embed")
    @patch("brain.retriever.db")
    def test_returns_empty_on_db_error(self, mock_db, mock_embed):
        mock_embed.return_value = [0.1] * 768
        mock_db.query.side_effect = Exception("DB error")

        from brain.retriever import retrieve
        chunks = retrieve("test query", n=5)
        assert chunks == []

    @patch("brain.retriever.embed")
    @patch("brain.retriever.db")
    def test_score_is_distance(self, mock_db, mock_embed):
        mock_embed.return_value = [0.1] * 768
        mock_db.query.return_value = {
            "ids": [["n::0"]],
            "documents": [["text"]],
            "metadatas": [[{"file_path": "n.md", "note_title": "N", "heading": "h"}]],
            "distances": [[0.42]],
        }
        from brain.retriever import retrieve
        chunks = retrieve("query")
        assert chunks[0].score == 0.42
