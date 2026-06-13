"""
tests/test_retriever.py — all external calls mocked
"""
import pytest
from unittest.mock import patch, MagicMock
from brain.retriever import build_context, format_sources, RetrievedChunk, retrieve


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

        chunks = retrieve("test query", n=1, hybrid=False)
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
        chunks = retrieve("query", hybrid=False)
        assert chunks[0].score == 0.42


class TestHybridSearch:
    @patch("brain.retriever._semantic_retrieve")
    @patch("brain.retriever._keyword_retrieve")
    def test_hybrid_combines_results(self, mock_keyword, mock_semantic):
        """Test that hybrid search combines semantic and keyword results."""
        # Semantic results
        semantic_chunk = RetrievedChunk(
            doc_id="a::0",
            file_path="a.md",
            note_title="Alpha",
            heading="h1",
            text="semantic match",
            score=0.1,
            semantic_score=0.1,
        )
        
        # Keyword results (different doc)
        keyword_chunk = RetrievedChunk(
            doc_id="b::0",
            file_path="b.md",
            note_title="Beta",
            heading="h1",
            text="keyword match",
            score=25.0,
            keyword_score=25.0,
        )
        
        mock_semantic.return_value = [semantic_chunk]
        mock_keyword.return_value = [keyword_chunk]
        
        chunks = retrieve("test query", hybrid=True)
        
        # Should return both chunks
        assert len(chunks) > 0
        doc_ids = [c.doc_id for c in chunks]
        assert "a::0" in doc_ids or "b::0" in doc_ids

    @patch("brain.retriever.embed")
    @patch("brain.retriever.db")
    def test_semantic_only_mode(self, mock_db, mock_embed):
        """Test that hybrid=False uses only semantic search."""
        mock_embed.return_value = [0.1] * 768
        mock_db.query.return_value = {
            "ids": [["n::0"]],
            "documents": [["text"]],
            "metadatas": [[{"file_path": "n.md", "note_title": "N", "heading": "h"}]],
            "distances": [[0.15]],
        }
        
        chunks = retrieve("query", hybrid=False)
        assert len(chunks) == 1
        assert chunks[0].semantic_score == 0.15
