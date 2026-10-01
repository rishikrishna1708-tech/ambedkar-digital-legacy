"""
Index Consistency Validation and Runtime Synchronization Utility
Validates and enforces the required invariant:
  SQLite verified chunks == FTS5 indexed verified chunks == FAISS metadata vectors == FAISS ntotal
Provides provenance breakdowns for DEMO DATA, USER-UPLOADED DATA, and REAL ARCHIVAL DATA.
"""
import sys
import os
import logging
from typing import Dict, Any, List
from collections import Counter

from backend.database.db import get_db_connection
from backend.services.faiss_service import faiss_service

logger = logging.getLogger("daic.validator")


def sync_and_rebuild_runtime_index() -> Dict[str, Any]:
    """
    Executes a complete rebuild and synchronization of the runtime index:
    1. Normalizes chunk provenance to match parent document's provenance_type
    2. Rebuilds SQLite FTS5 (archive_fts) with all verified chunks
    3. Rebuilds FAISS index and metadata.json with all verified chunks
    4. Validates invariant: SQLite verified chunks == FTS5 == FAISS metadata == FAISS vectors
    5. Returns actual counts including separate breakdowns by provenance category.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Normalize chunks provenance_type from parent document where needed
    cursor.execute("""
        UPDATE chunks
        SET provenance_type = (
            SELECT d.provenance_type 
            FROM documents d 
            WHERE d.id = chunks.document_id
        )
        WHERE chunks.provenance_type = 'VERIFIED SOURCE' OR chunks.provenance_type IS NULL
    """)
    conn.commit()

    # 2. Fetch all verified chunks from verified or demo documents
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
        WHERE d.verification_status IN ('VERIFIED SOURCE', 'DEMO DATA')
        ORDER BY c.document_id, c.page, c.chunk_index
    """)
    verified_chunks = cursor.fetchall()

    # 3. Synchronize FTS5 virtual table
    cursor.execute("DELETE FROM archive_fts;")
    for chunk in verified_chunks:
        cursor.execute("""
            INSERT INTO archive_fts (chunk_id, document_id, title, content, collection, author, section_title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk["chunk_id"],
            chunk["document_id"],
            chunk["title"] or "",
            chunk["content"],
            chunk["collection"] or "",
            chunk["author"] or "",
            chunk["section_title"] or ""
        ))
    conn.commit()

    # 4. Synchronize FAISS Dense Vector Index
    faiss_chunks_payload = []
    for chunk in verified_chunks:
        prov = chunk["provenance_type"] or chunk["doc_provenance_type"] or "USER-UPLOADED DATA"
        faiss_chunks_payload.append({
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "page": chunk["page"],
            "section_title": chunk["section_title"] or "",
            "content": chunk["content"],
            "title": chunk["title"] or "",
            "collection": chunk["collection"] or "",
            "author": chunk["author"] or "",
            "provenance_type": prov,
            "verification_status": chunk["verification_status"] or "VERIFIED SOURCE"
        })

    # Perform full FAISS rebuild
    faiss_service.rebuild()
    faiss_service.add_chunks(faiss_chunks_payload)

    # 5. Measure and verify runtime counts
    cursor.execute("""
        SELECT COUNT(*) FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.verification_status IN ('VERIFIED SOURCE', 'DEMO DATA')
    """)
    sqlite_verified_chunks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM archive_fts")
    fts5_indexed_chunks = cursor.fetchone()[0]

    # Provenance counts from SQLite
    cursor.execute("""
        SELECT 
            COALESCE(c.provenance_type, d.provenance_type) as prov,
            COUNT(*) 
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.verification_status IN ('VERIFIED SOURCE', 'DEMO DATA')
        GROUP BY prov
    """)
    sqlite_prov_rows = cursor.fetchall()
    sqlite_by_prov = {r[0]: r[1] for r in sqlite_prov_rows}

    conn.close()

    faiss_metadata_count = len(faiss_service.metadata)
    faiss_ntotal = faiss_service.index.ntotal if faiss_service.index is not None else 0

    faiss_by_prov = Counter(m.get("provenance_type") for m in faiss_service.metadata)

    is_synced = (
        sqlite_verified_chunks == fts5_indexed_chunks == faiss_metadata_count == faiss_ntotal
    )

    result = {
        "status": "HEALTHY" if is_synced else "MISMATCH",
        "is_healthy": is_synced,
        "sqlite_verified_chunks": sqlite_verified_chunks,
        "fts5_indexed_chunks": fts5_indexed_chunks,
        "faiss_metadata_vectors": faiss_metadata_count,
        "faiss_ntotal": faiss_ntotal,
        "by_provenance": {
            "DEMO DATA": sqlite_by_prov.get("DEMO DATA", 0),
            "USER-UPLOADED DATA": sqlite_by_prov.get("USER-UPLOADED DATA", 0),
            "REAL ARCHIVAL DATA": sqlite_by_prov.get("REAL ARCHIVAL DATA", 0),
        },
        "faiss_by_provenance": {
            "DEMO DATA": faiss_by_prov.get("DEMO DATA", 0),
            "USER-UPLOADED DATA": faiss_by_prov.get("USER-UPLOADED DATA", 0),
            "REAL ARCHIVAL DATA": faiss_by_prov.get("REAL ARCHIVAL DATA", 0),
        }
    }

    logger.info(f"Runtime index sync completed: status={result['status']}, total={sqlite_verified_chunks}")
    return result


def check_index_consistency() -> Dict[str, Any]:
    """
    Read-only consistency validator. Checks counts without modifying index.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.verification_status IN ('VERIFIED SOURCE', 'DEMO DATA')
    """)
    sqlite_chunks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM archive_fts")
    fts_entries = cur.fetchone()[0]

    cur.execute("""
        SELECT 
            COALESCE(c.provenance_type, d.provenance_type) as prov,
            COUNT(*) 
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE d.verification_status IN ('VERIFIED SOURCE', 'DEMO DATA')
        GROUP BY prov
    """)
    sqlite_by_prov = {r[0]: r[1] for r in cur.fetchall()}
    conn.close()

    faiss_ntotal = faiss_service.index.ntotal if (faiss_service.index is not None) else 0
    faiss_metadata = len(faiss_service.metadata)
    faiss_by_prov = Counter(m.get("provenance_type") for m in faiss_service.metadata)

    is_healthy = (sqlite_chunks == fts_entries == faiss_metadata == faiss_ntotal)
    status_str = "HEALTHY" if is_healthy else "MISMATCH"

    mismatches = []
    if sqlite_chunks != fts_entries:
        mismatches.append(f"SQLite verified chunks ({sqlite_chunks}) != FTS5 entries ({fts_entries})")
    if faiss_ntotal != faiss_metadata:
        mismatches.append(f"FAISS vectors ({faiss_ntotal}) != FAISS metadata ({faiss_metadata})")
    if sqlite_chunks != faiss_ntotal:
        mismatches.append(f"SQLite chunks ({sqlite_chunks}) != FAISS vectors ({faiss_ntotal})")

    return {
        "verified_chunks": sqlite_chunks,
        "fts5_entries": fts_entries,
        "faiss_vectors": faiss_ntotal,
        "faiss_metadata": faiss_metadata,
        "status": status_str,
        "is_healthy": is_healthy,
        "mismatches": mismatches,
        "by_provenance": {
            "DEMO DATA": sqlite_by_prov.get("DEMO DATA", 0),
            "USER-UPLOADED DATA": sqlite_by_prov.get("USER-UPLOADED DATA", 0),
            "REAL ARCHIVAL DATA": sqlite_by_prov.get("REAL ARCHIVAL DATA", 0),
        },
        "faiss_by_provenance": {
            "DEMO DATA": faiss_by_prov.get("DEMO DATA", 0),
            "USER-UPLOADED DATA": faiss_by_prov.get("USER-UPLOADED DATA", 0),
            "REAL ARCHIVAL DATA": faiss_by_prov.get("REAL ARCHIVAL DATA", 0),
        }
    }


def print_consistency_report():
    res = check_index_consistency()
    print("=" * 60)
    print("INDEX CONSISTENCY REPORT")
    print("=" * 60)
    print(f"SQLite verified chunks:  {res['verified_chunks']}")
    print(f"FTS5 indexed chunks:     {res['fts5_entries']}")
    print(f"FAISS metadata vectors:  {res['faiss_metadata']}")
    print(f"FAISS ntotal:            {res['faiss_vectors']}")
    print("-" * 60)
    print("Counts by Provenance (SQLite):")
    for prov, count in res["by_provenance"].items():
        print(f"  {prov:<22}: {count}")
    print("Counts by Provenance (FAISS):")
    for prov, count in res["faiss_by_provenance"].items():
        print(f"  {prov:<22}: {count}")
    print("-" * 60)
    print(f"INDEX STATUS:            {res['status']}")
    if res["mismatches"]:
        print("Mismatches detected:")
        for m in res["mismatches"]:
            print(f"  - {m}")
    return res


if __name__ == "__main__":
    if "--sync" in sys.argv:
        res = sync_and_rebuild_runtime_index()
    else:
        res = check_index_consistency()
    print_consistency_report()
