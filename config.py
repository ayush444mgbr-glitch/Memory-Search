# ─────────────────────────────────────────────────────────
# config.py
# All settings for the memory engine in one place.
# Change things here — nowhere else needs to be touched.
# ─────────────────────────────────────────────────────────

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────

# Where ChromaDB stores your vectors (just a folder on disk)
CHROMA_PATH = "./data/chroma_db"

# The folder watcher.py will watch for new/changed files
# Change this to your actual notes folder, e.g.:
# "/Users/yourname/Documents/Obsidian"
# "/Users/yourname/Desktop/Notes"
WATCH_FOLDER = "./data/notes"

# Supported file types for ingestion
SUPPORTED_EXTENSIONS = [".md", ".txt", ".pdf", ".png", ".jpg", ".jpeg"]


# ── Ollama Models ─────────────────────────────────────────

# Embedding model — converts text → vectors
# Run: ollama pull nomic-embed-text
EMBED_MODEL = "nomic-embed-text"

# Language model — reads chunks and writes answers
# Run: ollama pull llama3.2:3b (FASTEST for most computers)
# Run: ollama pull llama3.1:8b (HIGHER QUALITY but slower)
LLM_MODEL = "llama3.2:3b"

# Vision model — describes images so they become searchable
# Run: ollama pull llava  (optional, only needed for photos)
VISION_MODEL = "llava"


# ── Chunking Settings ─────────────────────────────────────

# How many words per chunk
# 300–500 is the sweet spot. Smaller = more precise but less context.
CHUNK_SIZE = 400

# How many words overlap between consecutive chunks
# Prevents ideas from being cut in half at chunk boundaries
CHUNK_OVERLAP = 50


# ── Search Settings ───────────────────────────────────────

# How many chunks to retrieve per query
# More = richer context for the LLM but slower response
N_RESULTS = 5

# Minimum similarity score to include a result (0.0 to 1.0)
# Results below this are considered irrelevant and dropped
MIN_SIMILARITY = 0.15


# ── UI Settings ───────────────────────────────────────────

APP_TITLE = "🧠 Personal Memory Engine"
APP_ICON = "🧠"
