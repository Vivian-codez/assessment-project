# Import module os
import os
# Import module sys
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import VectorService from app.services.vector_service
from app.services.vector_service import VectorService

# Define function run_test
def run_test():
    # Begin try block to handle operations safely
    try:
        # Set vs to VectorService()
        vs = VectorService()
        # Check if condition: vs.client
        if vs.client:
            # Set collections to [c.name for c in vs.client.get_collections().collections]
            collections = [c.name for c in vs.client.get_collections().collections]
            # Print console output: print(f"VectorService successfully connected to collection '{vs.collection_name}'")
            print(f"VectorService successfully connected to collection '{vs.collection_name}'")
            # Print console output: print(f"Active Qdrant collections: {collections}")
            print(f"Active Qdrant collections: {collections}")
            # Print console output: print(f"Vector dimensions: {vs.EMBEDDING_DIM} (Cosine Distance)")
            print(f"Vector dimensions: {vs.EMBEDDING_DIM} (Cosine Distance)")
            # Return value: True
            return True
        # Execute alternate fallback branch
        else:
            # Print console output: print("VectorService client is None.")
            print("VectorService client is None.")
            # Return value: False
            return False
    # Handle exception during execution: except Exception as e
    except Exception as e:
        # Print console output: print(f"VectorService error: {e}")
        print(f"VectorService error: {e}")
        # Return value: False
        return False


# Check if condition: __name__ == "__main__"
if __name__ == "__main__":
    # Set success to run_test()
    success = run_test()
    # Execute statement: sys.exit(0 if success else 1)
    sys.exit(0 if success else 1)
