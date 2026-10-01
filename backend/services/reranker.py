import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("daic.reranker")

class RerankerService:
    @staticmethod
    def rerank(query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Re-ranks RRF candidates using multi-factor evidence scoring:
        - Term density and exact phrase matching
        - Title & section relevance boost
        - Multi-modal agreement (present in both FTS and dense)
        - Historical / legal entity preservation
        """
        if not candidates:
            return []

        STOPWORDS = {
            "what", "where", "when", "how", "who", "whom", "which", "why",
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
            "into", "through", "during", "before", "after", "above", "below",
            "and", "or", "but", "not", "so", "than", "too", "very", "can", "will",
            "just", "should", "now", "did", "do", "does", "have", "has", "had",
            "tell", "me", "give", "say", "said"
        }
        q_terms = [w.lower() for w in re.findall(r'\b\w+\b', query) if len(w) > 2 and w.lower() not in STOPWORDS]
        reranked = []

        for cand in candidates:
            item = cand.copy()
            content = item.get("content", "").lower()
            title = item.get("title", "").lower()
            section = item.get("section_title", "").lower()

            # Term overlap score
            term_matches = sum(1 for t in q_terms if t in content or t in title or t in section)
            term_ratio = (term_matches / len(q_terms)) if q_terms else 0

            # If there are zero matching terms and no lexical match, heavily penalize to prevent false positive grounding
            matched_modes = item.get("matched_modes", [])
            has_lexical = "lexical" in matched_modes

            if term_matches == 0 and not has_lexical:
                # Query has no concept overlap with this archival chunk
                item["rerank_score"] = 0.05
                item["relevance_label"] = "Low relevance"
                reranked.append(item)
                continue

            # Base RRF score contribution
            score = item.get("normalized_score", 0.5) * 0.35
            score += term_ratio * 0.45

            # Exact phrase or title boost
            if query.lower() in content:
                score += 0.15
            if any(t in title or t in section for t in q_terms):
                score += 0.1

            # Cross-modal bonus (matched in both FTS5 and FAISS)
            if has_lexical and "dense" in matched_modes:
                score += 0.15

            # Provenance confidence
            if item.get("provenance_type") == "REAL ARCHIVAL DATA":
                score += 0.05

            item["rerank_score"] = round(min(1.0, score), 4)

            # Assign human-readable relevance category
            if item["rerank_score"] >= 0.65:
                item["relevance_label"] = "Highly relevant"
            elif item["rerank_score"] >= 0.35:
                item["relevance_label"] = "Relevant"
            else:
                item["relevance_label"] = "Supporting evidence"

            reranked.append(item)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]

reranker_service = RerankerService()
