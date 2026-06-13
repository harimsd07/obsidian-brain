"""Tests for brain ask command."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_chunks():
    """Fake retrieval results."""
    from brain.retriever import RetrievedChunk
    return [
        RetrievedChunk(
            doc_id="c1",
            note_title="Html tags",
            file_path="ObsidianForArch/Arch Linux/Html tags.md",
            heading="Structural Tags",
            text="<div>, <span>, <section> are structural HTML tags used for layout.",
            score=0.12,
        ),
        RetrievedChunk(
            doc_id="c2",
            note_title="Html tags",
            file_path="ObsidianForArch/Arch Linux/Html tags.md",
            heading="List Tags",
            text="<ul> creates unordered lists. <ol> creates ordered lists. <li> is a list item.",
            score=0.18,
        ),
    ]


@pytest.fixture
def mock_db_with_chunks():
    """DB has indexed chunks."""
    with patch("brain.commands.ask.db") as mock_db:
        mock_db.collection_stats.return_value = {"total_chunks": 500}
        yield mock_db


@pytest.fixture
def mock_db_empty():
    """DB is empty — vault not indexed."""
    with patch("brain.commands.ask.db") as mock_db:
        mock_db.collection_stats.return_value = {"total_chunks": 0}
        yield mock_db


# ──────────────────────────────────────────────────────────────────────────────
# Tests — vault not indexed
# ──────────────────────────────────────────────────────────────────────────────

class TestAskVaultNotIndexed:
    def test_raises_vault_not_indexed(self, mock_db_empty):
        from brain.commands.ask import run_ask
        from brain.exceptions import VaultNotIndexed

        with pytest.raises(VaultNotIndexed):
            run_ask("what are my notes?", raw=True)


# ──────────────────────────────────────────────────────────────────────────────
# Tests — retrieval
# ──────────────────────────────────────────────────────────────────────────────

class TestAskRetrieval:
    def test_no_chunks_found_raw(self, mock_db_with_chunks):
        from brain.commands.ask import run_ask

        with patch("brain.commands.ask.retrieve", return_value=[]):
            import io, sys
            captured = io.StringIO()
            sys.stdout = captured
            run_ask("nonexistent topic", raw=True)
            sys.stdout = sys.__stdout__
            output = captured.getvalue()
        assert "No relevant notes" in output

    def test_retrieves_correct_top_k(self, mock_db_with_chunks, mock_chunks):
        from brain.commands.ask import run_ask

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks) as mock_retrieve, \
             patch("brain.commands.ask.generate", return_value=iter(["Answer."])), \
             patch("brain.commands.ask.build_context", return_value="context"):
            run_ask("test question", top_k=7, thinking=False, raw=True)
            mock_retrieve.assert_called_once_with("test question", top_k=7, hybrid=True)

    def test_default_top_k_is_10(self, mock_db_with_chunks, mock_chunks):
        from brain.commands.ask import run_ask

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks) as mock_retrieve, \
             patch("brain.commands.ask.generate", return_value=iter(["Answer."])), \
             patch("brain.commands.ask.build_context", return_value="context"):
            run_ask("test question", thinking=False, raw=True)
            mock_retrieve.assert_called_once_with("test question", top_k=10, hybrid=True)


# ──────────────────────────────────────────────────────────────────────────────
# Tests — raw output (pipe-friendly)
# ──────────────────────────────────────────────────────────────────────────────

class TestAskRawOutput:
    def test_raw_prints_answer(self, mock_db_with_chunks, mock_chunks, capsys):
        from brain.commands.ask import run_ask

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks), \
             patch("brain.commands.ask.build_context", return_value="ctx"), \
             patch("brain.commands.ask.generate", return_value=iter(["Hello ", "world."])):
            run_ask("test", thinking=False, raw=True)

        captured = capsys.readouterr()
        assert "Hello" in captured.out
        assert "world" in captured.out

    def test_raw_strips_think_tags(self, mock_db_with_chunks, mock_chunks, capsys):
        from brain.commands.ask import run_ask

        tokens = ["<think>", "some reasoning", "</think>", "Final answer."]
        with patch("brain.commands.ask.retrieve", return_value=mock_chunks), \
             patch("brain.commands.ask.build_context", return_value="ctx"), \
             patch("brain.commands.ask.generate", return_value=iter(tokens)):
            run_ask("test", thinking=True, raw=True)

        captured = capsys.readouterr()
        assert "Final answer." in captured.out
        assert "<think>" not in captured.out
        assert "some reasoning" not in captured.out

    def test_raw_no_rich_markup(self, mock_db_with_chunks, mock_chunks, capsys):
        """Raw output should not contain Rich panel borders."""
        from brain.commands.ask import run_ask

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks), \
             patch("brain.commands.ask.build_context", return_value="ctx"), \
             patch("brain.commands.ask.generate", return_value=iter(["clean answer"])):
            run_ask("test", thinking=False, raw=True)

        captured = capsys.readouterr()
        # Rich panel borders use box-drawing chars — shouldn't appear in raw mode
        assert "╭" not in captured.out
        assert "╰" not in captured.out


# ──────────────────────────────────────────────────────────────────────────────
# Tests — messages construction
# ──────────────────────────────────────────────────────────────────────────────

class TestAskMessages:
    def test_question_included_in_messages(self, mock_db_with_chunks, mock_chunks):
        from brain.commands.ask import run_ask

        captured_messages = []

        def fake_generate(messages, stream=True):
            captured_messages.extend(messages)
            return iter(["answer"])

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks), \
             patch("brain.commands.ask.build_context", return_value="ctx"), \
             patch("brain.commands.ask.generate", side_effect=fake_generate):
            run_ask("what are HTML tags?", thinking=False, raw=True)

        user_msg = next(m for m in captured_messages if m["role"] == "user")
        assert "what are HTML tags?" in user_msg["content"]

    def test_context_included_in_messages(self, mock_db_with_chunks, mock_chunks):
        from brain.commands.ask import run_ask

        captured_messages = []

        def fake_generate(messages, stream=True):
            captured_messages.extend(messages)
            return iter(["answer"])

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks), \
             patch("brain.commands.ask.build_context", return_value="FAKE_CONTEXT_12345"), \
             patch("brain.commands.ask.generate", side_effect=fake_generate):
            run_ask("test", thinking=False, raw=True)

        user_msg = next(m for m in captured_messages if m["role"] == "user")
        assert "FAKE_CONTEXT_12345" in user_msg["content"]

    def test_thinking_uses_think_system_prompt(self, mock_db_with_chunks, mock_chunks):
        from brain.commands.ask import run_ask

        captured_messages = []

        def fake_generate(messages, stream=True):
            captured_messages.extend(messages)
            return iter(["<think>reasoning</think>answer"])

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks), \
             patch("brain.commands.ask.build_context", return_value="ctx"), \
             patch("brain.commands.ask.generate", side_effect=fake_generate):
            run_ask("test", thinking=True, raw=True)

        system_msg = next(m for m in captured_messages if m["role"] == "system")
        assert "<think>" in system_msg["content"]

    def test_no_thinking_uses_plain_system_prompt(self, mock_db_with_chunks, mock_chunks):
        from brain.commands.ask import run_ask

        captured_messages = []

        def fake_generate(messages, stream=True):
            captured_messages.extend(messages)
            return iter(["answer"])

        with patch("brain.commands.ask.retrieve", return_value=mock_chunks), \
             patch("brain.commands.ask.build_context", return_value="ctx"), \
             patch("brain.commands.ask.generate", side_effect=fake_generate):
            run_ask("test", thinking=False, raw=True)

        system_msg = next(m for m in captured_messages if m["role"] == "system")
        assert "<think>" not in system_msg["content"]
