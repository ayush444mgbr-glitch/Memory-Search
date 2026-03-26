
import chromadb
from config import CHROMA_PATH

def inspect_db():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection("memory")
    results = collection.get(include=["documents", "metadatas"])
    
    print(f"Total chunks: {len(results['ids'])}")
    for i in range(len(results['ids'])):
        print(f"\n--- Chunk {i+1} ---")
        print(f"ID: {results['ids'][i]}")
        print(f"Metadata: {results['metadatas'][i]}")
        print(f"Document: {results['documents'][i][:200]}...")

if __name__ == "__main__":
    inspect_db()
