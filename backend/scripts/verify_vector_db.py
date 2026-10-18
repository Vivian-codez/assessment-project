import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.vector_service import VectorService

def run_test():
    try:
        vs = VectorService()
        if vs.client:
            collections = [c.name for c in vs.client.get_collections().collections]
            print(f"VectorService successfully connected to collection '{vs.collection_name}'")
            print(f"Active Qdrant collections: {collections}")
            print(f"Vector dimensions: {vs.EMBEDDING_DIM} (Cosine Distance)")
            return True
        else:
            print("VectorService client is None.")
            return False
    except Exception as e:
        print(f"VectorService error: {e}")
        return False


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
