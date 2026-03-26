
from query import ask
import sys

def test_ask():
    question = "Who did I meet?"
    print(f"Testing ask with question: {question}")
    try:
        result = ask(question)
        print("--- Result ---")
        print(f"Answer: {result['answer']}")
        print(f"Chunks: {len(result['chunks'])}")
        print(f"Sources: {len(result['sources'])}")
    except Exception as e:
        print(f"✗ Error during ask: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ask()
