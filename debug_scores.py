
import chromadb
import ollama
from config import CHROMA_PATH, EMBED_MODEL

def check_raw_scores(question):
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_collection("memory")
        
        # Get embedding for the question
        response = ollama.embeddings(model=EMBED_MODEL, prompt=question)
        q_embedding = response["embedding"]
        
        # Query ChromaDB for raw distances
        raw = collection.query(
            query_embeddings=[q_embedding],
            n_results=5,
            include=["documents", "distances"]
        )
        
        print(f"--- Raw Search Debug ---")
        print(f"Query: \"{question}\"\n")
        
        if not raw["documents"] or not raw["documents"][0]:
            print("No documents found in the database.")
            return

        for doc, dist in zip(raw["documents"][0], raw["distances"][0]):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Similarity = 1 - (distance / 2)
            similarity = 1 - (dist / 2)
            status = "PASS" if similarity >= 0.3 else "FAIL (below 0.3 threshold)"
            print(f"Similarity: {similarity:.4f} [{status}]")
            print(f"Document: {doc[:100]}...\n")
            
    except Exception as e:
        print(f"Error during debug: {e}")

if __name__ == "__main__":
    check_raw_scores("Who did I meet?")
