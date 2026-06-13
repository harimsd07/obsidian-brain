"""
tests/test_history.py — tests for persistent chat history
"""
import time
import pytest
from pathlib import Path
from unittest.mock import patch
from brain.history import (
    new_session_id, save_message, load_session,
    list_sessions, get_latest_session_id,
    search_sessions, delete_session, clear_all_history,
)


@pytest.fixture
def tmp_history_dir(tmp_path, monkeypatch):
    """Redirect history to a temp directory."""
    import brain.history as h
    monkeypatch.setattr(h, "HISTORY_DIR", tmp_path / "history")
    return tmp_path / "history"


class TestNewSessionId:
    def test_format(self):
        sid = new_session_id()
        # Should be YYYY-MM-DD_HH-MM-SS
        parts = sid.split("_")
        assert len(parts) == 2
        assert len(parts[0]) == 10  # YYYY-MM-DD
        assert len(parts[1]) == 8   # HH-MM-SS

    def test_unique(self):
        s1 = new_session_id()
        time.sleep(1)
        s2 = new_session_id()
        assert s1 != s2


class TestSaveAndLoad:
    def test_save_and_load_single_message(self, tmp_history_dir):
        save_message("test-session", "user", "Hello brain")
        messages = load_session("test-session")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello brain"

    def test_save_multiple_messages(self, tmp_history_dir):
        save_message("sess1", "user", "Question 1")
        save_message("sess1", "assistant", "Answer 1")
        save_message("sess1", "user", "Question 2")
        messages = load_session("sess1")
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_load_nonexistent_returns_empty(self, tmp_history_dir):
        messages = load_session("nonexistent-session")
        assert messages == []

    def test_messages_have_timestamp(self, tmp_history_dir):
        save_message("sess2", "user", "test")
        messages = load_session("sess2")
        assert "timestamp" in messages[0]
        assert messages[0]["timestamp"] > 0

    def test_load_preserves_order(self, tmp_history_dir):
        for i in range(5):
            save_message("sess3", "user", f"message {i}")
        messages = load_session("sess3")
        for i, msg in enumerate(messages):
            assert f"message {i}" in msg["content"]


class TestListSessions:
    def test_returns_sessions(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "user", "First question")
        save_message("2024-01-02_10-00-00", "user", "Second question")
        sessions = list_sessions()
        assert len(sessions) == 2

    def test_sorted_most_recent_first(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "user", "Older question")
        save_message("2024-01-03_10-00-00", "user", "Newer question")
        sessions = list_sessions()
        assert "2024-01-03" in sessions[0]["date"]

    def test_empty_history(self, tmp_history_dir):
        sessions = list_sessions()
        assert sessions == []

    def test_first_question_extracted(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "assistant", "I am ready")
        save_message("2024-01-01_10-00-00", "user", "What is RAG?")
        sessions = list_sessions()
        assert "What is RAG?" in sessions[0]["first_question"]

    def test_respects_limit(self, tmp_history_dir):
        for i in range(10):
            save_message(f"2024-01-{i+1:02d}_10-00-00", "user", f"Q{i}")
        sessions = list_sessions(limit=3)
        assert len(sessions) <= 3


class TestGetLatestSessionId:
    def test_returns_latest(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "user", "old")
        save_message("2024-01-03_10-00-00", "user", "new")
        latest = get_latest_session_id()
        assert "2024-01-03" in latest

    def test_returns_none_when_empty(self, tmp_history_dir):
        assert get_latest_session_id() is None


class TestSearchSessions:
    def test_finds_keyword_in_user_message(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "user", "Tell me about RAG systems")
        results = search_sessions("RAG")
        assert len(results) == 1
        assert "RAG" in results[0]["excerpt"]

    def test_finds_keyword_in_assistant_message(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "assistant", "ChromaDB is a vector database")
        results = search_sessions("ChromaDB")
        assert len(results) == 1

    def test_case_insensitive(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "user", "Tell me about ollama")
        results = search_sessions("OLLAMA")
        assert len(results) == 1

    def test_no_match_returns_empty(self, tmp_history_dir):
        save_message("2024-01-01_10-00-00", "user", "Hello world")
        results = search_sessions("nonexistent_keyword_xyz")
        assert results == []

    def test_one_result_per_session(self, tmp_history_dir):
        # Same keyword appears multiple times in one session
        save_message("2024-01-01_10-00-00", "user", "RAG question 1")
        save_message("2024-01-01_10-00-00", "user", "RAG question 2")
        results = search_sessions("RAG")
        assert len(results) == 1  # deduplicated per session


class TestDeleteAndClear:
    def test_delete_session(self, tmp_history_dir):
        save_message("sess-to-delete", "user", "test")
        assert delete_session("sess-to-delete") is True
        assert load_session("sess-to-delete") == []

    def test_delete_nonexistent(self, tmp_history_dir):
        assert delete_session("nonexistent") is False

    def test_clear_all(self, tmp_history_dir):
        save_message("sess1", "user", "q1")
        save_message("sess2", "user", "q2")
        count = clear_all_history()
        assert count == 2
        assert list_sessions() == []

    def test_clear_empty(self, tmp_history_dir):
        count = clear_all_history()
        assert count == 0
