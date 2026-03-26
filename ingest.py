# ─────────────────────────────────────────────────────────
# ingest.py
# Turns any file into stored vectors in ChromaDB.
#
# Supports: .txt, .md, .pdf, .png, .jpg, .jpeg
#
# Usage:
#   python ingest.py                        ← ingest WATCH_FOLDER
#   python ingest.py /path/to/folder        ← ingest a specific folder
#   python ingest.py /path/to/file.pdf      ← ingest a single file
# ─────────────────────────────────────────────────────────

import sys
import hashlib
from pathlib import Path

import chromadb
import ollama
import pypdf
from PIL import Image

from config import (
    CHROMA_PATH, WATCH_FOLDER, SUPPORTED_EXTENSIONS,
    EMBED_MODEL, VISION_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
)


# ── Setup ChromaDB ────────────────────────────────────────

def get_collection():
    """Get (or create) the ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name="memory",
        metadata={"hnsw:space": "cosine"}
    )
    return collection


# ── Text Utilities ────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks of CHUNK_SIZE words.

    Why overlapping? So ideas that fall on a boundary between
    two chunks still appear fully in at least one of them.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk = " ".join(words[i : i + CHUNK_SIZE])
        if chunk.strip():
            chunks.append(chunk)

    return chunks


def file_hash(path: str) -> str:
    """
    Generate an MD5 fingerprint of a file.
    Used to skip files that have already been ingested.
    """
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def make_chunk_id(source: str, chunk_index: int, chunk_text: str) -> str:
    """Create a unique, stable ID for a chunk."""
    raw = f"{source}_{chunk_index}_{chunk_text[:40]}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Embedding ─────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """
    Convert text → vector using local Ollama.

    The model (nomic-embed-text) converts the meaning of the
    text into 768 numbers. Similar meanings → similar numbers.
    """
    try:
        response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"  ✗ Embedding failed: {e}")
        print(f"    Is Ollama running? Run: ollama serve")
        print(f"    Is the model installed? Run: ollama pull {EMBED_MODEL}")
        raise


# ── Text Extraction ───────────────────────────────────────

def extract_text_from_txt(path: str) -> str:
    """Read a plain text or markdown file."""
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def extract_text_from_pdf(path: str) -> str:
    """
    Extract all text from a PDF file.
    Works for text-based PDFs. Scanned PDFs need OCR (see image handling).
    """
    try:
        reader = pypdf.PdfReader(str(path))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(f"[Page {i+1}]\n{text}")
        return "\n\n".join(pages_text)
    except Exception as e:
        print(f"  ✗ PDF extraction failed: {e}")
        return ""


def extract_text_from_image(path: str) -> str:
    """
    Extract text from an image using two strategies:

    Strategy 1 — OCR (pytesseract):
        If the image contains typed/printed text (screenshot,
        whiteboard photo, scanned document, business card),
        Tesseract reads the text directly.

    Strategy 2 — Vision model (LLaVA):
        If OCR finds very little text, use the LLaVA vision
        model to generate a full description of the image.
        This makes photos searchable even with no text in them.
    """
    text = ""

    # Strategy 1: OCR
    try:
        import pytesseract
        img = Image.open(path)
        ocr_text = pytesseract.image_to_string(img).strip()
        if len(ocr_text) > 50:
            print(f"  → OCR found text ({len(ocr_text)} chars)")
            text = ocr_text
    except ImportError:
        print("  → pytesseract not installed, skipping OCR")
    except Exception as e:
        print(f"  → OCR failed: {e}")

    # Strategy 2: Vision model (if OCR found little/nothing)
    if len(text) < 50:
        try:
            print(f"  → Running vision model (LLaVA) to describe image...")
            response = ollama.chat(
                model=VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": "Describe this image in detail. Include what you see, any text visible, the setting, people if present, objects, and any notable details. Be thorough.",
                    "images": [str(path)]
                }]
            )
            vision_text = response["message"]["content"]
            text = f"[Image description by AI]\n{vision_text}"
            print(f"  → Vision model described image ({len(vision_text)} chars)")
        except Exception as e:
            print(f"  → Vision model failed (is LLaVA installed? Run: ollama pull llava): {e}")
            # Fallback: store the file path so it's at least findable
            text = f"[Image file: {Path(path).name}] — Install LLaVA for auto-description: ollama pull llava"

    return text


# ── Core Ingest Functions ─────────────────────────────────

def ingest_text(
    text: str,
    source: str,
    metadata: dict = None,
    collection=None
):
    """
    Core function. Takes raw text and stores it in ChromaDB.

    Steps:
    1. Split into overlapping chunks
    2. For each chunk: check if already stored (skip if so)
    3. Get embedding from Ollama
    4. Store (id, vector, text, metadata) in ChromaDB
    """
    if collection is None:
        collection = get_collection()

    if metadata is None:
        metadata = {}

    text = text.strip()
    if not text:
        print(f"  ✗ Empty text, skipping {source}")
        return 0

    chunks = chunk_text(text)
    if not chunks:
        return 0

    stored = 0
    for i, chunk in enumerate(chunks):
        chunk_id = make_chunk_id(source, i, chunk)

        # Skip if this exact chunk is already in the database
        existing = collection.get(ids=[chunk_id])
        if existing["ids"]:
            continue

        # Get embedding from Ollama
        embedding = get_embedding(chunk)

        # Store everything together
        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{
                "source": source,
                "chunk_index": i,
                "total_chunks": len(chunks),
                **metadata
            }]
        )
        stored += 1

    if stored > 0:
        print(f"  ✓ Stored {stored} new chunks from {source}")
    else:
        print(f"  ↩ Already ingested: {source}")

    return stored


def ingest_file(path: str, collection=None) -> int:
    """
    Ingest a single file into the memory engine.

    Handles: .txt, .md, .pdf, .png, .jpg, .jpeg
    Skips:   already-ingested files (checks by MD5 hash)
    Returns: number of new chunks stored
    """
    if collection is None:
        collection = get_collection()

    path = Path(path)

    # Check file exists
    if not path.exists():
        print(f"✗ File not found: {path}")
        return 0

    # Check file type is supported
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return 0

    print(f"\n📄 Ingesting: {path.name}")

    # Check if file has already been ingested (by content hash)
    # This prevents re-ingesting the same file even if renamed
    fhash = file_hash(str(path))
    existing = collection.get(where={"file_hash": fhash})
    if existing["ids"]:
        print(f"  ↩ Already ingested (content unchanged): {path.name}")
        return 0

    # Extract text based on file type
    suffix = path.suffix.lower()

    if suffix in [".txt", ".md"]:
        text = extract_text_from_txt(str(path))

    elif suffix == ".pdf":
        text = extract_text_from_pdf(str(path))

    elif suffix in [".png", ".jpg", ".jpeg"]:
        text = extract_text_from_image(str(path))

    else:
        print(f"  ✗ Unsupported file type: {suffix}")
        return 0

    if not text.strip():
        print(f"  ✗ No text extracted from {path.name}")
        return 0

    # Ingest the extracted text
    return ingest_text(
        text=text,
        source=path.name,
        metadata={
            "file_path": str(path.resolve()),
            "file_hash": fhash,
            "file_type": suffix,
        },
        collection=collection
    )


def ingest_folder(folder_path: str) -> int:
    """
    Ingest all supported files in a folder (recursively).
    Returns total number of new chunks stored.
    """
    folder = Path(folder_path)

    if not folder.exists():
        print(f"✗ Folder not found: {folder_path}")
        print(f"  Create it first or update WATCH_FOLDER in config.py")
        return 0

    # Find all supported files recursively
    all_files = []
    for ext in SUPPORTED_EXTENSIONS:
        all_files.extend(folder.rglob(f"*{ext}"))

    if not all_files:
        print(f"No supported files found in {folder_path}")
        print(f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}")
        return 0

    print(f"Found {len(all_files)} files in {folder_path}")
    print(f"Ingesting...\n")

    # Use one collection connection for the whole batch (faster)
    collection = get_collection()
    total = 0

    for f in all_files:
        total += ingest_file(str(f), collection=collection)

    print(f"\n✅ Done. Stored {total} new chunks from {len(all_files)} files.")
    return total


def ingest_quick_note(text: str, tag: str = "") -> int:
    """
    Ingest a quick note typed directly in the UI or Telegram bot.
    No file involved — just raw text.
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    source = f"quick_note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return ingest_text(
        text=text,
        source=source,
        metadata={
            "file_type": "quick_note",
            "timestamp": timestamp,
            "tag": tag
        }
    )


def get_stats() -> dict:
    """Return basic stats about what's stored in the database."""
    collection = get_collection()
    count = collection.count()

    # Get unique sources
    if count > 0:
        results = collection.get(include=["metadatas"])
        sources = set()
        for meta in results["metadatas"]:
            sources.add(meta.get("source", "unknown"))
    else:
        sources = set()

    return {
        "total_chunks": count,
        "total_sources": len(sources),
        "sources": sorted(sources)
    }


# ── CLI Entry Point ───────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        path = Path(target)
        if path.is_dir():
            ingest_folder(target)
        elif path.is_file():
            ingest_file(target)
        else:
            print(f"✗ Not a valid file or folder: {target}")
    else:
        # Default: ingest the configured watch folder
        print(f"Ingesting default folder: {WATCH_FOLDER}")
        ingest_folder(WATCH_FOLDER)
