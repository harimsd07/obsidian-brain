"""
brain/exceptions.py
All custom exceptions with user-friendly messages and fix suggestions.
"""


class BrainError(Exception):
    """Base exception for all brain errors."""
    def __init__(self, message: str, fix: str = ""):
        self.message = message
        self.fix = fix
        super().__init__(message)


class OllamaNotRunning(BrainError):
    def __init__(self):
        super().__init__(
            message="Ollama is not running.",
            fix="Start it with:  ollama serve\nOr switch provider:  export BRAIN_LLM_PROVIDER=groq",
        )


class VaultNotFound(BrainError):
    def __init__(self, path: str):
        super().__init__(
            message=f"Vault not found at: {path}",
            fix="Run:  brain init  to reconfigure your vault path.",
        )


class VaultNotIndexed(BrainError):
    def __init__(self):
        super().__init__(
            message="Vault has not been indexed yet.",
            fix="Run:  brain ingest  to index your vault first.",
        )


class MissingAPIKey(BrainError):
    def __init__(self, provider: str):
        key_name = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}.get(provider, f"{provider.upper()}_API_KEY")
        super().__init__(
            message=f"{key_name} is not set.",
            fix=f"Add it to your .env file:\n  {key_name}=your_key_here\nOr run:  brain init  to reconfigure.",
        )


class EmbeddingFailed(BrainError):
    def __init__(self, reason: str):
        super().__init__(
            message=f"Embedding failed: {reason}",
            fix=(
                "Options:\n"
                "  1. Start Ollama:         ollama serve\n"
                "  2. Use Gemini embedding: export BRAIN_LLM_PROVIDER=gemini\n"
                "  3. Install fallback:     pip install sentence-transformers"
            ),
        )


class ProviderError(BrainError):
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"LLM provider '{provider}' failed: {reason}",
            fix="Check your API key or switch provider:  export BRAIN_LLM_PROVIDER=ollama",
        )


class ChromaError(BrainError):
    def __init__(self, reason: str):
        super().__init__(
            message=f"Database error: {reason}",
            fix="Try re-indexing:  brain ingest --force",
        )
