import sqlite3
import re
import logging
from typing import List, Dict, Any
from backend.database.db import get_db_connection

logger = logging.getLogger("daic.fts")

class FTSService:
    @staticmethod
    def sanitize_fts_query(query: str) -> str:
        """
        Sanitize input query for SQLite FTS5 MATCH syntax.
        Supports phrases in quotes, escapes special operators, and splits into terms.
        Apostrophes/single-quotes are stripped from tokens to prevent FTS5 syntax errors
        (e.g. "Ambedkar's" → "Ambedkars*").
        """
        query = query.strip()
        if not query:
            return '""'

        # Check if user passed exact phrases with quotes
        phrases = re.findall(r'"([^"]*)"', query)
        remaining = re.sub(r'"[^"]*"', '', query)

        # Tokenize remaining words. Apostrophes are intentionally excluded from the
        # character class so that "Ambedkar's" splits into ["Ambedkar", "s"] rather
        # than the single token "Ambedkar's" which breaks FTS5 MATCH syntax.
        clean_words = re.findall(r"[a-zA-Z0-9\u0900-\u097F\u0B80-\u0BFF\u0C80-\u0CFF][\w\u0900-\u097F\u0B80-\u0BFF\u0C80-\u0CFF-]*", remaining)
        # Strip any residual single-quotes/curly-quotes that may still exist
        clean_words = [re.sub(r"['\u2018\u2019`]", '', w) for w in clean_words if w]

        # Stopwords to filter out from prefix matching
        STOPWORDS = {
            "what", "where", "when", "how", "who", "whom", "which", "why",
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
            "into", "through", "during", "before", "after", "above", "below",
            "and", "or", "but", "not", "so", "than", "too", "very", "can", "will",
            "just", "should", "now", "did", "do", "does", "have", "has", "had",
            "tell", "me", "give", "say", "said",
            "s"  # bare 's' produced by stripping apostrophe from possessives
        }

        parts = []
        for p in phrases:
            clean_p = re.sub(r"['\u2018\u2019`]", '', p).strip()
            if clean_p:
                parts.append(f'"{clean_p}"')

        for w in clean_words:
            w_lower = w.lower()
            if not w or w_lower in STOPWORDS:
                continue
            # Avoid FTS reserved keywords being bare
            if w.upper() in ["AND", "OR", "NOT", "NEAR"]:
                parts.append(f'"{w}"')
            else:
                parts.append(f'{w}*')  # prefix matching for flex

        if not parts:
            # If all words were stopwords, fallback to non-wildcard exact phrase
            safe = [re.sub(r"['\u2018\u2019`]", '', w) for w in clean_words[:3] if w]
            parts = [f'"{w}"' for w in safe if w] or ['""']

        # Join with OR
        return " OR ".join(parts)

    @classmethod
    def search(cls, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()

        fts_query = cls.sanitize_fts_query(query)
        logger.debug(f"FTS5 Query: {fts_query}")

        try:
            # FTS5 bm25 ranking function
            cursor.execute("""
                SELECT 
                    f.chunk_id,
                    f.document_id,
                    f.title,
                    f.content,
                    f.collection,
                    f.author,
                    f.section_title,
                    c.page,
                    c.provenance_type,
                    d.verification_status,
                    bm25(archive_fts) AS bm25_score
                FROM archive_fts f
                JOIN chunks c ON f.chunk_id = c.id
                JOIN documents d ON c.document_id = d.id
                WHERE archive_fts MATCH ?
                ORDER BY bm25_score ASC
                LIMIT ?
            """, (fts_query, top_k))

            rows = cursor.fetchall()
            results = []
            for rank, r in enumerate(rows):
                # SQLite FTS5 bm25 scores are negative (more negative = better match)
                raw_score = r["bm25_score"]
                norm_score = max(0.0, -float(raw_score))
                
                results.append({
                    "chunk_id": r["chunk_id"],
                    "document_id": r["document_id"],
                    "title": r["title"],
                    "content": r["content"],
                    "collection": r["collection"],
                    "author": r["author"],
                    "section_title": r["section_title"],
                    "page": r["page"],
                    "provenance_type": r["provenance_type"],
                    "verification_status": r["verification_status"],
                    "score": norm_score,
                    "fts_rank": rank + 1
                })
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"FTS5 search error: {e}")
            conn.close()
            return []

fts_service = FTSService()
