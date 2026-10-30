# Module docstring explaining the vector service using Qdrant for peer plagiarism detection
"""Vector Database Service using Qdrant for Peer-to-Peer Plagiarism Detection.

Stores assignment vector embeddings in Qdrant collections (`submissions_{assignment_id}`),
performs cross-submission k-NN queries with cosine similarity (> 0.75),
and generates text embeddings using Google GenAI SDK (text-embedding-004) with
graceful deterministic dense fallback.
"""

# Import math module for sqrt, vector calculations, and normalization
import math
# Import os module for environment and file utilities
import os
# Import re module for regex pattern operations and whitespace normalization
import re
# Import typing utilities for dictionary, list, optional, tuple, and any types
from typing import Dict, List, Optional, Tuple, Any
# Import application configuration settings
from app.core.config import settings
# Import system logger for vector operations logging
from app.core.logging import logger

# Attempt to import Qdrant client and vector data models
try:
    # Import QdrantClient class
    from qdrant_client import QdrantClient
    # Import distance metric, vector parameters, and point structure models
    from qdrant_client.models import Distance, VectorParams, PointStruct
    # Set boolean flag indicating Qdrant library is available
    _QDRANT_AVAILABLE = True
# Catch missing qdrant_client package import error
except ImportError:
    # Set boolean flag indicating Qdrant library is unavailable
    _QDRANT_AVAILABLE = False

# Attempt to import Google GenAI library for generating text embeddings
try:
    # Import google genai module
    from google import genai
    # Set boolean flag indicating Google GenAI library is available
    _GENAI_AVAILABLE = True
# Catch missing google genai package import error
except ImportError:
    # Set boolean flag indicating Google GenAI library is unavailable
    _GENAI_AVAILABLE = False


