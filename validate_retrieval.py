"""
Phase II.1 Validation Script
Runs 1 exact and 1 semantic query for ADL-MS-0001 through ADL-MS-0004
Validates: FTS5, FAISS, RRF, Reranker, Evidence Gate
"""
import sys
import os
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.fts_service import fts_service
from backend.services.faiss_service import faiss_service
from backend.services.rrf import rrf_service
from backend.services.reranker import reranker_service
from backend.services.evidence_gate import evidence_gate

def run_retrieval_validation():
    conn = sqlite3.connect("data/daic_archive.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=" * 80)
    print("PHASE II.1 — REAL DOCUMENT RETRIEVAL VALIDATION")
    print("=" * 80)

    # 1. Existence check in FTS5, FAISS metadata, FAISS vectors
    print("\n--- 1. INDEX EXISTENCE AUDIT ---")
    all_exist = True
    for doc_id in ["ADL-MS-0001", "ADL-MS-0002", "ADL-MS-0003", "ADL-MS-0004"]:
        cur.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (doc_id,))
        sqlite_cnt = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM archive_fts WHERE document_id = ?", (doc_id,))
        fts_cnt = cur.fetchone()[0]
        faiss_meta_cnt = sum(1 for m in faiss_service.metadata if m.get("document_id") == doc_id)
        exists = (sqlite_cnt > 0 and sqlite_cnt == fts_cnt == faiss_meta_cnt)
        if not exists:
            all_exist = False
        print(f"[{'PASS' if exists else 'FAIL'}] {doc_id}: SQLite={sqlite_cnt} | FTS5={fts_cnt} | FAISS_meta={faiss_meta_cnt}")
    conn.close()

    # 2. Queries
    queries = [
        ("ADL-MS-0001", "Exact", "Fundamental Rights are the birthright of every citizen"),
        ("ADL-MS-0001", "Semantic", "State socialism in key industries to prevent exploitation of working class"),
        ("ADL-MS-0002", "Exact", "Supplementary Memorandum on the Claims of the Depressed Classes"),
        ("ADL-MS-0002", "Semantic", "Demands of depressed classes at London Round Table Conference"),
        ("ADL-MS-0003", "Exact", "Southborough Committee on Franchise"),
        ("ADL-MS-0003", "Semantic", "Political franchise representation and separate electorates in 1919"),
        ("ADL-MS-0004", "Exact", "Annihilation of Caste: An Undelivered Address"),
        ("ADL-MS-0004", "Semantic", "Social endosmosis as the essence of democracy in Annihilation of Caste")
    ]

    print("\n--- 2. END-TO-END RETRIEVAL PIPELINE EVALUATION ---")
    results_summary = []
    
    for doc_id, q_type, q in queries:
        print("\n" + "=" * 80)
        print(f"TARGET DOC:        {doc_id}")
        print(f"QUERY TYPE:        {q_type}")
        print(f"QUERY TEXT:        \"{q}\"")
        print("-" * 80)

        # FTS5 search
        fts_res = fts_service.search(q, top_k=5)
        top_fts = fts_res[0] if fts_res else None
        print(f"FTS5 Result:       {top_fts['chunk_id'] if top_fts else 'NONE'} (doc={top_fts.get('document_id') if top_fts else 'N/A'}, score={round(top_fts.get('score', 0), 3) if top_fts else 'N/A'})")

        # FAISS search
        faiss_res = faiss_service.search(q, top_k=5)
        top_faiss = faiss_res[0] if faiss_res else None
        print(f"FAISS Result:      {top_faiss['chunk_id'] if top_faiss else 'NONE'} (doc={top_faiss.get('document_id') if top_faiss else 'N/A'}, score={round(top_faiss.get('score', 0), 3) if top_faiss else 'N/A'})")

        # RRF Fusion
        rrf_res = rrf_service.fuse(fts_res, faiss_res, top_n=5)
        top_rrf = rrf_res[0] if rrf_res else None
        print(f"RRF Result:        {top_rrf['chunk_id'] if top_rrf else 'NONE'} (rrf_score={round(top_rrf.get('rrf_score', 0), 5) if top_rrf else 'N/A'}, modes={top_rrf.get('matched_modes') if top_rrf else 'N/A'})")

        # Reranker
        reranked = reranker_service.rerank(q, rrf_res, top_k=3)
        top_rerank = reranked[0] if reranked else None
        print(f"Reranked Result:   {top_rerank['chunk_id'] if top_rerank else 'NONE'} (score={round(top_rerank.get('rerank_score', 0), 3) if top_rerank else 'N/A'}, label={top_rerank.get('relevance_label') if top_rerank else 'N/A'})")

        # Evidence Gate
        passed, reason, gate_chunks = evidence_gate.validate_retrieved_evidence(q, reranked)
        print(f"Evidence Gate:     {'ACCEPTED' if passed else 'REJECTED'} (reason: {reason})")

        if gate_chunks:
            top_evidence = gate_chunks[0]
            print(f"Document ID:       {top_evidence.get('document_id')}")
            print(f"Page:              {top_evidence.get('page')}")
            print(f"Provenance:        {top_evidence.get('provenance_type')}")
            print(f"Verification:      {top_evidence.get('verification_status')}")
            print(f"Snippet:           {top_evidence.get('content', '')[:120].strip()}...")
            
            results_summary.append({
                "target_doc": doc_id,
                "query_type": q_type,
                "query": q,
                "fts_chunk": top_fts["chunk_id"] if top_fts else None,
                "faiss_chunk": top_faiss["chunk_id"] if top_faiss else None,
                "rrf_chunk": top_rrf["chunk_id"] if top_rrf else None,
                "reranked_chunk": top_rerank["chunk_id"] if top_rerank else None,
                "gate_passed": passed,
                "retrieved_doc": top_evidence.get("document_id"),
                "page": top_evidence.get("page"),
                "provenance": top_evidence.get("provenance_type"),
                "verification_status": top_evidence.get("verification_status")
            })

    print("\n" + "=" * 80)
    print("SUMMARY OF ALL 8 QUERIES:")
    print("=" * 80)
    for r in results_summary:
        match = "MATCH" if r["target_doc"] == r["retrieved_doc"] else "RELATED"
        print(f"[{match}] {r['target_doc']} ({r['query_type']:<8}): retrieved={r['retrieved_doc']} P{r['page']} | Gate={'PASS' if r['gate_passed'] else 'FAIL'} | Prov={r['provenance']}")

if __name__ == "__main__":
    run_retrieval_validation()
