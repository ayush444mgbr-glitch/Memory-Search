
import chromadb
import ollama
from config import CHROMA_PATH, EMBED_MODEL, LLM_MODEL

def diagnostic():
    print("--- Diagnostic Report ---")
    
    # 1. Check ChromaDB
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_collection("memory")
        count = collection.count()
        print(f"✓ ChromaDB connected. Chunks in 'memory' collection: {count}")
    except Exception as e:
        print(f"✗ ChromaDB error: {e}")

    # 2. Check Ollama Connection & Embedding Model
    try:
        ollama.list()
        print("✓ Ollama service is running.")
    except Exception as e:
        print(f"✗ Ollama service is NOT running: {e}")
        return

    # 3. Check specific models
    try:
        raw_models = ollama.list()['models']
        models = []
        for m in raw_models:
            # Handle both dictionary and attribute access
            if hasattr(m, 'name'):
                models.append(m.name)
            elif isinstance(m, dict) and 'name' in m:
                models.append(m['name'])
            elif hasattr(m, 'model'): # Some versions use .model
                models.append(m.model)
    except Exception as e:
        print(f"✗ Failed to list models: {e}")
        return
    
    if any(EMBED_MODEL in m for m in models):
        print(f"✓ Embedding model '{EMBED_MODEL}' is installed.")
    else:
        print(f"✗ Embedding model '{EMBED_MODEL}' is MISSING. Run: ollama pull {EMBED_MODEL}")

    if any(LLM_MODEL in m for m in models):
        print(f"✓ LLM model '{LLM_MODEL}' is installed.")
    else:
        print(f"✗ LLM model '{LLM_MODEL}' is MISSING. Run: ollama pull {LLM_MODEL}")

if __name__ == "__main__":
    diagnostic()