# Class providing vector embedding generation, Qdrant indexing, and cosine similarity search
class VectorService:
    # Set standard dense embedding dimensionality to 768
    EMBEDDING_DIM = 768

    # Initializer configuring clients and fallback connections
    def __init__(self):
        # Initialize Qdrant client reference to None
        self.client: Optional[QdrantClient] = None
        # Initialize Google GenAI client reference to None
        self.genai_client = None

        # 1. Initialize Google GenAI client for embeddings if library and API key exist
        if _GENAI_AVAILABLE and settings.GEMINI_API_KEY:
            # Wrap client initialization in try-except block
            try:
                # Instantiate Google GenAI client with configured API key
                self.genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
            # Catch and log initialization exceptions
            except Exception as e:
                # Log warning about failure to initialize GenAI client
                logger.warning(f"Could not initialize GenAI Client for embeddings: {e}")

        # 2. Initialize Qdrant Client (remote server or embedded in-memory)
        if _QDRANT_AVAILABLE:
            # Check if configuration requests explicit in-memory database
            if settings.QDRANT_URL == ":memory:":
                # Wrap in-memory initialization in try-except block
                try:
                    # Instantiate embedded in-memory Qdrant client
                    self.client = QdrantClient(":memory:")
                    # Log successful in-memory initialization
                    logger.info("Qdrant client initialized in embedded/in-memory mode (:memory:)")
                # Catch in-memory initialization exceptions
                except Exception as mem_err:
                    # Log error details
                    logger.error(f"Failed to initialize in-memory Qdrant client: {mem_err}")
            # Remote server mode
            else:
                # Attempt to connect to remote Qdrant instance
                try:
                    # Instantiate Qdrant client with URL, API key, and short timeout
                    client = QdrantClient(
                        url=settings.QDRANT_URL,
                        api_key=settings.QDRANT_API_KEY or None,
                        timeout=1.5,
                        check_compatibility=False,
                    )
                    # Test connection probe by requesting collections
                    client.get_collections()
                    # Store connected client reference
                    self.client = client
                    # Log successful remote connection
                    logger.info(f"Qdrant client connected to {settings.QDRANT_URL}")
                # Catch remote connection failures and fallback to in-memory
                except Exception as e:
                    # Log warning about remote connection failure
                    logger.warning(f"Could not connect to Qdrant at {settings.QDRANT_URL} ({e}). Falling back to embedded in-memory Qdrant (:memory:).")
                    # Wrap fallback in-memory client initialization
                    try:
                        # Instantiate fallback embedded in-memory Qdrant client
                        self.client = QdrantClient(":memory:")
                        # Log successful fallback
                        logger.info("Qdrant client fallback to embedded :memory: successful.")
                    # Catch fallback initialization exceptions
                    except Exception as mem_err:
                        # Log fallback error details
                        logger.error(f"In-memory Qdrant fallback failed: {mem_err}")
                        # Set client to None
                        self.client = None

    # Method to format a standard collection name for a given assignment
    def get_collection_name(self, assignment_id: Optional[str] = None) -> str:
        # Method docstring describing collection naming format
        """Returns standard collection name submissions_{assignment_id}."""
        # If an assignment ID is provided, format and sanitize it
        if assignment_id:
            # Sanitize assignment identifier replacing non-alphanumeric characters with underscores
            safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(assignment_id))
            # Return prefixed collection name
            return f"submissions_{safe_id}"
        # Return default collection name from configuration
        return settings.QDRANT_COLLECTION_NAME

    # Method to ensure the target Qdrant collection exists prior to indexing
    def ensure_collection(self, collection_name: Optional[str] = None, assignment_id: Optional[str] = None) -> bool:
        # Method docstring describing collection creation behavior
        """Creates the Qdrant collection if it does not already exist."""
        # Check if Qdrant client is available
        if not self.client:
            # Return False if client is not configured
            return False
        # Resolve collection name from arguments
        col = collection_name or self.get_collection_name(assignment_id)
        # Attempt to inspect and create collection if missing
        try:
            # Fetch list of existing collection names from Qdrant
            collections = [c.name for c in self.client.get_collections().collections]
            # Check if target collection is missing
            if col not in collections:
                # Create collection with 768 dimensions and Cosine distance metric
                self.client.create_collection(
                    collection_name=col,
                    vectors_config=VectorParams(size=self.EMBEDDING_DIM, distance=Distance.COSINE),
                )
                # Log collection creation confirmation
                logger.info(f"Created Qdrant collection '{col}'")
            # Return True indicating collection is ready
            return True
        # Catch and log any errors ensuring the collection
        except Exception as e:
            # Log warning message
            logger.warning(f"Qdrant ensure collection error for '{col}': {e}")
            # Return False on error
            return False

    # Method to generate a normalized 768-dimensional dense vector embedding
    def generate_embedding(self, text: str) -> List[float]:
        # Method docstring describing embedding models and fallback behavior
        """Generates a 768-dimensional normalized dense embedding.

        Uses Google GenAI SDK (text-embedding-004) when available,
        with a deterministic dense vector fallback for offline execution.
        """
        # Collapse multiple whitespace characters into single spaces and truncate to 8000 characters
        clean = re.sub(r"\s+", " ", text or "").strip()[:8000]
        # Check if cleaned text is empty
        if not clean:
            # Return uniformly normalized default dense vector
            return [1.0 / math.sqrt(self.EMBEDDING_DIM)] * self.EMBEDDING_DIM

        # 1. Try Google GenAI SDK embedding
        if self.genai_client:
            # Iterate through candidate embedding models
            for model_name in ["text-embedding-004", "gemini-embedding-001"]:
                # Attempt to call GenAI embedding API
                try:
                    # Invoke embed_content on models endpoint
                    res = self.genai_client.models.embed_content(
                        model=model_name,
                        contents=clean,
                    )
                    # Check if embeddings were successfully returned
                    if res and res.embeddings:
                        # Extract the float values array
                        emb = res.embeddings[0].values
                        # Check if embedding dimension matches exactly 768
                        if len(emb) == self.EMBEDDING_DIM:
                            # Return embedding as a standard float list
                            return list(emb)
                        # Truncate if embedding is larger than 768
                        elif len(emb) > self.EMBEDDING_DIM:
                            # Slice first 768 dimensions
                            emb = emb[:self.EMBEDDING_DIM]
                            # Compute Euclidean L2 norm
                            norm = math.sqrt(sum(v * v for v in emb)) or 1.0
                            # Return L2 normalized vector
                            return [v / norm for v in emb]
                        # Pad with zeros if embedding is smaller than 768
                        else:
                            # Pad missing dimensions with zeros
                            emb = emb + [0.0] * (self.EMBEDDING_DIM - len(emb))
                            # Compute Euclidean L2 norm
                            norm = math.sqrt(sum(v * v for v in emb)) or 1.0
                            # Return L2 normalized vector
                            return [v / norm for v in emb]
                # Catch API call exceptions and try next model
                except Exception as e:
                    # Log debug notification for embedding API attempt
                    logger.debug(f"GenAI embedding call for {model_name} notice: {e}")

        # 2. Fast deterministic 768-dim semantic hashing vector fallback
        dim = self.EMBEDDING_DIM
        # Initialize zeroed vector with dimension 768
        vec = [0.0] * dim

        # Tokenize text into lowercase words
        words = clean.lower().split()
        # Check if words list is empty
        if not words:
            # Return uniformly normalized default dense vector
            return [1.0 / math.sqrt(dim)] * dim

        # Iterate over words and compute semantic hash projections
        for i, word in enumerate(words):
            # Compute hash integer of word
            h = hash(word)
            # Derive primary projection index using XOR bitmask
            pos_1 = (h ^ 0x55555555) % dim
            # Derive secondary projection index using inverted XOR bitmask
            pos_2 = (h ^ 0xAAAAAAAA) % dim
            # Calculate position weight diminishing with word distance
            weight = 1.0 + (1.0 / (1.0 + 0.1 * i))
            # Accumulate positive weight at primary index
            vec[pos_1] += weight
            # Accumulate negative contrast weight at secondary index
            vec[pos_2] -= weight * 0.5

        # Calculate Euclidean L2 norm across all dimensions
        norm = math.sqrt(sum(v * v for v in vec))
        # Normalize vector if Euclidean norm is greater than zero
        if norm > 0:
            # Scale each dimension by the norm
            vec = [v / norm for v in vec]
        # Otherwise if norm is zero, fallback to uniform vector
        else:
            # Assign uniformly normalized values
            vec = [1.0 / math.sqrt(dim)] * dim

        # Return computed deterministic dense vector
        return vec

    # Method to index a submission text directly by computing and saving its vector
    def index_submission(
        self,
        # Unique identifier of the submission
        submission_id: str,
        # Unique identifier of the assignment
        assignment_id: str,
        # Raw extracted text of the submission
        text: str,
        # Optional metadata payload
        payload: Optional[Dict[str, Any]] = None,
    # Return True on success, False otherwise
    ) -> bool:
        # Method docstring describing indexing behavior
        """Indexes a submission's vector embedding into Qdrant collection `submissions_{assignment_id}`."""
        # Generate dense vector embedding from text
        vector = self.generate_embedding(text)
        # Delegate storage to upsert_submission_vector
        return self.upsert_submission_vector(
            submission_id=submission_id,
            assignment_id=assignment_id,
            vector=vector,
            payload=payload,
        )

    # Method to upsert a precomputed vector into the assignment's Qdrant collection
    def upsert_submission_vector(
        self,
        # Unique identifier of the submission
        submission_id: str,
        # Unique identifier of the assignment
        assignment_id: str,
        # Precomputed float embedding vector
        vector: List[float],
        # Optional metadata payload dictionary
        payload: Optional[Dict[str, Any]] = None,
    # Return True on success, False otherwise
    ) -> bool:
        # Method docstring describing upsert behavior
        """Upserts precomputed vector into Qdrant collection `submissions_{assignment_id}`."""
        # Resolve target collection name
        collection_name = self.get_collection_name(assignment_id)
        # Ensure collection exists before inserting points
        self.ensure_collection(collection_name)

        # Make a copy of the payload or initialize an empty dictionary
        point_payload = payload.copy() if payload else {}
        # Update payload with core submission and assignment identifiers
        point_payload.update({
            "submission_id": submission_id,
            "assignment_id": assignment_id,
        })

        # Check if Qdrant client is initialized
        if self.client:
            # Wrap insertion in try-except block
            try:
                # Convert string ID to positive 63-bit integer point id for Qdrant compatibility
                point_id = abs(hash(submission_id)) % (2**63 - 1)
                # Execute upsert call on Qdrant client
                self.client.upsert(
                    collection_name=collection_name,
                    points=[
                        PointStruct(
                            id=point_id,
                            vector=vector,
                            payload=point_payload,
                        )
                    ],
                )
                # Log successful vector indexing
                logger.info(f"Indexed submission vector {submission_id} in Qdrant collection {collection_name}")
                # Return True on success
                return True
            # Catch and log upsert errors
            except Exception as e:
                # Log error details
                logger.error(f"Error upserting vector into Qdrant for {submission_id}: {e}")

        # Return False if client is missing or error occurred
        return False

    # Method to query Qdrant for peer submissions exceeding cosine similarity threshold
    def search_peer_similarity(
        self,
        # Target submission identifier
        submission_id: str,
        # Target assignment identifier
        assignment_id: str,
        # Target embedding vector
        vector: List[float],
        # Cosine similarity threshold, defaulting to 0.75
        threshold: float = 0.75,
        # Maximum number of peer matches to return, defaulting to 10
        limit: int = 10,
    # Return list of matching peer submission dictionaries
    ) -> List[Dict[str, Any]]:
        # Method docstring describing peer-to-peer similarity query
        """Queries Qdrant to detect peer-to-peer similarity (> threshold, e.g. 0.75)

        against already-evaluated student submissions in `submissions_{assignment_id}`.
        """
        # Resolve collection name for this assignment
        collection_name = self.get_collection_name(assignment_id)
        # Ensure collection exists
        self.ensure_collection(collection_name)

        # Initialize empty list to accumulate matches
        matches: List[Dict[str, Any]] = []
        # Return empty list if Qdrant client is not available
        if not self.client:
            # Return empty list
            return matches

        # Wrap search in try-except block
        try:
            # Query Qdrant using query_points API if supported by installed version
            if hasattr(self.client, "query_points"):
                # Execute query_points call with vector and threshold
                query_res = self.client.query_points(
                    collection_name=collection_name,
                    query=vector,
                    limit=limit,
                    score_threshold=threshold,
                )
                # Extract scored points list
                results = query_res.points
            # Otherwise use search API for earlier versions
            elif hasattr(self.client, "search"):
                # Execute search call with vector and threshold
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=vector,
                    limit=limit,
                    score_threshold=threshold,
                )
            # Fallback to empty results if neither method exists
            else:
                # Empty results list
                results = []

            # Iterate through search result hits
            for hit in results:
                # Extract payload dictionary or default to empty dict
                hit_payload = hit.payload or {}
                # Extract peer submission identifier
                peer_sub_id = hit_payload.get("submission_id")
                # Ensure we do not match the target submission against itself
                if peer_sub_id and str(peer_sub_id) != str(submission_id):
                    # Convert cosine score to rounded percentage
                    sim_pct = round(float(hit.score) * 100.0, 1)
                    # Append match record dictionary to matches list
                    matches.append({
                        "submission_id": peer_sub_id,
                        "similarity_score": sim_pct,
                        "cosine_score": float(hit.score),
                        "file_name": hit_payload.get("file_name", ""),
                        "student_name": hit_payload.get("student_name", "Peer"),
                        "status": "High similarity" if hit.score >= 0.75 else "Within range",
                    })
        # Catch and log any search errors
        except Exception as e:
            # Log warning with error details
            logger.warning(f"Qdrant peer search notice for {collection_name}: {e}")

        # Return list of detected peer matches
        return matches

    # Method to run peer-to-peer cross-submission similarity checks across an entire batch in memory
    def check_cross_submission_similarity(
        self,
        # Submission ID to compare
        submission_id: str,
        # Assignment ID
        assignment_id: str,
        # Text content of primary submission
        text: str,
        # List of all other submission dictionaries in the batch
        all_submissions_in_batch: List[Dict],
        # Percentage threshold for flagging, defaulting to 75.0%
        threshold: float = 75.0,
    # Return list of pairwise match dictionaries
    ) -> List[Dict]:
        # Method docstring describing batch cross-submission comparison
        """Runs peer-to-peer cross-submission similarity checks across batch."""
        # Initialize empty list to accumulate pairwise matches
        matches = []
        # Generate dense vector embedding for primary text
        vec_a = self.generate_embedding(text)

        # Iterate through all peer submissions in the batch
        for peer in all_submissions_in_batch:
            # Extract peer submission ID
            peer_id = peer["id"]
            # Skip comparing submission to itself
            if peer_id == submission_id:
                # Continue to next peer
                continue

            # Retrieve text content of peer submission
            peer_text = peer.get("text", "")
            # Generate dense vector embedding for peer text
            vec_b = self.generate_embedding(peer_text)

            # Compute dot product cosine similarity between vector A and vector B
            cos_sim = sum(a * b for a, b in zip(vec_a, vec_b))
            # Convert cosine score to clamped percentage between 0.0 and 100.0
            similarity_pct = max(0.0, min(100.0, round(cos_sim * 100.0, 1)))

            # Search for shared verbatim n-gram phrases between both texts
            shared_phrases = self.find_matching_phrases(text, peer_text)
            # If shared phrases exist and score is below 85, boost similarity score proportionally
            if shared_phrases and similarity_pct < 85.0:
                # Add 5% per matching phrase up to 100% max
                similarity_pct = min(100.0, similarity_pct + len(shared_phrases) * 5.0)

            # Determine qualitative status based on threshold comparison
            status = "High similarity" if similarity_pct >= threshold else "Within range"

            # Check if similarity meets minimum threshold of 35% for reporting
            if similarity_pct >= 35.0:
                # Append pairwise comparison result dictionary
                matches.append({
                    "submission_a_id": submission_id,
                    "submission_b_id": peer_id,
                    "student_a_name": peer.get("student_a_name", "Student A"),
                    "student_b_name": peer.get("student_b_name", "Student B"),
                    "similarity_score": similarity_pct,
                    "matching_phrases": shared_phrases,
                    "status": status,
                })

        # Return matches sorted in descending order by similarity score
        return sorted(matches, key=lambda x: x["similarity_score"], reverse=True)

    # Method to locate matching verbatim n-gram phrases between two texts
    def find_matching_phrases(self, text_a: str, text_b: str, min_words: int = 5) -> List[str]:
        # Method docstring describing n-gram matching logic
        """Finds verbatim or near-verbatim matching phrases between two texts."""
        # Return empty list if either text is blank
        if not text_a or not text_b:
            # Return empty list
            return []

        # Helper function to extract set of lowercase n-gram phrases from a text string
        def get_ngrams(s: str, n: int) -> set:
            # Tokenize string into word tokens
            words = re.findall(r"\b\w+\b", s.lower())
            # Generate set of space-joined sliding window n-grams
            return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}

        # Extract n-grams of size min_words for text A
        ngrams_a = get_ngrams(text_a, min_words)
        # Extract n-grams of size min_words for text B
        ngrams_b = get_ngrams(text_b, min_words)
        # Find intersecting n-grams common to both texts
        common = list(ngrams_a.intersection(ngrams_b))

        # Initialize formatted results list
        results = []
        # Take up to 3 common phrases for display
        for phrase in common[:3]:
            # Format phrase enclosed in quotation marks and ellipses
            results.append(f"“…{phrase}…”")

        # Return formatted phrase list
        return results


# Instantiate singleton vector service instance for backend operations
vector_service = VectorService()
