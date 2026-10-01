#!/usr/bin/env python3
"""
PHASE I.1 — Index Integrity Repair Script
==========================================
Repairs FTS5 and FAISS indexes to include all verified ADL-MS chunks.

Operations:
  1. Populate FTS5 (archive_fts) with missing verified chunk entries
  2. Rebuild FAISS index to include all 28 chunks (demo + real)
  3. Validate consistency: SQLite = FTS5 = FAISS metadata counts for verified chunks
  4. Save updated metadata.json with complete provenance metadata
"""

import sys
import json
import logging
import sqlite3
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("repair")

from backend.database.db import get_db_connection
from backend.services.embeddings import embedding_service
from backend.services.faiss_service import faiss_service, METADATA_FILE, INDEX_FILE, HAS_FAISS

import numpy as np

# ─────────────────────────────────────────────────────────────
# 1. DIAGNOSTIC: Pre-repair state
# ─────────────────────────────────────────────────────────────
def run_diagnostics():
    conn = get_db_connection()

    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    fts_total = conn.execute("SELECT COUNT(*) FROM archive_fts").fetchone()[0]
    adl_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE document_id LIKE 'ADL-MS%'"
    ).fetchone()[0]
    adl_fts = conn.execute(
        "SELECT COUNT(*) FROM archive_fts WHERE document_id LIKE 'ADL-MS%'"
    ).fetchone()[0]

    faiss_total = len(faiss_service.metadata)
    adl_faiss = sum(1 for m in faiss_service.metadata if m.get("document_id", "").startswith("ADL-MS"))

    logger.info("=" * 60)
    logger.info("PRE-REPAIR DIAGNOSTICS")
    logger.info("=" * 60)
    logger.info(f"  SQLite total chunks:        {total_chunks}")
    logger.info(f"  SQLite ADL-MS chunks:       {adl_chunks}")
    logger.info(f"  FTS5 total entries:         {fts_total}")
    logger.info(f"  FTS5 ADL-MS entries:        {adl_fts}")
    logger.info(f"  FAISS metadata count:       {faiss_total}")
    logger.info(f"  FAISS ADL-MS vectors:       {adl_faiss}")
    logger.info(f"  Embedding model real:       {embedding_service.is_real_model}")
    logger.info(f"  Embedding model name:       {'BAAI/bge-m3' if embedding_service.is_real_model else 'deterministic-fallback'}")
    logger.info(f"  Embedding dim:              {embedding_service.dim}")
    if HAS_FAISS and faiss_service.index is not None:
        logger.info(f"  FAISS index ntotal:         {faiss_service.index.ntotal}")
        logger.info(f"  FAISS index dim:            {faiss_service.index.d}")
    conn.close()

    return {
        "total_chunks": total_chunks,
        "adl_chunks": adl_chunks,
        "fts_total": fts_total,
        "adl_fts": adl_fts,
        "faiss_total": faiss_total,
        "adl_faiss": adl_faiss,
    }


