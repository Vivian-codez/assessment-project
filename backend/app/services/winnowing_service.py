"""MOSS-style Winnowing Peer Similarity Service.

Specifications:
- Excludes the submission itself from its peer pool.
- Duplicate detection: Identical file hash (SHA-256) or identical normalized text is flagged as 'Duplicate upload', NOT counted as plagiarism.
- Guard: If either document has fewer than 50 tokens or fewer than 10 fingerprints, returns None ('N/A').
- Boilerplate elimination: Strips assignment prompt, reference solution, common student headers, and subtracts fingerprints appearing in >80% of submissions in the batch.
- Algorithm: Winnowing with k-gram (k=5 tokens, window w=4) on normalized text.
- Similarity metric: Containment similarity = |A ∩ B| / min(|A|, |B|).
- Batch size: Requires >= 2 distinct submissions; otherwise returns None ('N/A').
"""

import re
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from app.core.logging import logger


class WinnowingService:
    def __init__(self, k: int = 5, w: int = 4):
        self.k: int = k
        self.w: int = w

    def normalize_text(self, text: str) -> str:
        """Normalizes text by removing headers, punctuation, and collapsing whitespace."""
        if not text:
            return ""
        # Remove typical student header lines: Name:, Roll:, PRN:, Subject:, Class:, Date:
        cleaned = re.sub(
            r"(?i)^(name|roll|prn|subject|class|assignment|date|student|faculty)\s*[:=-].*$",
            "",
            text,
            flags=re.MULTILINE,
        )
        # Lowercase
        cleaned = cleaned.lower()
        # Keep alphanumeric characters and whitespace
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        # Collapse multiple whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def tokenize(self, text: str) -> List[str]:
        """Splits normalized text into word tokens."""
        norm = self.normalize_text(text)
        if not norm:
            return []
        return norm.split()

    def compute_fingerprints(
        self,
        tokens: List[str],
        excluded_fingerprints: Optional[Set[int]] = None,
    ) -> Set[int]:
        """Computes MOSS-style winnowing fingerprints from token stream."""
        excluded = excluded_fingerprints or set()
        if len(tokens) < self.k:
            return set()

        # 1. Generate k-gram hashes
        kgram_hashes: List[int] = []
        for i in range(len(tokens) - self.k + 1):
            kgram = " ".join(tokens[i : i + self.k])
            # Hash to 64-bit integer
            h = int(hashlib.md5(kgram.encode("utf-8")).hexdigest()[:16], 16)
            kgram_hashes.append(h)

        if len(kgram_hashes) < self.w:
            min_h = min(kgram_hashes)
            return {min_h} if min_h not in excluded else set()

        # 2. Slide window of size w and pick minimum hash
        fingerprints: Set[int] = set()
        for i in range(len(kgram_hashes) - self.w + 1):
            window = kgram_hashes[i : i + self.w]
            min_h = min(window)
            if min_h not in excluded:
                fingerprints.add(min_h)

        return fingerprints

    def compute_pairwise_similarity(
        self,
        fps_a: Set[int],
        fps_b: Set[int],
        tokens_a_len: int,
        tokens_b_len: int,
    ) -> Optional[float]:
        """Computes containment similarity: |A ∩ B| / min(|A|, |B|).

        Returns None if either document has < 50 tokens or < 10 fingerprints.
        """
        if tokens_a_len < 50 or tokens_b_len < 50:
            return None
        if len(fps_a) < 10 or len(fps_b) < 10:
            return None

        intersection = len(fps_a.intersection(fps_b))
        min_size = min(len(fps_a), len(fps_b))
        if min_size == 0:
            return 0.0

        ratio = (intersection / min_size) * 100.0
        return round(ratio, 1)

    def analyze_batch(
        self,
        submissions: List[Dict[str, Any]],
        reference_text: Optional[str] = None,
        assignment_prompt: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Analyzes an entire assignment batch and computes per-submission peer similarity.

        submissions: list of dicts with keys:
          - id: str
          - text: str
          - file_hash: Optional[str]
          - file_name: Optional[str]
          - student_name: Optional[str]

        Returns dict mapping submission_id -> {
          - similarity_score: Optional[float] (0-100 or None for N/A)
          - is_duplicate: bool
          - duplicate_of: Optional[str]
          - fingerprints_count: int
          - tokens_count: int
          - compared_peers_count: int
          - matched_fingerprints_count: int
          - top_match_peer_id: Optional[str]
          - top_match_file_name: Optional[str]
          - explanation: str
        }
        """
        results: Dict[str, Dict[str, Any]] = {}
        valid_items = []

        # 1. Pre-process each submission
        for s in submissions:
            sid = s["id"]
            raw_text = s.get("text") or ""
            tokens = self.tokenize(raw_text)
            norm_hash = hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest() if tokens else ""
            raw_hash = s.get("file_hash") or hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

            results[sid] = {
                "similarity_score": None,
                "is_duplicate": False,
                "duplicate_of": None,
                "fingerprints_count": 0,
                "tokens_count": len(tokens),
                "compared_peers_count": 0,
                "matched_fingerprints_count": 0,
                "top_match_peer_id": None,
                "top_match_file_name": None,
                "explanation": "",
                "_tokens": tokens,
                "_norm_hash": norm_hash,
                "_raw_hash": raw_hash,
                "_file_name": s.get("file_name", ""),
            }
            if len(tokens) >= 50:
                valid_items.append(s)

        # 2. Check for duplicate uploads (identical file hash or identical normalized text)
        seen_hashes: Dict[str, str] = {}
        for s in submissions:
            sid = s["id"]
            nh = results[sid]["_norm_hash"]
            rh = results[sid]["_raw_hash"]
            key = rh or nh
            if not key or results[sid]["tokens_count"] < 10:
                continue
            if key in seen_hashes:
                original_id = seen_hashes[key]
                results[sid]["is_duplicate"] = True
                results[sid]["duplicate_of"] = original_id
                results[sid]["similarity_score"] = None  # Duplicates do not count as plagiarism
                results[sid]["explanation"] = f"Duplicate upload of submission '{original_id}'"
            else:
                seen_hashes[key] = sid

        # 3. Extract boilerplate fingerprints from reference solution and assignment prompt
        boilerplate_fps: Set[int] = set()
        if reference_text:
            ref_tokens = self.tokenize(reference_text)
            boilerplate_fps.update(self.compute_fingerprints(ref_tokens))
        if assignment_prompt:
            prompt_tokens = self.tokenize(assignment_prompt)
            boilerplate_fps.update(self.compute_fingerprints(prompt_tokens))

        # 4. Compute preliminary fingerprints per valid submission
        submission_fps: Dict[str, Set[int]] = {}
        fp_frequency: Dict[int, int] = {}

        for s in valid_items:
            sid = s["id"]
            tokens = results[sid]["_tokens"]
            fps = self.compute_fingerprints(tokens, excluded_fingerprints=boilerplate_fps)
            submission_fps[sid] = fps
            for fp in fps:
                fp_frequency[fp] = fp_frequency.get(fp, 0) + 1

        # 5. Subtract fingerprints appearing in >80% of submissions (shared template/questions)
        total_valid = len(valid_items)
        if total_valid >= 3:
            threshold_80 = total_valid * 0.80
            common_template_fps = {fp for fp, count in fp_frequency.items() if count >= threshold_80}
            for sid in submission_fps:
                submission_fps[sid] = submission_fps[sid] - common_template_fps

        for sid, fps in submission_fps.items():
            results[sid]["fingerprints_count"] = len(fps)

        # 6. Guard: Peer similarity requires at least 2 distinct valid non-duplicate submissions
        non_dup_valid = [s for s in valid_items if not results[s["id"]]["is_duplicate"]]
        if len(non_dup_valid) < 2:
            for sid in results:
                if not results[sid]["is_duplicate"]:
                    results[sid]["similarity_score"] = None
                    results[sid]["explanation"] = "N/A: Fewer than 2 distinct valid submissions with text."
            return results

        # 7. Compute pairwise similarities excluding self and duplicates
        for i, item_a in enumerate(non_dup_valid):
            sid_a = item_a["id"]
            fps_a = submission_fps.get(sid_a, set())
            tokens_a = len(results[sid_a]["_tokens"])
            highest_sim = 0.0
            top_peer = None
            top_peer_file = None
            max_matched_fps = 0

            compared_count = 0
            for j, item_b in enumerate(non_dup_valid):
                if i == j:
                    continue  # Exclude self!
                sid_b = item_b["id"]
                fps_b = submission_fps.get(sid_b, set())
                tokens_b = len(results[sid_b]["_tokens"])
                compared_count += 1

                sim = self.compute_pairwise_similarity(fps_a, fps_b, tokens_a, tokens_b)
                if sim is not None:
                    matched_fps = len(fps_a.intersection(fps_b))
                    if sim > highest_sim:
                        highest_sim = sim
                        top_peer = sid_b
                        top_peer_file = results[sid_b]["_file_name"]
                        max_matched_fps = matched_fps

            results[sid_a]["compared_peers_count"] = compared_count
            if highest_sim > 0.0:
                results[sid_a]["similarity_score"] = highest_sim
                results[sid_a]["top_match_peer_id"] = top_peer
                results[sid_a]["top_match_file_name"] = top_peer_file
                results[sid_a]["matched_fingerprints_count"] = max_matched_fps
                results[sid_a]["explanation"] = (
                    f"Highest peer similarity: {highest_sim}% with {top_peer_file or top_peer} "
                    f"({max_matched_fps} matched fingerprints)."
                )
            else:
                results[sid_a]["similarity_score"] = 0.0
                results[sid_a]["explanation"] = "No significant winnowing fingerprint overlaps detected."

        return results


winnowing_service = WinnowingService()
