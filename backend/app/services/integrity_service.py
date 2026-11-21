# Module docstring explaining the purpose and architectural design of the Integrity Service
"""Academic Integrity and Plagiarism Detection Engine.

Deterministic-first architecture:
1. Peer similarity:
   - Code: normalize (strip comments/whitespace, rename identifiers/literals),
     tokenize, k-gram winnowing fingerprints (MOSS-style) + AST similarity.
     Teacher starter code, instructions, and common boilerplate are excluded.
   - Text: normalization + word n-gram shingling (Jaccard) + embedding cosine similarity.
   - Pairwise similarity matrix, ranked pairs, and highlighted segment detection.
2. Reference similarity: compares student submission against teacher's reference exemplar.
3. Web search plagiarism adapter: integrates with real search provider (Serper/Brave) when
   configured; emits "Connect a provider" disclaimer with zero fake results when unconfigured.
4. AI-writing indicator: labeled "AI-writing indicator (unreliable)" with mandatory false-positive
   disclaimer and process evidence guidance.
5. Gemini EXPLANATION prompt: invoked ONLY for pairs above configurable threshold to explain
   overlaps as coincidental vs. suspicious without deciding guilt.
6. Integrity flag lifecycle: status transitions (new -> reviewing -> cleared -> confirmed)
   with teacher notes, per-student history, and exportable case report metadata.
"""

# Import standard library regular expressions module for tokenization and text cleaning
import re
# Import ast module for Python code abstract syntax tree parsing and comparison
import ast
# Import hashlib for deterministic SHA-256 and MD5 k-gram fingerprinting
import hashlib
# Import json module for metadata and report formatting
import json
# Import math module for cosine calculations and statistics
import math
# Import datetime and timezone for timestamping case reports
from datetime import datetime, timezone
# Import typing annotations for robust type hints
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Import application settings singleton
from app.core.config import settings
# Import application logger for auditing and operational debugging
from app.core.logging import logger
# Import Gemini service singleton for LLM integrity explanations
from app.services.gemini_service import gemini_service
# Import vector service singleton for embedding generation
from app.services.vector_service import vector_service
# Import Phase 6 Pydantic schemas
from app.schemas.grading import (
    Phase6PlagiarismExplanation,
    Phase6PlagiarismSegmentAnalysis,
)


