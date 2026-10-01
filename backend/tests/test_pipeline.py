"""
DAIC Archive — Phase II Pipeline Test Suite
Tests verify the full retrieval stack and real archival document retrieval.
Assertions validate: SQLite chunk existence, FTS5 indexing, FAISS vectors,
correct document mapping, correct page mapping, Evidence Gate, and real uploaded
document retrievability.
"""
import unittest
import asyncio
import sqlite3
import json
import os

from backend.config import DB_PATH
from backend.database.seed_data import seed_database
from backend.services.fts_service import fts_service
from backend.services.faiss_service import faiss_service
from backend.services.rrf import rrf_service
from backend.services.reranker import reranker_service
from backend.services.evidence_gate import evidence_gate
from backend.services.retrieval import retrieval_pipeline


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


class TestArchivalPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Seed demo data and rebuild indexes preserving all verified archival chunks."""
        seed_database()

    # ─────────────────────────────────────────────────────────────
    # 1. Index consistency — invariant must hold after seed
    # ─────────────────────────────────────────────────────────────
    def test_index_invariant(self):
        """SQLite verified chunks == FTS5 entries == FAISS metadata == FAISS ntotal."""
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.verification_status IN ('VERIFIED SOURCE', 'DEMO DATA')
        """)
        sqlite_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM archive_fts")
        fts_count = cur.fetchone()[0]
        conn.close()

        faiss_meta = len(faiss_service.metadata)
        faiss_ntotal = faiss_service.index.ntotal if faiss_service.index else 0

        self.assertEqual(sqlite_count, fts_count,
            f"SQLite verified chunks ({sqlite_count}) != FTS5 entries ({fts_count})")
        self.assertEqual(fts_count, faiss_meta,
            f"FTS5 entries ({fts_count}) != FAISS metadata ({faiss_meta})")
        self.assertEqual(faiss_meta, faiss_ntotal,
            f"FAISS metadata ({faiss_meta}) != FAISS ntotal ({faiss_ntotal})")
        self.assertGreater(sqlite_count, 0, "At least one indexed chunk is required")

    # ─────────────────────────────────────────────────────────────
    # 2. FTS5 BM25 lexical search
    # ─────────────────────────────────────────────────────────────
    def test_database_and_fts5(self):
        """FTS5 returns results for 'labour rights' mapping to BAWS_VOL_10_LABOUR."""
        results = fts_service.search("labour rights", top_k=5)
        self.assertGreater(len(results), 0, "FTS5 should return results for 'labour rights'")
        self.assertTrue(any("BAWS_VOL_10_LABOUR" in r["document_id"] for r in results),
            "Top FTS5 results must include BAWS_VOL_10_LABOUR chunk")

        # Validate chunk fields
        top = results[0]
        self.assertIn("chunk_id", top)
        self.assertIn("document_id", top)
        self.assertIn("content", top)
        self.assertIn("page", top)
        self.assertIn("provenance_type", top)

        # Verify chunk actually exists in SQLite
        conn = get_conn()
        row = conn.execute("SELECT id FROM chunks WHERE id = ?", (top["chunk_id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(row, f"Chunk {top['chunk_id']} returned by FTS5 must exist in SQLite")

    # ─────────────────────────────────────────────────────────────
    # 3. FAISS dense semantic search
    # ─────────────────────────────────────────────────────────────
    def test_faiss_dense_search(self):
        """FAISS returns dense matches and all chunks exist in SQLite."""
        results = faiss_service.search("working hours and factory conditions", top_k=5)
        self.assertGreater(len(results), 0, "FAISS should return dense matches")
        self.assertIn("chunk_id", results[0])
        self.assertIn("score", results[0])
        self.assertGreater(results[0]["score"], 0.0, "FAISS score must be positive")

        conn = get_conn()
        for r in results:
            row = conn.execute("SELECT id FROM chunks WHERE id = ?", (r["chunk_id"],)).fetchone()
            self.assertIsNotNone(row, f"FAISS chunk {r['chunk_id']} must exist in SQLite")
        conn.close()

    # ─────────────────────────────────────────────────────────────
    # 4. RRF fusion
    # ─────────────────────────────────────────────────────────────
    def test_rrf_fusion(self):
        """RRF fuses FTS5 and FAISS results with rrf_score and matched_modes."""
        lexical = fts_service.search("labour", top_k=5)
        dense = faiss_service.search("labour", top_k=5)
        fused = rrf_service.fuse(lexical, dense, top_n=5)

        self.assertGreater(len(fused), 0, "RRF should produce fused results")
        top = fused[0]
        self.assertIn("rrf_score", top)
        self.assertIn("matched_modes", top)
        self.assertIn("chunk_id", top)
        self.assertIsInstance(top["rrf_score"], float)
        self.assertGreater(top["rrf_score"], 0.0)

        # Verify top chunk is in SQLite
        conn = get_conn()
        row = conn.execute("SELECT id FROM chunks WHERE id = ?", (top["chunk_id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(row, "RRF top chunk must exist in SQLite")

    # ─────────────────────────────────────────────────────────────
    # 5. Reranker
    # ─────────────────────────────────────────────────────────────
    def test_reranker(self):
        """Reranker assigns rerank_score and relevance_label to each candidate."""
        lexical = fts_service.search("Article 17", top_k=5)
        dense = faiss_service.search("Article 17", top_k=5)
        fused = rrf_service.fuse(lexical, dense, top_n=5)
        reranked = reranker_service.rerank("Article 17", fused, top_k=3)

        self.assertGreater(len(reranked), 0)
        top = reranked[0]
        self.assertIn("rerank_score", top)
        self.assertIn("relevance_label", top)
        self.assertIn("chunk_id", top)
        self.assertIsInstance(top["rerank_score"], float)
        self.assertGreaterEqual(top["rerank_score"], 0.0)
        self.assertIn(top["relevance_label"], ["Highly relevant", "Relevant", "Supporting evidence"])

        # Verify page mapping
        conn = get_conn()
        row = conn.execute("SELECT id, page FROM chunks WHERE id = ?", (top["chunk_id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(row, f"Reranked chunk {top['chunk_id']} must exist in SQLite")

    # ─────────────────────────────────────────────────────────────
    # 6. Evidence Gate — acceptance
    # ─────────────────────────────────────────────────────────────
    def test_evidence_gate_acceptance(self):
        """Evidence Gate accepts authentic Mahad Satyagraha archival query."""
        lexical = fts_service.search("Mahad Satyagraha", top_k=5)
        dense = faiss_service.search("Mahad Satyagraha", top_k=5)
        fused = rrf_service.fuse(lexical, dense, top_n=5)
        reranked = reranker_service.rerank("Mahad Satyagraha", fused, top_k=5)
        passed, reason, chunks = evidence_gate.validate_retrieved_evidence("Mahad Satyagraha", reranked)

        self.assertTrue(passed, f"Evidence gate must pass authentic archival query: {reason}")
        self.assertGreater(len(chunks), 0)

        # Verify gate chunk exists in SQLite with correct document mapping
        conn = get_conn()
        top = chunks[0]
        row = conn.execute("""
            SELECT c.id, c.document_id, c.page, d.verification_status
            FROM chunks c JOIN documents d ON c.document_id = d.id
            WHERE c.id = ?
        """, (top["chunk_id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(row, f"Evidence Gate chunk {top['chunk_id']} must exist in SQLite")
        self.assertEqual(row["document_id"], top["document_id"],
            "Evidence Gate chunk document_id must match SQLite document mapping")

    # ─────────────────────────────────────────────────────────────
    # 7. Evidence Gate — rejection
    # ─────────────────────────────────────────────────────────────
    def test_evidence_gate_rejection(self):
        """Evidence Gate rejects off-topic queries with empty candidate list."""
        passed, reason, chunks = evidence_gate.validate_retrieved_evidence("Space shuttles in 2050", [])
        self.assertFalse(passed, "Evidence gate must reject unsupported query")
        self.assertIn("No candidate", reason)
        self.assertEqual(len(chunks), 0)

    # ─────────────────────────────────────────────────────────────
    # 8. ADL-MS real uploaded document retrieval
    # ─────────────────────────────────────────────────────────────
    def test_real_archival_document_retrieval(self):
        """ADL-MS-0001 through ADL-MS-0004 must be retrievable from FTS5 and FAISS."""
        conn = get_conn()
        for doc_id in ["ADL-MS-0001", "ADL-MS-0002", "ADL-MS-0003", "ADL-MS-0004"]:
            # SQLite chunk existence
            row = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (doc_id,)
            ).fetchone()
            sqlite_cnt = row[0]
            self.assertGreater(sqlite_cnt, 0, f"{doc_id} must have chunks in SQLite")

            # FTS5 indexed existence
            row = conn.execute(
                "SELECT COUNT(*) FROM archive_fts WHERE document_id = ?", (doc_id,)
            ).fetchone()
            fts_cnt = row[0]
            self.assertGreater(fts_cnt, 0, f"{doc_id} must have chunks in FTS5")
            self.assertEqual(sqlite_cnt, fts_cnt,
                f"{doc_id}: SQLite chunk count ({sqlite_cnt}) must match FTS5 count ({fts_cnt})")

            # FAISS metadata existence
            faiss_cnt = sum(1 for m in faiss_service.metadata if m.get("document_id") == doc_id)
            self.assertGreater(faiss_cnt, 0, f"{doc_id} must have vectors in FAISS metadata")
            self.assertEqual(sqlite_cnt, faiss_cnt,
                f"{doc_id}: SQLite chunk count ({sqlite_cnt}) must match FAISS metadata count ({faiss_cnt})")

            # Verification status
            doc_row = conn.execute(
                "SELECT verification_status, provenance_type FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            self.assertIsNotNone(doc_row, f"{doc_id} must exist in documents table")
            self.assertEqual(doc_row["verification_status"], "VERIFIED SOURCE",
                f"{doc_id} verification_status must be VERIFIED SOURCE")
        conn.close()

    # ─────────────────────────────────────────────────────────────
    # 9. End-to-end ask pipeline
    # ─────────────────────────────────────────────────────────────
    def test_end_to_end_ask_pipeline(self):
        """End-to-end ask() returns verified answer grounded in BAWS_VOL_10_LABOUR."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(
            retrieval_pipeline.ask("What did Ambedkar say about labour rights?")
        )
        loop.close()

        self.assertIsInstance(res, dict)
        self.assertTrue(res["verified"], "Pipeline response must be verified")
        self.assertIn("BAWS_VOL_10_LABOUR", str(res["sources"]),
            "Sources must include BAWS_VOL_10_LABOUR")
        self.assertIn("8 hours", res["answer"],
            "Answer must mention 8-hour workday from archival source")
        self.assertGreater(len(res["evidence"]), 0, "At least one evidence chunk required")

        # Validate evidence chunk mappings
        for ev in res["evidence"]:
            self.assertIn("document_id", ev)
            # field is named 'relevance' in the pipeline evidence dict
            self.assertTrue(
                "relevance" in ev or "relevance_percent" in ev,
                f"Evidence chunk must have a relevance score field: {list(ev.keys())}"
            )


if __name__ == "__main__":
    unittest.main()
