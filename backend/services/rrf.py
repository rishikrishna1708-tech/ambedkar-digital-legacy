import logging
from typing import List, Dict, Any
from backend.config import RRF_K

logger = logging.getLogger("daic.rrf")

class RRFService:
    @staticmethod
    def fuse(
        lexical_results: List[Dict[str, Any]], 
        dense_results: List[Dict[str, Any]], 
        k: int = RRF_K,
        top_n: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF):
        RRF_score(d) = sum_{m in models} 1 / (k + rank_m(d))
        """
        combined: Dict[str, Dict[str, Any]] = {}

        # 1. Process Lexical (FTS5) ranks
        for rank, item in enumerate(lexical_results):
            cid = item["chunk_id"]
            rrf_contrib = 1.0 / (k + (rank + 1))
            if cid not in combined:
                combined[cid] = item.copy()
                combined[cid]["rrf_score"] = rrf_contrib
                combined[cid]["fts_rank"] = rank + 1
                combined[cid]["dense_rank"] = None
                combined[cid]["matched_modes"] = ["lexical"]
            else:
                combined[cid]["rrf_score"] += rrf_contrib
                combined[cid]["fts_rank"] = rank + 1
                if "lexical" not in combined[cid]["matched_modes"]:
                    combined[cid]["matched_modes"].append("lexical")

        # 2. Process Dense (FAISS) ranks
        for rank, item in enumerate(dense_results):
            cid = item["chunk_id"]
            rrf_contrib = 1.0 / (k + (rank + 1))
            if cid not in combined:
                combined[cid] = item.copy()
                combined[cid]["rrf_score"] = rrf_contrib
                combined[cid]["fts_rank"] = None
                combined[cid]["dense_rank"] = rank + 1
                combined[cid]["matched_modes"] = ["dense"]
            else:
                combined[cid]["rrf_score"] += rrf_contrib
                combined[cid]["dense_rank"] = rank + 1
                for key in ("verification_status", "provenance_type", "author", "collection", "title", "page"):
                    if not combined[cid].get(key) and item.get(key):
                        combined[cid][key] = item[key]
                if "dense" not in combined[cid]["matched_modes"]:
                    combined[cid]["matched_modes"].append("dense")

        # 3. Sort by RRF score descending
        fused_candidates = list(combined.values())
        fused_candidates.sort(key=lambda x: x["rrf_score"], reverse=True)

        # 4. Normalize RRF scores to 0.0 - 1.0 range for clean presentation
        if fused_candidates:
            max_score = fused_candidates[0]["rrf_score"]
            for i, cand in enumerate(fused_candidates):
                cand["rrf_rank"] = i + 1
                cand["normalized_score"] = round(cand["rrf_score"] / max_score, 4) if max_score > 0 else 0.0

        return fused_candidates[:top_n]

rrf_service = RRFService()