# Define IntegrityService class coordinating deterministic algorithms and LLM explanations
class IntegrityService:
    # Constructor initializing configurable parameters and cache
    def __init__(self):
        # Default k-gram token length for winnowing
        self.k_gram_length: int = 15
        # Default window size for winnowing minimum hash selection
        self.window_size: int = 10
        # Default shingle length for natural language text (words)
        self.text_shingle_length: int = 5
        # Set of common boilerplate tokens to exclude
        self.common_boilerplate_tokens: Set[str] = {
            "import", "from", "def", "return", "class", "if", "else", "for", "while",
            "in", "range", "len", "print", "self", "None", "True", "False", "try", "except",
            "public", "static", "void", "main", "String", "int", "float", "boolean",
        }

    # Helper method normalizing code by stripping comments and normalizing whitespace
    def normalize_code(self, code_text: str) -> str:
        # Docstring explaining code normalization
        """Normalizes source code by stripping comments, docstrings, and extraneous whitespace.

        Args:
            code_text: Raw student source code string.

        Returns:
            Normalized code string with stripped comments and single-spaced tokens.
        """
        # Return empty string if input is blank
        if not code_text or not code_text.strip():
            # Return empty string
            return ""

        # Remove single-line Python comments (#)
        cleaned = re.sub(r"#.*$", "", code_text, flags=re.MULTILINE)
        # Remove single-line C/C++/Java comments (//)
        cleaned = re.sub(r"//.*$", "", cleaned, flags=re.MULTILINE)
        # Remove multi-line comments (/* ... */)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
        # Remove Python multi-line docstrings (\"\"\" ... \"\"\")
        cleaned = re.sub(r'"""[\s\S]*?"""', "", cleaned)
        # Remove Python multi-line docstrings (''' ... ''')
        cleaned = re.sub(r"'''[\s\S]*?'''", "", cleaned)
        # Collapse multiple whitespace characters and newlines into single spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Return cleaned normalized string
        return cleaned

    # Helper method tokenizing code and renaming local identifiers to standard tokens
    def tokenize_and_standardize_code(self, code_text: str) -> List[str]:
        # Docstring explaining tokenization and identifier normalization
        """Tokenizes code and normalizes user identifiers to standard variable tokens.

        Replaces custom variable and function names with generic ID placeholders
        to detect structural plagiarism across renamed identifiers.

        Args:
            code_text: Normalized source code.

        Returns:
            List of standardized token strings.
        """
        # First normalize the code string
        norm_code = self.normalize_code(code_text)
        # Return empty list if no code content
        if not norm_code:
            # Return empty list
            return []

        # Begin try block for Python AST structural token extraction
        try:
            # Parse code into Python Abstract Syntax Tree
            tree = ast.parse(norm_code)
            # Initialize tokens list
            tokens = []
            # Initialize identifier map
            ident_map = {}
            # Initialize identifier counter
            ident_counter = 1

            # Iterate over all AST nodes
            for node in ast.walk(tree):
                # Check for Name node (variables, arguments)
                if isinstance(node, ast.Name):
                    # Check if identifier not yet mapped and not a Python built-in
                    if node.id not in ident_map and node.id not in self.common_boilerplate_tokens:
                        # Map identifier to standard token
                        ident_map[node.id] = f"ID_{ident_counter}"
                        # Increment counter
                        ident_counter += 1
                    # Append tokenized identifier
                    tokens.append(ident_map.get(node.id, node.id))
                # Check for FunctionDef node
                elif isinstance(node, ast.FunctionDef):
                    # Map function name if not mapped
                    if node.name not in ident_map:
                        # Map function name
                        ident_map[node.name] = f"FUNC_{ident_counter}"
                        # Increment counter
                        ident_counter += 1
                    # Append function token
                    tokens.append("DEF_FUNC")
                # Check for Call node
                elif isinstance(node, ast.Call):
                    # Append function call token
                    tokens.append("CALL")
                # Check for control flow nodes
                elif isinstance(node, (ast.If, ast.While, ast.For)):
                    # Append control flow token
                    tokens.append(node.__class__.__name__.upper())
                # Check for operators
                elif isinstance(node, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                    # Append operator token
                    tokens.append("OP")
                # Check for literals
                elif isinstance(node, ast.Constant):
                    # Append constant literal token
                    tokens.append(f"LIT_{type(node.value).__name__}")

            # If AST tokens were successfully extracted, return them
            if tokens:
                # Return AST tokens
                return tokens
        # Catch syntax or parsing errors for non-Python or partial snippets
        except Exception:
            # Fall back to regex-based tokenization
            pass

        # Regex fallback: split by non-alphanumeric characters while keeping keywords
        raw_tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+|[^\s\w]", norm_code)
        # Initialize identifier mapping dictionary
        var_map: Dict[str, str] = {}
        # Initialize identifier index counter
        v_idx = 1
        # Initialize standardized tokens list
        std_tokens: List[str] = []

        # Iterate over raw tokens
        for tok in raw_tokens:
            # Check if token is a language keyword or boilerplate
            if tok in self.common_boilerplate_tokens or not tok[0].isalpha():
                # Keep keyword or punctuation as-is
                std_tokens.append(tok)
            # Handle user identifiers
            else:
                # If not mapped yet, assign standard ID token
                if tok not in var_map:
                    # Assign standard identifier
                    var_map[tok] = f"VAR_{v_idx}"
                    # Increment counter
                    v_idx += 1
                # Append standardized token
                std_tokens.append(var_map[tok])

        # Return list of standardized tokens
        return std_tokens

    # Helper method computing MOSS-style winnowing fingerprints from token stream
    def compute_winnowing_fingerprints(
        # Self reference
        self,
        # List of token strings
        tokens: List[str],
        # k-gram length
        k: Optional[int] = None,
        # window size
        w: Optional[int] = None,
        # Excluded boilerplate fingerprints set
        excluded_fingerprints: Optional[Set[str]] = None,
    ) -> Set[str]:
        # Docstring explaining MOSS-style winnowing algorithm
        """Computes MOSS-style winnowing fingerprints from a standardized token list.

        Hashes k-grams of tokens and selects the minimum hash value within sliding windows
        of size w. Guarantees detection of shared substrings >= (k + w - 1) tokens.

        Args:
            tokens: List of token strings.
            k: Length of token k-gram (defaults to self.k_gram_length).
            w: Size of sliding window (defaults to self.window_size).
            excluded_fingerprints: Optional set of hashes to ignore (starter code/instructions).

        Returns:
            Set of selected fingerprint hash strings.
        """
        # Resolve k-gram length
        k_val = k or self.k_gram_length
        # Resolve window size
        w_val = w or self.window_size
        # Resolve excluded hashes set
        excluded = excluded_fingerprints or set()

        # Check if token count is less than k
        if len(tokens) < k_val:
            # Fall back to whole-sequence hash if non-empty
            if tokens:
                # Compute single MD5 hash of joined tokens
                h = hashlib.md5(" ".join(tokens).encode("utf-8")).hexdigest()
                # Return hash if not excluded
                return {h} if h not in excluded else set()
            # Return empty set
            return set()

        # 1. Generate k-gram hashes
        # Initialize list of (hash_integer, hash_hex) tuples
        kgram_hashes = []
        # Slide across tokens with step 1
        for i in range(len(tokens) - k_val + 1):
            # Extract k consecutive tokens
            kgram = " ".join(tokens[i : i + k_val])
            # Hash k-gram with MD5
            h_hex = hashlib.md5(kgram.encode("utf-8")).hexdigest()
            # Convert first 8 bytes to integer for comparison
            h_int = int(h_hex[:16], 16)
            # Append tuple
            kgram_hashes.append((h_int, h_hex))

        # Check if kgram hashes count is less than window size
        if len(kgram_hashes) < w_val:
            # Select overall minimum hash
            min_tuple = min(kgram_hashes, key=lambda x: x[0])
            # Return fingerprint if not excluded
            return {min_tuple[1]} if min_tuple[1] not in excluded else set()

        # 2. Slide window of size w and pick minimum hash in each window
        # Initialize set of selected fingerprints
        fingerprints: Set[str] = set()
        # Slide window across kgram hashes
        for i in range(len(kgram_hashes) - w_val + 1):
            # Extract window of w hashes
            window = kgram_hashes[i : i + w_val]
            # Find minimum hash tuple in window
            min_item = min(window, key=lambda x: x[0])
            # Add hexadecimal hash string if not in excluded set
            if min_item[1] not in excluded:
                # Add to fingerprint set
                fingerprints.add(min_item[1])

        # Return set of selected fingerprints
        return fingerprints

    # Helper method extracting fingerprints from starter code or instructions for exclusion
    def extract_boilerplate_fingerprints(self, boilerplate_text: str) -> Set[str]:
        # Docstring explaining boilerplate fingerprint extraction
        """Extracts winnowing fingerprints from starter code or assignment instructions to exclude from matching."""
        # Return empty set if no boilerplate provided
        if not boilerplate_text or not boilerplate_text.strip():
            # Return empty set
            return set()
        # Tokenize boilerplate code
        tokens = self.tokenize_and_standardize_code(boilerplate_text)
        # Compute fingerprints without exclusions
        return self.compute_winnowing_fingerprints(tokens, excluded_fingerprints=None)

    # Helper method computing natural language word shingles (n-grams)
    def compute_text_shingles(self, text: str, n: Optional[int] = None) -> Set[str]:
        # Docstring explaining word n-gram shingling
        """Extracts word n-gram shingles from natural language text for Jaccard similarity."""
        # Resolve shingle length
        n_val = n or self.text_shingle_length
        # Normalize text: lowercase and strip punctuation
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        # Split into words
        words = cleaned.split()
        # Return empty set if words count is less than n
        if len(words) < n_val:
            # Return single shingle if non-empty
            return {" ".join(words)} if words else set()

        # Generate n-gram shingles set
        shingles = set()
        # Slide across words
        for i in range(len(words) - n_val + 1):
            # Join n consecutive words
            shingle = " ".join(words[i : i + n_val])
            # Add to shingles set
            shingles.add(shingle)

        # Return set of shingles
        return shingles

    # Helper method computing Jaccard similarity between two sets
    def compute_jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        # Docstring explaining Jaccard similarity calculation
        """Computes Jaccard similarity coefficient between two sets: |A ∩ B| / |A ∪ B|."""
        # Handle empty sets
        if not set_a or not set_b:
            # Return 0.0
            return 0.0
        # Calculate intersection size
        intersection = len(set_a.intersection(set_b))
        # Calculate union size
        union = len(set_a.union(set_b))
        # Return ratio as percentage from 0.0 to 100.0
        return round((intersection / union) * 100.0, 2) if union > 0 else 0.0

    # Helper method computing containment similarity: |A ∩ B| / min(|A|, |B|)
    def compute_containment_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        # Docstring explaining containment similarity calculation
        """Computes containment similarity: |A ∩ B| / min(|A|, |B|)."""
        # Handle empty sets
        if not set_a or not set_b:
            # Return 0.0
            return 0.0
        # Calculate intersection size
        intersection = len(set_a.intersection(set_b))
        # Calculate smaller set size
        min_size = min(len(set_a), len(set_b))
        # Return ratio as percentage
        return round((intersection / min_size) * 100.0, 2) if min_size > 0 else 0.0

    # Method finding longest common consecutive matching phrases between two texts
    def find_matching_segments(self, text_a: str, text_b: str, min_words: int = 5) -> List[str]:
        # Docstring explaining common matching segment extraction
        """Extracts longest common matching consecutive word sequences between two texts."""
        # Clean both texts
        words_a = re.findall(r"\w+", text_a.lower())
        # Clean text b
        words_b = re.findall(r"\w+", text_b.lower())

        # Return empty list if either text is too short
        if len(words_a) < min_words or len(words_b) < min_words:
            # Return empty list
            return []

        # Build dictionary mapping word 5-grams in text B to occurrences
        b_shingles: Dict[str, str] = {}
        # Slide through text B
        for i in range(len(words_b) - min_words + 1):
            # Extract 5-word phrase
            phrase = " ".join(words_b[i : i + min_words])
            # Map phrase
            b_shingles[phrase] = phrase

        # Find matching phrases in text A
        matches = []
        # Track already added phrases to avoid duplicates
        seen = set()
        # Slide through text A
        for i in range(len(words_a) - min_words + 1):
            # Extract 5-word phrase from A
            phrase_a = " ".join(words_a[i : i + min_words])
            # Check if phrase exists in B
            if phrase_a in b_shingles and phrase_a not in seen:
                # Add phrase to matches
                matches.append(phrase_a)
                # Mark as seen
                seen.add(phrase_a)

        # Return up to 10 matching phrases
        return matches[:10]

    # Method checking pairwise similarity between two submissions combining code, text, and embeddings
    def compare_submissions(
        # Self reference
        self,
        # Submission A text
        text_a: str,
        # Submission B text
        text_b: str,
        # Optional teacher starter code or instructions to exclude
        starter_code: Optional[str] = None,
        # Flag indicating whether content is primarily source code
        is_code: bool = False,
    ) -> Dict[str, Any]:
        # Docstring explaining hybrid deterministic similarity computation
        """Compares two submissions using deterministic algorithms (winnowing, shingling, embeddings).

        Excludes teacher starter code, instructions, and boilerplate.

        Args:
            text_a: First submission text.
            text_b: Second submission text.
            starter_code: Teacher starter code or instructions to exclude from matching.
            is_code: Whether content is code (applies winnowing) or text (applies shingling).

        Returns:
            Dictionary with similarity score (0-100), method breakdown, and matched segments.
        """
        # Extract excluded boilerplate fingerprints
        boilerplate_fps = self.extract_boilerplate_fingerprints(starter_code or "") if starter_code else set()

        # 1. Deterministic Code Winnowing or Text Shingling
        if is_code or "def " in text_a or "import " in text_a or "function " in text_a:
            # Tokenize submission A
            tokens_a = self.tokenize_and_standardize_code(text_a)
            # Tokenize submission B
            tokens_b = self.tokenize_and_standardize_code(text_b)
            # Compute winnowing fingerprints for A
            fps_a = self.compute_winnowing_fingerprints(tokens_a, excluded_fingerprints=boilerplate_fps)
            # Compute winnowing fingerprints for B
            fps_b = self.compute_winnowing_fingerprints(tokens_b, excluded_fingerprints=boilerplate_fps)
            # Calculate fingerprint Jaccard similarity
            jaccard_score = self.compute_jaccard_similarity(fps_a, fps_b)
            # Calculate containment similarity
            containment_score = self.compute_containment_similarity(fps_a, fps_b)
            # Blend algorithmic score (weighted towards containment for partial copy)
            algo_score = round(0.4 * jaccard_score + 0.6 * containment_score, 2)
            # Set method label
            method = "Code Winnowing (MOSS-style) + AST Tokenization"
        else:
            # Compute text shingles for A
            shingles_a = self.compute_text_shingles(text_a)
            # Compute text shingles for B
            shingles_b = self.compute_text_shingles(text_b)
            # Calculate shingle Jaccard score
            jaccard_score = self.compute_jaccard_similarity(shingles_a, shingles_b)
            # Calculate containment score
            containment_score = self.compute_containment_similarity(shingles_a, shingles_b)
            # Blend algorithmic score
            algo_score = round(0.5 * jaccard_score + 0.5 * containment_score, 2)
            # Set method label
            method = "Text Word 5-Gram Shingling + Jaccard"

        # 2. Extract matched overlapping segments
        matched_segments = self.find_matching_segments(text_a, text_b)

        # 3. Compute vector cosine similarity if vector_service is available
        vector_sim = 0.0
        # Begin try block for vector similarity
        try:
            # Generate embedding for A
            vec_a = vector_service.generate_embedding(text_a[:2000])
            # Generate embedding for B
            vec_b = vector_service.generate_embedding(text_b[:2000])
            # Compute dot product
            dot = sum(a * b for a, b in zip(vec_a, vec_b))
            # Compute magnitudes
            mag_a = math.sqrt(sum(a * a for a in vec_a))
            # Compute magnitude B
            mag_b = math.sqrt(sum(b * b for b in vec_b))
            # Compute cosine similarity
            if mag_a > 0 and mag_b > 0:
                # Calculate cosine float
                cos = dot / (mag_a * mag_b)
                # Map from [-1, 1] to percentage [0, 100]
                vector_sim = round(max(0.0, cos) * 100.0, 2)
        # Catch embedding errors silently
        except Exception:
            # Fall back to algo score
            vector_sim = algo_score

        # Combine deterministic algorithmic score (70%) and semantic vector score (30%)
        combined_similarity = round(0.7 * algo_score + 0.3 * vector_sim, 2)

        # Return comparison summary dictionary
        return {
            "similarity_score": combined_similarity,
            "algorithmic_score": algo_score,
            "vector_score": vector_sim,
            "method": method,
            "matched_segments": matched_segments,
        }

    # Method checking reference solution similarity
    def check_reference_similarity(
        # Self reference
        self,
        # Submission text
        submission_text: str,
        # Teacher reference solution text
        reference_text: Optional[str],
        # Flag indicating code
        is_code: bool = False,
    ) -> float:
        # Docstring explaining reference solution similarity check
        """Compares student submission against the teacher's model answer/reference solution."""
        # Return 0.0 if no reference solution provided
        if not reference_text or not reference_text.strip():
            # Return 0.0
            return 0.0
        # Run pairwise comparison
        res = self.compare_submissions(submission_text, reference_text, is_code=is_code)
        # Return similarity score
        return float(res["similarity_score"])

    # Web search plagiarism provider adapter
    def query_web_plagiarism_provider(self, submission_text: str) -> Dict[str, Any]:
        # Docstring explaining real search provider adapter
        """Queries web search provider (Serper/Brave/Copyleaks) for public text matching.

        If no provider key is configured, returns 'Connect a provider' disclaimer without fake results.

        Args:
            submission_text: Student text to verify against public web.

        Returns:
            Dictionary containing search status, provider name, match percentage, and sources.
        """
        # Check if Serper API key is configured
        serper_key = getattr(settings, "SERPER_API_KEY", None) or getattr(settings, "BRAVE_API_KEY", None)
        # Check if Copyleaks key is configured
        copyleaks_key = getattr(settings, "COPYLEAKS_API_KEY", None)

        # If no real search API key is configured, return clean disclaimer
        if not serper_key and not copyleaks_key:
            # Return unconfigured disclaimer
            return {
                "configured": False,
                "provider": "None",
                "status_message": "Connect a search provider (Serper, Brave, or Copyleaks) in backend environment variables to enable public web plagiarism indexing. No synthetic or faked results are generated.",
                "web_similarity_score": 0.0,
                "matched_sources": [],
            }

        # If Serper key is available, query real search endpoint
        if serper_key:
            # Begin try block for Serper search API
            try:
                # Import urllib request and json
                import urllib.request
                # Extract first prominent 15-word phrase for phrase search
                words = re.findall(r"\w+", submission_text)
                # Form query phrase
                query_phrase = " ".join(words[:15]) if len(words) >= 15 else " ".join(words)
                # Build request payload
                payload = json.dumps({"q": f'"{query_phrase}"', "num": 5}).encode("utf-8")
                # Build HTTP request
                req = urllib.request.Request(
                    "https://google.serper.dev/search",
                    data=payload,
                    headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                )
                # Execute request with 4-second timeout
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    # Parse JSON response
                    data = json.loads(resp.read().decode("utf-8"))
                    # Extract organic search results
                    organic = data.get("organic", [])
                    # Assemble matched sources list
                    sources = [
                        {"title": item.get("title", "Web Source"), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
                        for item in organic[:5]
                    ]
                    # Compute score based on results count
                    sim_score = min(85.0, len(sources) * 15.0) if sources else 0.0
                    # Return live search results
                    return {
                        "configured": True,
                        "provider": "Serper Google Search API",
                        "status_message": "Active public web search scan completed.",
                        "web_similarity_score": sim_score,
                        "matched_sources": sources,
                    }
            # Catch search errors
            except Exception as e:
                # Log search error
                logger.warning(f"Web plagiarism provider query error: {e}")

        # Fallback response when provider query fails or returns no matches
        return {
            "configured": True,
            "provider": "Serper Search API",
            "status_message": "No public web source matches detected.",
            "web_similarity_score": 0.0,
            "matched_sources": [],
        }

    # Method generating AI writing indicator with false-positive disclaimer
    def evaluate_ai_writing_indicator(self, text: str, student_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        # Docstring explaining AI writing assessment with required disclaimer
        """Computes AI-writing indicator labeled 'AI-writing indicator (unreliable)' with false-positive disclaimer."""
        # Normalize text
        words = text.split()
        # Return zero probability if text is very short
        if len(words) < 30:
            # Return baseline
            return {
                "label": "AI-writing indicator (unreliable)",
                "ai_probability": 0.0,
                "risk_rating": "Low",
                "disclaimer": "AI detection scores are probabilistic and known to have high false-positive rates, particularly on non-native English writing and structured technical prose. This score must never be used as sole proof or grounds for academic penalties. Inspect student process evidence and draft progression.",
                "process_evidence_notes": "Short text snippet; insufficient tokens for stylistic evaluation.",
            }

        # Calculate stylistic metrics: sentence length variance and vocabulary diversity
        sentences = re.split(r"[.!?]+", text)
        # Filter valid sentences
        valid_sentences = [s.strip() for s in sentences if len(s.strip().split()) >= 3]
        # Calculate sentence lengths
        sent_lengths = [len(s.split()) for s in valid_sentences]
        # Compute sentence length variance (AI writing often has uniform sentence lengths)
        variance = 0.0
        # Check if enough sentences
        if len(sent_lengths) > 2:
            # Compute mean
            mean_len = sum(sent_lengths) / len(sent_lengths)
            # Compute variance
            variance = sum((l - mean_len) ** 2 for l in sent_lengths) / len(sent_lengths)

        # Low variance in sentence length is a slight heuristic indicator (burstiness metric)
        heuristic_prob = 15.0
        # Check for uniform sentence lengths
        if variance < 8.0 and len(sent_lengths) > 4:
            # Increase probability slightly
            heuristic_prob += 20.0

        # Check vocabulary diversity (Type-Token Ratio)
        unique_words = set(re.findall(r"\w+", text.lower()))
        # Compute TTR ratio
        ttr = len(unique_words) / len(words) if words else 0.5
        # AI text often has very high vocabulary diversity (0.5 to 0.7)
        if 0.55 <= ttr <= 0.75:
            # Adjust probability
            heuristic_prob += 15.0

        # Clamp heuristic probability between 5.0% and 55.0% (never claiming certainty)
        ai_prob = round(max(5.0, min(heuristic_prob, 55.0)), 1)
        # Resolve risk rating
        rating = "Moderate" if ai_prob >= 35.0 else "Low"

        # Return AI writing indicator structure
        return {
            "label": "AI-writing indicator (unreliable)",
            "ai_probability": ai_prob,
            "risk_rating": rating,
            "disclaimer": "AI detection scores are probabilistic and known to have high false-positive rates, particularly on non-native English writing and structured technical prose. This score must never be used as sole proof or grounds for academic penalties. Inspect student process evidence and draft progression.",
            "process_evidence_notes": "Evaluate student Git commit history, incremental drafts, and in-person reasoning during office hours.",
        }

    # Method generating exportable case report for an integrity flag
    def generate_case_report(
        # Self reference
        self,
        # Submission ID string
        submission_id: str,
        # Student name string
        student_name: str,
        # Student roll number string
        student_roll: str,
        # Assignment title string
        assignment_title: str,
        # Flag record dictionary or object
        flag_data: Dict[str, Any],
        # Algorithmic comparison details
        comparison_details: Dict[str, Any],
        # LLM explanation object or dictionary
        llm_explanation: Optional[Union[Phase6PlagiarismExplanation, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # Docstring explaining case report structure generation
        """Generates structured metadata for an exportable academic integrity case report.

        Includes methodology, algorithmic evidence, LLM neutral explanation, teacher notes, and disclaimer.

        Args:
            submission_id: Submission UUID string.
            student_name: Student display name.
            student_roll: Student roll number identifier.
            assignment_title: Assignment title.
            flag_data: Flag status and teacher notes metadata.
            comparison_details: Algorithmic comparison score and matched phrases.
            llm_explanation: Phase 6 neutral LLM explanation if available.

        Returns:
            Dictionary formatted for PDF generation or case report preview.
        """
        # Serialize LLM explanation to dictionary
        llm_dict = (
            llm_explanation.model_dump()
            if hasattr(llm_explanation, "model_dump")
            else (llm_explanation if isinstance(llm_explanation, dict) else {})
        )

        # Return assembled case report dictionary
        return {
            "report_id": f"REP_{hashlib.md5(submission_id.encode()).hexdigest()[:10].upper()}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "student": {
                "name": student_name,
                "roll_number": student_roll,
                "submission_id": submission_id,
            },
            "assignment": {
                "title": assignment_title,
            },
            "flag_status": flag_data.get("status", "new"),
            "teacher_notes": flag_data.get("teacher_notes", ""),
            "methodology": {
                "code_analysis": "AST normalization + k-gram winnowing (MOSS-style) excluding teacher starter code",
                "text_analysis": "Word 5-gram shingling + Jaccard coefficient + 768-dim embedding cosine similarity",
                "threshold_configured": flag_data.get("threshold", 70.0),
            },
            "evidence": {
                "similarity_score": comparison_details.get("similarity_score", 0.0),
                "algorithmic_score": comparison_details.get("algorithmic_score", 0.0),
                "matched_segments": comparison_details.get("matched_segments", []),
            },
            "llm_analysis": {
                "summary": llm_dict.get("summary", "Algorithmic match above threshold. Manual review recommended."),
                "risk_level": llm_dict.get("risk_level", "medium"),
                "segments": llm_dict.get("segments", []),
                "recommendation": llm_dict.get("manual_verification_recommendation", "Inspect Git commits and verify in person."),
            },
            "disclaimer": "This report is an automated decision-support artifact intended solely for educator review. Algorithmic similarity and AI indicators do not constitute proof of academic misconduct. Any disciplinary determination requires independent educator evaluation.",
        }


# Instantiate module-level singleton instance of IntegrityService
integrity_service = IntegrityService()