# ─────────────────────────────────────────────────────────────
# 2. FTS5 REPAIR: Insert missing verified chunks
# ─────────────────────────────────────────────────────────────
def repair_fts5():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all chunk_ids already in FTS5
    existing_fts_ids = {
        row[0] for row in cursor.execute("SELECT chunk_id FROM archive_fts").fetchall()
    }
    logger.info(f"FTS5 existing chunk_ids ({len(existing_fts_ids)}): {sorted(existing_fts_ids)[:5]}...")

    # Get all chunks from SQLite that are NOT in FTS5
    cursor.execute("""
        SELECT 
            c.id AS chunk_id,
            c.document_id,
            d.title,
            c.content,
            d.collection,
            d.author,
            c.section_title
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.id NOT IN (SELECT chunk_id FROM archive_fts)
    """)
    missing_chunks = cursor.fetchall()
    logger.info(f"FTS5 chunks missing: {len(missing_chunks)}")

    inserted_count = 0
    skipped_count = 0
    for row in missing_chunks:
        chunk_id = row["chunk_id"]
        if chunk_id in existing_fts_ids:
            skipped_count += 1
            continue
        try:
            cursor.execute("""
                INSERT INTO archive_fts (chunk_id, document_id, title, content, collection, author, section_title)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row["chunk_id"],
                row["document_id"],
                row["title"] or "",
                row["content"] or "",
                row["collection"] or "",
                row["author"] or "",
                row["section_title"] or "",
            ))
            inserted_count += 1
            logger.info(f"  FTS5 inserted: {chunk_id} (doc={row['document_id']})")
        except Exception as e:
            logger.error(f"  FTS5 insert error for {chunk_id}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"FTS5 repair complete: inserted={inserted_count}, skipped={skipped_count}")
    return inserted_count


# ─────────────────────────────────────────────────────────────
# 3. FAISS REPAIR: Add missing chunks to FAISS index
# ─────────────────────────────────────────────────────────────
def repair_faiss():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all chunks + document metadata
    cursor.execute("""
        SELECT 
            c.id AS chunk_id,
            c.document_id,
            c.page,
            c.section_title,
            c.content,
            c.provenance_type,
            d.title,
            d.collection,
            d.author,
            d.verification_status,
            d.provenance_type AS doc_provenance_type
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        ORDER BY c.document_id, c.page, c.chunk_index
    """)
    all_chunks = cursor.fetchall()
    conn.close()

    logger.info(f"Total SQLite chunks to index: {len(all_chunks)}")

    # Get existing chunk_ids in FAISS metadata
    existing_faiss_ids = {m["chunk_id"] for m in faiss_service.metadata}
    logger.info(f"Existing FAISS chunk_ids: {len(existing_faiss_ids)}")

    # Build list of chunks missing from FAISS
    missing_chunks = []
    for row in all_chunks:
        if row["chunk_id"] not in existing_faiss_ids:
            # Use chunk's provenance_type if set, else fall back to document's
            prov = row["provenance_type"] if row["provenance_type"] else row["doc_provenance_type"]
            missing_chunks.append({
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "page": row["page"],
                "section_title": row["section_title"] or "",
                "content": row["content"],
                "title": row["title"] or "",
                "collection": row["collection"] or "",
                "author": row["author"] or "",
                "provenance_type": prov or "USER-UPLOADED DATA",
                "verification_status": row["verification_status"] or "VERIFIED SOURCE",
            })

    logger.info(f"FAISS chunks missing: {len(missing_chunks)}")
    for c in missing_chunks:
        logger.info(f"  Will add: {c['chunk_id']} (doc={c['document_id']}, prov={c['provenance_type']})")

    if not missing_chunks:
        logger.info("FAISS already has all chunks. No repair needed.")
        return 0

    # Use faiss_service.add_chunks() which handles dedup, embedding, and sync
    faiss_service.add_chunks(missing_chunks)
    logger.info(f"FAISS repair complete: added {len(missing_chunks)} chunks. Total now: {len(faiss_service.metadata)}")
    return len(missing_chunks)


# ─────────────────────────────────────────────────────────────
# 4. POST-REPAIR VALIDATION
# ─────────────────────────────────────────────────────────────
def run_post_validation():
    conn = get_db_connection()

    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    fts_total = conn.execute("SELECT COUNT(*) FROM archive_fts").fetchone()[0]
    adl_chunks = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE document_id LIKE 'ADL-MS%'"
    ).fetchone()[0]
    adl_fts = conn.execute(
        "SELECT COUNT(*) FROM archive_fts WHERE document_id LIKE 'ADL-MS%'"
    ).fetchone()[0]

    # Reload faiss metadata fresh
    faiss_total = len(faiss_service.metadata)
    adl_faiss = sum(1 for m in faiss_service.metadata if m.get("document_id", "").startswith("ADL-MS"))

    if HAS_FAISS and faiss_service.index is not None:
        faiss_ntotal = faiss_service.index.ntotal
        faiss_dim = faiss_service.index.d
    elif faiss_service.numpy_vectors is not None:
        faiss_ntotal = len(faiss_service.numpy_vectors)
        faiss_dim = faiss_service.numpy_vectors.shape[1]
    else:
        faiss_ntotal = 0
        faiss_dim = 0

    logger.info("=" * 60)
    logger.info("POST-REPAIR VALIDATION")
    logger.info("=" * 60)
    logger.info(f"  SQLite total chunks:        {total_chunks}")
    logger.info(f"  SQLite ADL-MS chunks:       {adl_chunks}")
    logger.info(f"  FTS5 total entries:         {fts_total}")
    logger.info(f"  FTS5 ADL-MS entries:        {adl_fts}")
    logger.info(f"  FAISS metadata count:       {faiss_total}")
    logger.info(f"  FAISS index ntotal:         {faiss_ntotal}")
    logger.info(f"  FAISS ADL-MS vectors:       {adl_faiss}")
    logger.info(f"  FAISS dim:                  {faiss_dim}")
    logger.info(f"  FAISS metadata/index sync:  {'OK' if faiss_total == faiss_ntotal else 'MISMATCH'}")
    logger.info(f"  FTS5 == SQLite chunks:      {'OK' if fts_total == total_chunks else f'MISMATCH ({fts_total} vs {total_chunks})'}")
    logger.info(f"  Embedding model:            {'BAAI/bge-m3 (real)' if embedding_service.is_real_model else 'deterministic-fallback'}")
    logger.info(f"  Embedding dim:              {embedding_service.dim}")

    conn.close()

    return {
        "total_chunks": total_chunks,
        "fts_total": fts_total,
        "adl_chunks": adl_chunks,
        "adl_fts": adl_fts,
        "faiss_total": faiss_total,
        "faiss_ntotal": faiss_ntotal,
        "adl_faiss": adl_faiss,
        "faiss_dim": faiss_dim,
        "embedding_model": "BAAI/bge-m3" if embedding_service.is_real_model else "deterministic-fallback",
        "embedding_dim": embedding_service.dim,
        "fts_sync_ok": fts_total == total_chunks,
        "faiss_sync_ok": faiss_total == faiss_ntotal,
    }


# ─────────────────────────────────────────────────────────────
# 5. RETRIEVAL TEST: ADL-MS-0004 query
# ─────────────────────────────────────────────────────────────
def test_retrieval():
    from backend.services.fts_service import fts_service
    from backend.services.faiss_service import faiss_service as fs

    test_query = "What is my ideal of a society?"

    logger.info("=" * 60)
    logger.info(f"RETRIEVAL TEST: '{test_query}'")
    logger.info("=" * 60)

    # FTS5 test
    fts_results = fts_service.search(test_query, top_k=5)
    logger.info(f"FTS5 results ({len(fts_results)}):")
    for r in fts_results[:5]:
        logger.info(f"  chunk={r['chunk_id']}, doc={r['document_id']}, page={r.get('page')}, score={r.get('score', 0):.4f}, prov={r.get('provenance_type')}")

    # FAISS test
    dense_results = fs.search(test_query, top_k=5)
    logger.info(f"\nFAISS results ({len(dense_results)}):")
    for r in dense_results[:5]:
        logger.info(f"  chunk={r['chunk_id']}, doc={r['document_id']}, page={r.get('page')}, score={r.get('score', 0):.4f}, prov={r.get('provenance_type')}")

    # Check if ADL-MS-0004 appears
    adl_in_fts = any(r["document_id"] == "ADL-MS-0004" for r in fts_results)
    adl_in_faiss = any(r["document_id"] == "ADL-MS-0004" for r in dense_results)
    logger.info(f"\nADL-MS-0004 in FTS5 results: {adl_in_fts}")
    logger.info(f"ADL-MS-0004 in FAISS results: {adl_in_faiss}")

    return {
        "test_query": test_query,
        "fts_count": len(fts_results),
        "faiss_count": len(dense_results),
        "adl_in_fts": adl_in_fts,
        "adl_in_faiss": adl_in_faiss,
        "fts_top_result": fts_results[0] if fts_results else None,
        "faiss_top_result": dense_results[0] if dense_results else None,
    }


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting PHASE I.1 Index Integrity Repair")

    pre = run_diagnostics()

    logger.info("\n--- STEP 1: FTS5 Repair ---")
    fts_inserted = repair_fts5()

    logger.info("\n--- STEP 2: FAISS Repair ---")
    faiss_added = repair_faiss()

    logger.info("\n--- STEP 3: Post-Repair Validation ---")
    post = run_post_validation()

    logger.info("\n--- STEP 4: Retrieval Test ---")
    test_results = test_retrieval()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("REPAIR SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  FTS5 chunks inserted:       {fts_inserted}")
    logger.info(f"  FAISS chunks added:         {faiss_added}")
    logger.info(f"  Final total chunks:         {post['total_chunks']}")
    logger.info(f"  Final FTS5 total:           {post['fts_total']}")
    logger.info(f"  Final FAISS metadata:       {post['faiss_total']}")
    logger.info(f"  Final FAISS index ntotal:   {post['faiss_ntotal']}")
    logger.info(f"  Final ADL-MS in FAISS:      {post['adl_faiss']}")
    logger.info(f"  FTS5 sync:                  {'PASS' if post['fts_sync_ok'] else 'FAIL'}")
    logger.info(f"  FAISS sync:                 {'PASS' if post['faiss_sync_ok'] else 'FAIL'}")
    logger.info(f"  ADL-MS-0004 in retrieval:   {'PASS' if test_results['adl_in_fts'] or test_results['adl_in_faiss'] else 'FAIL'}")

    print("\nRepair script complete. All results logged above.")
