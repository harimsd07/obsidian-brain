import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# --- Vault ---
VAULT_PATH = Path(os.getenv("BRAIN_VAULT_PATH", "/home/irah/Desktop/Obsidian")).expanduser()

# --- ChromaDB ---
CHROMA_PATH = Path(os.getenv("BRAIN_CHROMA_PATH", "./data/chroma"))
COLLECTION_NAME = "obsidian_notes"

# --- Ollama models ---
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3"

# --- Chunking ---
CHUNK_SIZE = 512        # tokens per chunk
CHUNK_OVERLAP = 64      # overlap between chunks

# --- Retrieval ---
TOP_K = 5               # number of chunks to retrieve per query

# --- Folders to skip inside vault ---
IGNORE_DIRS = {".obsidian", ".trash", "templates", "attachments", "assets"}
IGNORE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".mp4", ".zip"}


LLM_PROVIDER = os.getenv("BRAIN_LLM_PROVIDER", "ollama")

# --- API Keys (set in environment or .env) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Provider-specific model names ---
GROQ_MODEL = "llama-3.3-70b-versatile"       # same model you use in Rudratic
GEMINI_MODEL = "gemini-2.0-flash"  
GEMINI_EMBED_MODEL = "models/text-embedding-004"   # 768 dims, free tier           # free tier, fast
