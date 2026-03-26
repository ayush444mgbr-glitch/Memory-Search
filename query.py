# ─────────────────────────────────────────────────────────
# query.py
# Takes your question, finds the most relevant memory
# chunks, and generates a synthesized answer using the
# local LLM.
#
# Two functions you care about:
#   search(question)  → returns raw chunks with scores
#   ask(question)     → returns a full written answer
#
# Usage (CLI):
#   python query.py
# ─────────────────────────────────────────────────────────

import chromadb
import ollama
import time
from typing import Union, Any

from config import (
    CHROMA_PATH, EMBED_MODEL, LLM_MODEL,
    N_RESULTS, MIN_SIMILARITY
)


# ── Setup ─────────────────────────────────────────────────

def get_collection():
    """Get (or create) the ChromaDB collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        return client.get_or_create_collection(
            name="memory",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        print(f"Error getting collection: {e}")
        return None


# ── Embedding ─────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """
    Embed the query using the same model used during ingestion.

    CRITICAL: Must use the same model as ingest.py.
    Different models live in different vector spaces.
    Mixing them produces garbage results.
    """
    try:
        response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return response["embedding"]
    except Exception as e:
        raise RuntimeError(
            f"Embedding failed: {e}\n"
            f"Is Ollama running? Run: ollama serve\n"
            f"Is the model installed? Run: ollama pull {EMBED_MODEL}"
        )


# ── Search ────────────────────────────────────────────────

def search(question: str, n_results: int = None) -> list[dict]:
    """
    Find the most semantically similar chunks to the question.

    Returns a list of dicts, each with:
        text       — the original chunk text
        source     — which file it came from
        file_path  — full path to the source file
        file_type  — .md, .pdf, .png, quick_note, etc.
        relevance  — similarity score 0.0 to 1.0
        chunk_index — which chunk in the source document

    Example:
        results = search("Who works in biotech?")
        for r in results:
            print(r['relevance'], r['source'], r['text'][:100])
    """
    if n_results is None:
        n_results = N_RESULTS

    collection = get_collection()
    if collection is None or collection.count() == 0:
        return []

    # ⏱️ TIME THE EMBEDDING
    start_embed = time.time()
    q_embedding = get_embedding(question)
    end_embed = time.time()
    embed_duration = end_embed - start_embed

    # ⏱️ TIME THE DB QUERY
    start_query = time.time()
    raw = collection.query(
        query_embeddings=[q_embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"]
    )
    end_query = time.time()
    query_duration = end_query - start_query

    print(f"  ⚡ PERFORMANCE: Embed {embed_duration:.2f}s | DB Search {query_duration:.2f}s")

    results = []
    for doc, meta, distance in zip(
        raw["documents"][0],
        raw["metadatas"][0],
        raw["distances"][0]
    ):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity score: 1 = identical, 0 = unrelated
        similarity = round(1 - (distance / 2), 3)

        # Drop results below the minimum threshold
        if similarity < MIN_SIMILARITY:
            continue

        results.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "file_path": meta.get("file_path", ""),
            "file_type": meta.get("file_type", ""),
            "relevance": similarity,
            "chunk_index": meta.get("chunk_index", 0),
            "total_chunks": meta.get("total_chunks", 1),
            "timestamp": meta.get("timestamp", ""),
        })

    return results


# ── Answer ────────────────────────────────────────────────

def ask(question: str, n_results: int = None, stream: bool = False) -> Union[dict, Any]:
    """
    The full pipeline: question → search → synthesize → answer.

    If stream=True, returns a generator that yields chunks of text.
    If stream=False, returns a dict with the full answer, chunks, and sources.
    """
    # Step 1: Find relevant memory chunks
    chunks = search(question, n_results)

    if not chunks:
        msg = "I don't have anything in memory relevant to that question. Try ingesting some notes first."
        if stream:
            def empty_gen(): yield {"message": {"content": msg}}
            return empty_gen(), []
        return {
            "answer": msg,
            "chunks": [],
            "sources": []
        }

    # Step 2: Build context string from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Memory {i} | Source: {chunk['source']} | Relevance: {chunk['relevance']}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Step 3: Build the prompt
    prompt = f"""You are a personal memory assistant. Your job is to help the user recall information from their own notes, documents, and writings.

RULES:
- Answer using ONLY the memory fragments provided below
- Do NOT mention "Memory 1", "Memory 2", "the fragments", or "according to my memory"
- Do NOT say "Based on the provided fragments..." or similar phrases
- Just provide the information naturally as if you already know it
- If the answer is not in the fragments, say "I don't have that in my memory"
- Be specific — mention names, dates, details from the fragments
- If multiple fragments are relevant, synthesize them into a coherent answer
- Keep your answer focused and direct

MEMORY FRAGMENTS:
{context}

QUESTION: {question}

ANSWER:"""

    # Step 4: Send to local LLM and get answer
    try:
        if stream:
            # Return the generator directly for the UI to consume
            return ollama.chat(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            ), chunks

        print(f"  → Sending request to {LLM_MODEL}...")
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response["message"]["content"].strip()
        print(f"  ✓ Answer received ({len(answer)} chars)")
    except Exception as e:
        print(f"  ✗ LLM error: {e}")
        error_msg = f"LLM error: {e}\nIs Ollama running? Run: ollama serve\nIs the model installed? Run: ollama pull {LLM_MODEL}"
        if stream:
            def error_gen(): yield {"message": {"content": error_msg}}
            return error_gen(), []
        answer = error_msg

    # Step 5: Collect unique source files
    sources = []
    seen = set()
    for chunk in chunks:
        s = chunk["source"]
        if s not in seen:
            seen.add(s)
            sources.append({
                "name": s,
                "path": chunk["file_path"],
                "type": chunk["file_type"]
            })

    return {
        "answer": answer,
        "chunks": chunks,
        "sources": sources
    }


# ── CLI Entry Point ───────────────────────────────────────

if __name__ == "__main__":
    print("🧠 Personal Memory Engine — Query Mode")
    print("Type your question and press Enter. Type 'quit' to exit.\n")

    collection = get_collection()
    if collection is None or collection.count() == 0:
        print("⚠️  No memories found. Run ingest.py first to add some notes.")
        print("   python ingest.py /path/to/your/notes\n")
    else:
        print(f"✓ {collection.count()} memory chunks loaded\n")

    while True:
        try:
            question = input("🔍 Ask: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not question:
            continue
        if question.lower() in ["quit", "exit", "q"]:
            break

        result = ask(question)

        print(f"\n{'─'*60}")
        print(f"ANSWER:\n{result['answer']}")

        if result["sources"]:
            print(f"\nSOURCES:")
            for s in result["sources"]:
                print(f"  • {s['name']}")

        if result["chunks"]:
            print(f"\nTOP CHUNK (relevance {result['chunks'][0]['relevance']}):")
            print(f"  {result['chunks'][0]['text'][:200]}...")

        print(f"{'─'*60}\n")
