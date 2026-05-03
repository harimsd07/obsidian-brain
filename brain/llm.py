import ollama
from brain.config import EMBED_MODEL, LLM_MODEL


def embed(text: str) -> list[float]:
    """Generate embedding — always uses Ollama locally."""
    from brain.config import LLM_PROVIDER

    # Try Ollama first (preferred for embeddings)
    try:
        response = ollama.embed(model=EMBED_MODEL, input=text)
        return response["embeddings"][0]
    except Exception as e:
        # Ollama not running — fall back to provider-specific embedding
        if LLM_PROVIDER == "gemini":
            return _embed_gemini(text)
        elif LLM_PROVIDER == "groq":
            return _embed_groq(text)
        else:
            raise ConnectionError(
                "Ollama is not running and no fallback provider configured. "
                "Run 'ollama serve' or set BRAIN_LLM_PROVIDER=gemini/groq"
            ) from e


def _embed_gemini(text: str) -> list[float]:
    """Embed using Gemini text-embedding-004 (free tier, 768 dims)."""
    import google.generativeai as genai
    from brain.config import GEMINI_API_KEY
    genai.configure(api_key=GEMINI_API_KEY)
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


def _embed_groq(text: str) -> list[float]:
    """
    Groq doesn't offer an embedding API.
    Falls back to a lightweight local model or raises a clear error.
    """
    # Try sentence-transformers as fallback (lightweight, no GPU needed)
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model.encode(text).tolist()
    except ImportError:
        raise RuntimeError(
            "Groq has no embedding API. Either:\n"
            "  1. Run 'ollama serve' for local embeddings (recommended)\n"
            "  2. pip install sentence-transformers (lightweight fallback)\n"
            "  3. Set BRAIN_LLM_PROVIDER=gemini which has a free embedding API"
        )


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts."""
    return [embed(t) for t in texts]


def _generate_ollama(messages: list[dict], stream: bool):
    import ollama as _ollama
    if stream:
        response = _ollama.chat(model=LLM_MODEL, messages=messages, stream=True)
        for chunk in response:
            delta = chunk["message"]["content"]
            if delta:
                yield delta
    else:
        response = _ollama.chat(model=LLM_MODEL, messages=messages, stream=False)
        return response["message"]["content"]


def _generate_groq(messages: list[dict], stream: bool):
    from groq import Groq
    from brain.config import GROQ_API_KEY, GROQ_MODEL
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        stream=stream,
    )
    if stream:
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    else:
        return response.choices[0].message.content


def _generate_gemini(messages: list[dict], stream: bool):
    import google.generativeai as genai
    from brain.config import GEMINI_API_KEY, GEMINI_MODEL
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    # Convert OpenAI-style messages to Gemini format
    system_text = ""
    history = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        elif msg["role"] == "user":
            history.append({"role": "user", "parts": [msg["content"]]})
        elif msg["role"] == "assistant":
            history.append({"role": "model", "parts": [msg["content"]]})

    # Prepend system prompt to first user message
    if system_text and history and history[0]["role"] == "user":
        history[0]["parts"][0] = f"{system_text}\n\n{history[0]['parts'][0]}"

    last_user = history.pop()["parts"][0] if history else ""
    chat = model.start_chat(history=history)

    if stream:
        response = chat.send_message(last_user, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    else:
        response = chat.send_message(last_user)
        return response.text


def generate(messages: list[dict], stream: bool = True):
    """
    Route to the correct LLM provider based on BRAIN_LLM_PROVIDER.
    Yields text chunks if stream=True, returns full string if stream=False.
    Falls back to Ollama if provider fails.
    """
    from brain.config import LLM_PROVIDER
    try:
        if LLM_PROVIDER == "groq":
            yield from _generate_groq(messages, stream)
        elif LLM_PROVIDER == "gemini":
            yield from _generate_gemini(messages, stream)
        else:
            yield from _generate_ollama(messages, stream)
    except Exception as e:
        # Fallback to Ollama on any provider error
        from rich.console import Console
        Console().print(f"\n[yellow]Provider '{LLM_PROVIDER}' failed ({e}), falling back to Ollama...[/]")
        yield from _generate_ollama(messages, stream)


def check_ollama_models() -> dict:
    """Check which required models are available locally."""
    try:
        models_resp = ollama.list()
        available = {m["model"] for m in models_resp["models"]}
    except Exception as e:
        return {"ok": False, "error": str(e), "available": [], "missing": []}

    required = {EMBED_MODEL, LLM_MODEL}
    available_base = {m.split(":")[0] for m in available}
    required_base = {m.split(":")[0] for m in required}
    missing = required_base - available_base

    return {
        "ok": len(missing) == 0,
        "available": sorted(available),
        "missing": sorted(missing),
    }


def check_ollama_models() -> dict:
    """Check which required models are available locally."""
    try:
        models_resp = ollama.list()
        available = {m["model"] for m in models_resp["models"]}
    except Exception as e:
        return {"ok": False, "error": str(e), "available": [], "missing": []}

    required = {EMBED_MODEL, LLM_MODEL}
    available_base = {m.split(":")[0] for m in available}
    required_base = {m.split(":")[0] for m in required}
    missing = required_base - available_base

    return {
        "ok": len(missing) == 0,
        "available": sorted(available),
        "missing": sorted(missing),
    }