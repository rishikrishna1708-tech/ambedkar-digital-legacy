import io
import json
import os
import shutil
import uuid
import logging
import hashlib
import re
from typing import Optional, List
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel

from backend.config import DATA_MODE, IS_DEMO_MODE, GEMINI_API_KEY, UPLOAD_DIR
from backend.database.db import get_db_connection
from backend.services.retrieval import retrieval_pipeline
from backend.services.evidence_gate import evidence_gate
from backend.services.ocr_service import ocr_service
from backend.services.faiss_service import faiss_service
from backend.services.embeddings import embedding_service

logger = logging.getLogger("daic.api")
api_router = APIRouter(prefix="/api")

# Pydantic models for request bodies
class AskRequest(BaseModel):
    question: str
    language: Optional[str] = "en"

class RetrieveRequest(BaseModel):
    query: str
    top_k: Optional[int] = 15

class VerifyRequest(BaseModel):
    query: str
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None

class ResearchSaveRequest(BaseModel):
    collection_id: Optional[str] = "DEFAULT_COLLECTION"
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    title: str
    quote: Optional[str] = None
    page: Optional[int] = None
    source_title: Optional[str] = None
    notes: Optional[str] = None

class FeedbackRequest(BaseModel):
    query: str
    answer_id: Optional[str] = None
    rating: int  # 1 for thumbs up, -1 for thumbs down
    comments: Optional[str] = None

class OCRReviewRequest(BaseModel):
    ocr_id: str
    recognized_text: str
    status: str = "archivist_reviewed"
    notes: Optional[str] = None
    reason: Optional[str] = None
    changed_by: Optional[str] = "Chief Archivist"

class MetadataUpdateRequest(BaseModel):
    document_id: str
    title: str
    type: str
    year: Optional[int] = None
    collection: str
    author: str
    verification_status: str

# 1. Health & Status
@api_router.get("/health")
def health_check():
    # Report the actual embedding model that is loaded at runtime — not a hardcoded label
    if embedding_service.is_real_model:
        embedding_model_name = "BAAI/bge-m3"
        embedding_status = "real-model-loaded"
    else:
        embedding_model_name = "deterministic-fallback (BAAI/bge-m3 unavailable)"
        embedding_status = "fallback-projection"
    return {
        "status": "healthy",
        "service": "DAIC Archive API",
        "data_mode": DATA_MODE,
        "is_demo_mode": IS_DEMO_MODE,
        "gemini_configured": bool(GEMINI_API_KEY),
        "embedding_model": embedding_model_name,
        "embedding_status": embedding_status,
        "embedding_dim": embedding_service.dim,
        "principles": ["PRESERVE", "DISCOVER", "UNDERSTAND", "VERIFY", "LEARN"]
    }

# 2. Ask (Full End-to-End RAG)
@api_router.post("/ask")
async def ask_archive(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    result = await retrieval_pipeline.ask(
        question=req.question,
        language=req.language or "en"
    )
    return result

# 3. Retrieve (Hybrid Retrieval & Explainability)
@api_router.post("/retrieve")
async def retrieve_evidence(req: RetrieveRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    result = await retrieval_pipeline.execute_retrieval(
        question=req.query,
        top_k=req.top_k or 15
    )
    return result

# 4. Verify (Evidence Gate Endpoint)
@api_router.post("/verify")
def verify_evidence(req: VerifyRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if req.chunk_id:
        cursor.execute("""
            SELECT c.id, c.document_id, c.page, c.section_title, c.content, c.provenance_type,
                   d.title as doc_title, d.verification_status
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.id = ?
        """, (req.chunk_id,))
        chunk = cursor.fetchone()
        conn.close()
        if not chunk:
            return {"verified": False, "reason": f"Chunk {req.chunk_id} not found in archive."}
        return {
            "verified": True,
            "chunk_id": chunk["id"],
            "document_id": chunk["document_id"],
            "document_title": chunk["doc_title"],
            "page": chunk["page"],
            "section": chunk["section_title"],
            "verification_status": chunk["verification_status"],
            "provenance_type": chunk["provenance_type"]
        }
    
    conn.close()
    return {"verified": True, "status": "Evidence Gate module active."}

# 5. Archive Catalogue Search & Filter
@api_router.get("/archive")
def list_archive(
    q: Optional[str] = None,
    doc_type: Optional[str] = Query(None, alias="type"),
    year: Optional[int] = None,
    collection: Optional[str] = None,
    language: Optional[str] = None,
    verification_status: Optional[str] = None,
    provenance: Optional[str] = Query(None, alias="provenance_type"),
    limit: int = 50,
    offset: int = 0
):
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if q and q.strip():
        # Search via FTS5 or simple LIKE
        conditions.append("(d.title LIKE ? OR d.summary LIKE ? OR d.collection LIKE ?)")
        term = f"%{q.strip()}%"
        params.extend([term, term, term])

    if doc_type and doc_type != "All":
        conditions.append("d.type = ?")
        params.append(doc_type)

    if year:
        conditions.append("d.year = ?")
        params.append(year)

    if collection and collection != "All":
        conditions.append("d.collection = ?")
        params.append(collection)

    if language and language != "All":
        conditions.append("d.language = ?")
        params.append(language)

    if verification_status and verification_status != "All":
        conditions.append("d.verification_status = ?")
        params.append(verification_status)

    if provenance and provenance != "All":
        conditions.append("d.provenance_type = ?")
        params.append(provenance)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query_sql = f"""
        SELECT d.*, 
               (SELECT COUNT(*) FROM chunks WHERE document_id = d.id) as chunk_count
        FROM documents d
        {where_clause}
        ORDER BY d.year ASC, d.id ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    cursor.execute(query_sql, params)
    docs = [dict(row) for row in cursor.fetchall()]

    cursor.execute(f"SELECT COUNT(*) as total FROM documents d {where_clause}", params[:-2])
    total_count = cursor.fetchone()["total"]

    conn.close()
    return {
        "total": total_count,
        "count": len(docs),
        "data_mode": DATA_MODE,
        "documents": docs
    }

# 6. Single Document Detail
@api_router.get("/archive/{doc_id}")
def get_document(doc_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    cursor.execute("SELECT * FROM chunks WHERE document_id = ? ORDER BY page ASC, chunk_index ASC", (doc_id,))
    chunks = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM ocr_results WHERE document_id = ? ORDER BY page ASC", (doc_id,))
    ocr = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "document": dict(doc),
        "chunks": chunks,
        "ocr_results": ocr
    }

# 7. Timeline
@api_router.get("/timeline")
def get_timeline(category: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if category and category != "All":
        cursor.execute("SELECT * FROM timeline_events WHERE category = ? ORDER BY year ASC", (category,))
    else:
        cursor.execute("SELECT * FROM timeline_events ORDER BY year ASC")

    events = []
    for row in cursor.fetchall():
        evt = dict(row)
        evt["related_documents"] = json.loads(evt["related_documents"] or "[]")
        evt["related_people"] = json.loads(evt["related_people"] or "[]")
        evt["related_media"] = json.loads(evt["related_media"] or "[]")
        events.append(evt)

    conn.close()
    return {"events": events}

# 8. Knowledge Graph
@api_router.get("/knowledge")
def get_knowledge_graph():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM knowledge_entities")
    nodes = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM knowledge_relations")
    edges = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "nodes": nodes,
        "edges": edges
    }

# 9. Media Assets
@api_router.get("/media")
def get_media_assets(media_type: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    if media_type and media_type != "All":
        cursor.execute("SELECT * FROM media WHERE type = ?", (media_type,))
    else:
        cursor.execute("SELECT * FROM media")

    media_items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"media": media_items}

# 10. Stories
@api_router.get("/stories")
def get_stories():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, slug, title, subtitle, cover_image, excerpt, timeline_year, provenance_type FROM stories")
    stories = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"stories": stories}

@api_router.get("/stories/{slug}")
def get_story_detail(slug: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM stories WHERE slug = ?", (slug,))
    story = cursor.fetchone()
    if not story:
        conn.close()
        raise HTTPException(status_code=404, detail="Story not found")

    res = dict(story)
    res["chapters"] = json.loads(res["content_json"])
    res["sources"] = json.loads(res["sources_json"])

    # Fetch source document summaries
    source_docs = []
    for doc_id in res["sources"]:
        cursor.execute("SELECT id, title, year, collection, source_institution FROM documents WHERE id = ?", (doc_id,))
        s_doc = cursor.fetchone()
        if s_doc:
            source_docs.append(dict(s_doc))
    res["source_documents"] = source_docs

    conn.close()
    return res

# 11. Research Notebook / Collection
@api_router.get("/research")
def get_research_items(collection_id: str = "DEFAULT_COLLECTION"):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM research_collections WHERE id = ?", (collection_id,))
    coll = cursor.fetchone()

    cursor.execute("SELECT * FROM research_items WHERE collection_id = ? ORDER BY created_at DESC", (collection_id,))
    items = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "collection": dict(coll) if coll else None,
        "items": items
    }

@api_router.post("/research/save")
def save_research_item(req: ResearchSaveRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    item_id = f"res_{uuid.uuid4().hex[:8]}"
    cursor.execute("""
        INSERT INTO research_items (
            id, collection_id, document_id, chunk_id, title, quote, page, source_title, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_id, req.collection_id, req.document_id, req.chunk_id,
        req.title, req.quote, req.page, req.source_title, req.notes
    ))

    conn.commit()
    conn.close()
    return {"status": "success", "id": item_id, "message": "Saved to Research Collection."}

@api_router.delete("/research/{item_id}")
def delete_research_item(item_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM research_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "deleted": item_id}

# 12. Feedback
@api_router.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (action, entity_type, details)
        VALUES ('USER_FEEDBACK', 'QUERY', ?)
    """, (json.dumps(req.dict()),))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Feedback recorded. Thank you for contributing to archive quality."}

# 13. Admin Dashboard & Ingestion
@api_router.get("/admin/stats")
def get_admin_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    _ensure_ingest_jobs_table(cursor)

    cursor.execute("SELECT COUNT(*) as count FROM documents")
    total_docs = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE provenance_type = 'REAL ARCHIVAL DATA'")
    real_docs = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE provenance_type = 'USER-UPLOADED DATA'")
    user_uploaded_docs = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE provenance_type = 'DEMO DATA'")
    demo_docs_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE verification_status = 'VERIFIED SOURCE'")
    verified_docs = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM documents WHERE ocr_status = 'pending_review'")
    pending_review_docs = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM chunks")
    total_chunks = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM ocr_results WHERE archivist_status = 'pending_review'")
    ocr_pending = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM ocr_results WHERE archivist_status = 'archivist_reviewed'")
    ocr_reviewed = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM ocr_results WHERE archivist_status = 'verified'")
    ocr_verified_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM ocr_results")
    total_ocr_records = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM archive_fts")
    fts_indexed = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM media")
    total_media = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM ingest_jobs WHERE status = 'DUPLICATE'")
    duplicate_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM ingest_jobs WHERE status IN ('OCR_FAILED', 'INDEXING_FAILED')")
    failed_count = cursor.fetchone()["count"]

    cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10")
    recent_logs = [dict(r) for r in cursor.fetchall()]

    conn.close()

    faiss_vector_count = len(faiss_service.metadata)
    embedding_model_name = "BAAI/bge-m3" if embedding_service.is_real_model else "deterministic-fallback"
    embedding_dim = embedding_service.dim

    return {
        "total_documents": total_docs,
        "real_archival_documents": real_docs,
        "user_uploaded_documents": user_uploaded_docs,
        "demo_documents": demo_docs_count,
        "verified_documents": verified_docs,
        "pending_review_documents": pending_review_docs,
        "total_chunks": total_chunks,
        "verified_chunks": total_chunks,
        "fts_indexed_chunks": fts_indexed,
        "faiss_vectors": faiss_vector_count,
        "total_ocr_records": total_ocr_records,
        "ocr_pending_review": ocr_pending,
        "ocr_reviewed": ocr_reviewed,
        "ocr_verified": ocr_verified_count,
        "total_media": total_media,
        "duplicate_count": duplicate_count,
        "failed_count": failed_count,
        "data_mode": DATA_MODE,
        "embedding_model": embedding_model_name,
        "embedding_dim": embedding_dim,
        "recent_logs": recent_logs
    }


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}

def _get_next_adl_id(cursor) -> str:
    highest = 0
    cursor.execute("SELECT id FROM documents WHERE id LIKE 'ADL-MS-%'")
    for r in cursor.fetchall():
        m = re.search(r"ADL-MS-(\d+)", r["id"])
        if m:
            val = int(m.group(1))
            if val > highest:
                highest = val

    cursor.execute("SELECT document_id FROM ingest_jobs WHERE document_id LIKE 'ADL-MS-%'")
    for r in cursor.fetchall():
        if r["document_id"]:
            m = re.search(r"ADL-MS-(\d+)", r["document_id"])
            if m:
                val = int(m.group(1))
                if val > highest:
                    highest = val

    if UPLOAD_DIR.exists():
        for f in UPLOAD_DIR.glob("ADL-MS-*"):
            m = re.search(r"ADL-MS-(\d+)", f.name)
            if m:
                val = int(m.group(1))
                if val > highest:
                    highest = val

    return f"ADL-MS-{highest + 1:04d}"

def _ensure_ingest_jobs_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingest_jobs (
            id TEXT PRIMARY KEY,
            document_id TEXT,
            original_filename TEXT NOT NULL,
            sha256_hash TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            status TEXT DEFAULT 'UPLOADED',
            duplicate_of TEXT,
            error_message TEXT,
            pages_processed INTEGER DEFAULT 0,
            chunks_indexed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

@api_router.post("/admin/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: str = Form("Manuscript"),
    year: Optional[int] = Form(None),
    collection: str = Form("Archival Ingestions"),
    author: Optional[str] = Form(None),
    source_institution: Optional[str] = Form(None),
    language: str = Form("en"),
    description: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    edition: Optional[str] = Form(None),
    volume: Optional[str] = Form(None),
    page_count: Optional[int] = Form(None),
    rights: Optional[str] = Form(None),
    provenance_type: str = Form("USER-UPLOADED DATA")
):
    """
    Archival Ingestion Pipeline:
    1. Validation: Strictly allow PDF, PNG, JPG, JPEG, TIFF, TIF
    2. Preservation: Generate sequential ID (ADL-MS-0001), compute SHA-256, preserve exact file
    3. Extraction & OCR: Extract pages and facsimile images, store in ocr_results as 'pending_review'
    4. Isolation: Do NOT index into FTS5 or FAISS until archivist human verification
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: PDF, PNG, JPG, JPEG, TIFF, TIF."
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()
    doc_id = _get_next_adl_id(cursor)

    saved_filename = f"{doc_id}{ext}"
    saved_path = UPLOAD_DIR / saved_filename

    # Read all bytes first, compute SHA-256, then check for duplicates
    content = await file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()
    file_size = len(content)

    # Duplicate check
    cursor.execute("SELECT id, original_filename, title FROM documents WHERE sha256_hash = ?", (sha256_hash,))
    existing = cursor.fetchone()
    if existing:
        existing_doc_id = existing["id"]
        existing_fn = existing["original_filename"] or existing["title"] or "unknown"
        # Record the duplicate attempt
        _ensure_ingest_jobs_table(cursor)
        cursor.execute("""
            INSERT OR IGNORE INTO ingest_jobs (id, document_id, original_filename, sha256_hash, file_type, file_size, status, duplicate_of)
            VALUES (?, NULL, ?, ?, ?, ?, 'DUPLICATE', ?)
        """, (f"dup_{sha256_hash[:16]}", file.filename, sha256_hash, ext.replace(".","").upper(), file_size, existing_doc_id))
        conn.commit()
        conn.close()
        return {
            "status": "duplicate",
            "document_id": None,
            "duplicate_of": existing_doc_id,
            "existing_document_id": existing_doc_id,
            "existing_filename": existing_fn,
            "sha256_hash": sha256_hash,
            "original_filename": file.filename,
            "message": f"DUPLICATE DOCUMENT\nExisting Document ID: {existing_doc_id}\nExisting filename: {existing_fn}"
        }

    # Write file to disk
    with open(saved_path, "wb") as f:
        f.write(content)

    # Run OCR / page extraction (saves to ocr_results with status 'pending_review')
    ocr_res = ocr_service.process_document(saved_path, doc_id=doc_id, title=title)

    # Insert document record into DB with unverified status
    clean_author = author.strip() if author and author.strip() else "NOT PROVIDED"
    clean_institution = source_institution.strip() if source_institution and source_institution.strip() else "NOT PROVIDED"
    clean_edition = edition.strip() if edition and edition.strip() else None
    clean_volume = volume.strip() if volume and volume.strip() else None
    clean_rights = rights.strip() if rights and rights.strip() else "NOT PROVIDED"
    final_page_count = page_count if (page_count is not None and page_count > 0) else ocr_res["pages_processed"]
    summary_text = description.strip() if description and description.strip() else f"Archival document: {title}. Keywords: {keywords or 'Historical'}."

    cursor.execute("""
        INSERT INTO documents (
            id, title, type, year, date_str, collection, author, language,
            source_institution, source_url, page_count, digitization_method,
            ocr_status, verification_status, provenance_type, summary,
            original_filename, file_path, file_type, file_size, sha256_hash,
            edition, volume, rights, upload_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        doc_id, title, doc_type, year, str(year) if year else "Unknown", collection,
        clean_author, language, clean_institution, f"/uploads/{saved_filename}",
        final_page_count, "PyMuPDF High-Resolution Ingestion Pipeline",
        "pending_review", "UNVERIFIED (NEW INGESTION)", provenance_type, summary_text,
        file.filename, str(saved_path), ext.replace(".", "").upper(), file_size, sha256_hash,
        clean_edition, clean_volume, clean_rights
    ))

    # Insert ingest_jobs record for this upload
    _ensure_ingest_jobs_table(cursor)
    cursor.execute("""
        INSERT OR IGNORE INTO ingest_jobs (id, document_id, original_filename, sha256_hash, file_type, file_size, status, pages_processed)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING_REVIEW', ?)
    """, (f"job_{doc_id}", doc_id, file.filename, sha256_hash, ext.replace(".","").upper(), file_size, ocr_res["pages_processed"]))

    # Log to institutional audit trail
    cursor.execute("""
        INSERT INTO audit_logs (action, entity_type, entity_id, user, details)
        VALUES ('DOCUMENT_UPLOAD', 'DOCUMENT', ?, 'archivist', ?)
    """, (doc_id, f"Preserved '{file.filename}' as {doc_id} (SHA-256: {sha256_hash[:16]}..., size: {file_size} bytes). Initial status: pending_review."))

    conn.commit()
    conn.close()

    logger.info(f"Preserved document {doc_id} ('{title}') with SHA-256: {sha256_hash}. Status: pending_review.")

    return {
        "status": "success",
        "document_id": doc_id,
        "original_filename": file.filename,
        "file_type": ext.replace(".", "").upper(),
        "file_size": file_size,
        "sha256_hash": sha256_hash,
        "pages_processed": ocr_res["pages_processed"],
        "ocr_status": "pending_review",
        "verification_status": "UNVERIFIED (NEW INGESTION)",
        "provenance_type": provenance_type,
        "message": f"Document '{title}' preserved under ID {doc_id}. OCR extracted and queued for archivist review."
    }

@api_router.get("/admin/ocr-pending")
def get_pending_ocr_records(doc_id: Optional[str] = None):
    """Returns OCR records pending review or recently reviewed for archivist verification."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if doc_id:
        cursor.execute("""
            SELECT o.*, d.title as doc_title, d.author, d.collection, d.provenance_type, d.verification_status
            FROM ocr_results o
            JOIN documents d ON o.document_id = d.id
            WHERE o.document_id = ?
            ORDER BY o.page ASC
        """, (doc_id,))
    else:
        cursor.execute("""
            SELECT o.*, d.title as doc_title, d.author, d.collection, d.provenance_type, d.verification_status
            FROM ocr_results o
            JOIN documents d ON o.document_id = d.id
            ORDER BY 
                CASE WHEN o.archivist_status = 'pending_review' THEN 0 
                     WHEN o.archivist_status = 'archivist_reviewed' THEN 1 
                     ELSE 2 END,
                o.updated_at DESC, o.page ASC
            LIMIT 50
        """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"count": len(rows), "records": rows}

@api_router.post("/admin/ocr-review")
def review_ocr_result(req: OCRReviewRequest):
    """
    Archivist Human Review Station:
    - Edit OCR text and mark as 'archivist_reviewed'
    - When marked as 'verified': converts verified text to chunks, indexes into FTS5,
      generates embeddings, adds to FAISS, and promotes document to 'VERIFIED SOURCE'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT o.*, d.title as doc_title, d.collection, d.author, d.provenance_type
        FROM ocr_results o
        JOIN documents d ON o.document_id = d.id
        WHERE o.id = ?
    """, (req.ocr_id,))
    record = cursor.fetchone()
    if not record:
        conn.close()
        raise HTTPException(status_code=404, detail=f"OCR record '{req.ocr_id}' not found.")

    doc_id = record["document_id"]
    page_num = record["page"]
    doc_title = record["doc_title"]
    doc_collection = record["collection"]
    doc_author = record["author"]
    doc_provenance = record["provenance_type"]
    old_text = record["recognized_text"]
    new_text = req.recognized_text
    new_status = req.status

    # Record OCR revision history in audit trail
    cursor.execute("""
        INSERT INTO ocr_revisions (ocr_id, document_id, page_number, old_text, new_text, changed_by, action, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.ocr_id, doc_id, page_num, old_text, new_text,
        req.changed_by or "Chief Archivist", new_status.upper(), req.reason or req.notes
    ))

    # Update OCR record with corrected text and new status
    cursor.execute("""
        UPDATE ocr_results
        SET recognized_text = ?, archivist_status = ?, reviewed_by = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_text, new_status, req.changed_by or "Chief Archivist", req.notes, req.ocr_id))

    cursor.execute("""
        INSERT INTO audit_logs (action, entity_type, entity_id, user, details)
        VALUES ('OCR_REVIEW', 'OCR_RESULT', ?, 'archivist', ?)
    """, (req.ocr_id, f"Archivist updated OCR record {req.ocr_id} with status '{new_status}'."))

    chunks_created = []

    # Clean up any previously verified chunks for this page (if re-verifying or rejecting/returning)
    cursor.execute("SELECT id FROM chunks WHERE document_id = ? AND page = ?", (doc_id, page_num))
    prev_chunk_rows = cursor.fetchall()
    prev_chunk_ids = [r["id"] for r in prev_chunk_rows]
    if prev_chunk_ids:
        for cid in prev_chunk_ids:
            cursor.execute("DELETE FROM archive_fts WHERE chunk_id = ?", (cid,))
        cursor.execute("DELETE FROM chunks WHERE document_id = ? AND page = ?", (doc_id, page_num))
        faiss_service.remove_chunks_by_ids(prev_chunk_ids)

    if new_status == "verified":
        # 1. Chunk verified text: logical paragraphs preserving source page
        clean_text = new_text.strip()
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [clean_text]

        cursor.execute("SELECT COUNT(*) as count FROM chunks WHERE document_id = ?", (doc_id,))
        start_chunk_idx = cursor.fetchone()["count"]

        for idx, para in enumerate(paragraphs):
            c_num = start_chunk_idx + idx + 1
            chunk_id = f"{doc_id}-C{c_num:03d}"
            sec_title = f"{doc_title} (Page {page_num})"

            # Insert chunk into chunks table
            cursor.execute("""
                INSERT OR REPLACE INTO chunks (
                    id, document_id, chunk_index, page, section_title, content,
                    char_count, word_count, provenance_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id, doc_id, c_num, page_num, sec_title, para,
                len(para), len(para.split()), doc_provenance or "USER-UPLOADED DATA"
            ))

            # Index into SQLite FTS5
            cursor.execute("""
                INSERT INTO archive_fts (chunk_id, document_id, title, content, collection, author, section_title)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id, doc_id, doc_title, para, doc_collection, doc_author, sec_title
            ))

            chunks_created.append({
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "page": page_num,
                "section_title": sec_title,
                "title": doc_title,
                "collection": doc_collection,
                "author": doc_author,
                "content": para,
                "provenance_type": doc_provenance or "USER-UPLOADED DATA",
                "verification_status": "VERIFIED SOURCE"
            })

        # Update document verification status
        cursor.execute("""
            UPDATE documents 
            SET ocr_status = 'verified', verification_status = 'VERIFIED SOURCE'
            WHERE id = ?
        """, (doc_id,))

        cursor.execute("""
            INSERT INTO audit_logs (action, entity_type, entity_id, user, details)
            VALUES ('OCR_VERIFY', 'DOCUMENT', ?, 'archivist', ?)
        """, (doc_id, f"Verified page {page_num} of {doc_id}. Created and indexed {len(chunks_created)} chunk(s). Status: VERIFIED SOURCE."))

    elif new_status in ("rejected", "pending_review", "archivist_reviewed"):
        # Check if document has any other verified pages remaining
        cursor.execute("SELECT COUNT(*) as cnt FROM ocr_results WHERE document_id = ? AND archivist_status = 'verified' AND id != ?", (doc_id, req.ocr_id))
        verified_cnt = cursor.fetchone()["cnt"]
        if verified_cnt == 0:
            cursor.execute("""
                UPDATE documents
                SET ocr_status = ?, verification_status = 'UNVERIFIED (NEW INGESTION)'
                WHERE id = ?
            """, (new_status, doc_id))
        else:
            cursor.execute("""
                UPDATE documents
                SET ocr_status = ?
                WHERE id = ?
            """, (new_status, doc_id))

    conn.commit()
    conn.close()

    # Index into FAISS / dense vector index if verified
    if chunks_created:
        faiss_service.add_chunks(chunks_created)
        logger.info(f"Indexed {len(chunks_created)} verified chunk(s) from {doc_id} into FAISS.")

    return {
        "status": "success",
        "ocr_id": req.ocr_id,
        "document_id": doc_id,
        "page": page_num,
        "archivist_status": new_status,
        "verification_status": "VERIFIED SOURCE" if new_status == "verified" else "UNVERIFIED (NEW INGESTION)",
        "chunks_indexed": len(chunks_created),
        "message": f"OCR record {req.ocr_id} updated with status '{new_status}'." + (f" Indexed {len(chunks_created)} chunk(s) into FTS5 and FAISS." if new_status == "verified" else "")
    }


# ─────────────────────────────────────────────────────────────
# Phase II: Batch Upload Endpoint
# ─────────────────────────────────────────────────────────────
@api_router.post("/admin/upload-batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    doc_type: str = Form("Manuscript"),
    year: Optional[int] = Form(None),
    collection: str = Form("Archival Ingestions"),
    author: Optional[str] = Form(None),
    source_institution: Optional[str] = Form(None),
    language: str = Form("en"),
    description: Optional[str] = Form(None),
    edition: Optional[str] = Form(None),
    volume: Optional[str] = Form(None),
    page_count: Optional[int] = Form(None),
    rights: Optional[str] = Form(None),
    provenance_type: str = Form("USER-UPLOADED DATA")
):
    """
    Batch Archival Ingestion Pipeline.
    Processes multiple files sequentially. Per-file errors do not abort the entire batch.
    Returns per-file status: success | DUPLICATE | OCR_FAILED | UNSUPPORTED_FORMAT
    """
    results = []
    successful = 0
    duplicates = 0
    failed = 0
    unsupported = 0

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    clean_author = author.strip() if author and author.strip() else "NOT PROVIDED"
    clean_institution = source_institution.strip() if source_institution and source_institution.strip() else "NOT PROVIDED"
    clean_edition = edition.strip() if edition and edition.strip() else None
    clean_volume = volume.strip() if volume and volume.strip() else None
    clean_rights = rights.strip() if rights and rights.strip() else "NOT PROVIDED"
    summary_base = description.strip() if description and description.strip() else ""

    for file_index, upload_file in enumerate(files):
        file_result = {
            "index": file_index + 1,
            "total": len(files),
            "filename": upload_file.filename,
            "status": "unknown",
            "document_id": None,
            "duplicate_of": None,
            "existing_document_id": None,
            "existing_filename": None,
            "error": None,
            "sha256_hash": None,
            "pages_processed": 0,
        }

        ext = Path(upload_file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            file_result["status"] = "UNSUPPORTED_FORMAT"
            file_result["error"] = f"Unsupported format '{ext}'. Allowed: PDF, PNG, JPG, JPEG, TIFF, TIF"
            unsupported += 1
            results.append(file_result)
            continue

        conn = None
        try:
            content = await upload_file.read()
            sha256_hash = hashlib.sha256(content).hexdigest()
            file_size = len(content)
            file_result["sha256_hash"] = sha256_hash

            conn = get_db_connection()
            cursor = conn.cursor()
            _ensure_ingest_jobs_table(cursor)

            # Duplicate check
            cursor.execute("SELECT id, original_filename, title FROM documents WHERE sha256_hash = ?", (sha256_hash,))
            existing = cursor.fetchone()
            if existing:
                existing_doc_id = existing["id"]
                existing_fn = existing["original_filename"] or existing["title"] or "unknown"
                cursor.execute("""
                    INSERT OR IGNORE INTO ingest_jobs (id, document_id, original_filename, sha256_hash, file_type, file_size, status, duplicate_of)
                    VALUES (?, NULL, ?, ?, ?, ?, 'DUPLICATE', ?)
                """, (f"dup_{sha256_hash[:16]}_{file_index}", upload_file.filename, sha256_hash,
                      ext.replace(".", "").upper(), file_size, existing_doc_id))
                conn.commit()
                conn.close()
                conn = None
                file_result["status"] = "DUPLICATE"
                file_result["duplicate_of"] = existing_doc_id
                file_result["existing_document_id"] = existing_doc_id
                file_result["existing_filename"] = existing_fn
                file_result["message"] = f"DUPLICATE DOCUMENT\nExisting Document ID: {existing_doc_id}\nExisting filename: {existing_fn}"
                duplicates += 1
                results.append(file_result)
                continue

            doc_id = _get_next_adl_id(cursor)
            saved_filename = f"{doc_id}{ext}"
            saved_path = UPLOAD_DIR / saved_filename

            with open(saved_path, "wb") as f:
                f.write(content)

            # Use original filename stem as title if no shared title
            auto_title = Path(upload_file.filename).stem.replace("_", " ").replace("-", " ").title()
            doc_title = auto_title
            summary_text = summary_base if summary_base else f"Archival document: {doc_title}."

            ocr_res = ocr_service.process_document(saved_path, doc_id=doc_id, title=doc_title)
            final_pages = page_count if (page_count is not None and page_count > 0) else ocr_res["pages_processed"]

            cursor.execute("""
                INSERT INTO documents (
                    id, title, type, year, date_str, collection, author, language,
                    source_institution, source_url, page_count, digitization_method,
                    ocr_status, verification_status, provenance_type, summary,
                    original_filename, file_path, file_type, file_size, sha256_hash,
                    edition, volume, rights, upload_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                doc_id, doc_title, doc_type, year, str(year) if year else "Unknown", collection,
                clean_author, language, clean_institution, f"/uploads/{saved_filename}",
                final_pages, "PyMuPDF High-Resolution Ingestion Pipeline",
                "pending_review", "UNVERIFIED (NEW INGESTION)", provenance_type, summary_text,
                upload_file.filename, str(saved_path), ext.replace(".", "").upper(), file_size, sha256_hash,
                clean_edition, clean_volume, clean_rights
            ))

            cursor.execute("""
                INSERT OR IGNORE INTO ingest_jobs (id, document_id, original_filename, sha256_hash, file_type, file_size, status, pages_processed)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING_REVIEW', ?)
            """, (f"job_{doc_id}", doc_id, upload_file.filename, sha256_hash,
                  ext.replace(".", "").upper(), file_size, ocr_res["pages_processed"]))

            cursor.execute("""
                INSERT INTO audit_logs (action, entity_type, entity_id, user, details)
                VALUES ('BATCH_UPLOAD', 'DOCUMENT', ?, 'archivist', ?)
            """, (doc_id, f"[Batch {file_index+1}/{len(files)}] Preserved '{upload_file.filename}' as {doc_id} "
                          f"(SHA-256: {sha256_hash[:16]}...). Status: pending_review."))

            conn.commit()
            conn.close()
            conn = None

            file_result["status"] = "success"
            file_result["document_id"] = doc_id
            file_result["pages_processed"] = ocr_res["pages_processed"]
            file_result["ocr_status"] = "pending_review"
            file_result["verification_status"] = "UNVERIFIED (NEW INGESTION)"
            file_result["message"] = f"Preserved as {doc_id}. {ocr_res['pages_processed']} page(s) queued for OCR review."
            successful += 1
            logger.info(f"Batch [{file_index+1}/{len(files)}]: Preserved '{upload_file.filename}' as {doc_id}")

        except Exception as e:
            logger.error(f"Batch upload error for '{upload_file.filename}': {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            file_result["status"] = "OCR_FAILED"
            file_result["error"] = str(e)
            failed += 1

        results.append(file_result)

    return {
        "total": len(files),
        "successful": successful,
        "duplicates": duplicates,
        "failed": failed,
        "unsupported": unsupported,
        "results": results
    }


# ─────────────────────────────────────────────────────────────
# Phase II: Ingest Jobs History
# ─────────────────────────────────────────────────────────────
@api_router.get("/admin/ingest-jobs")
def get_ingest_jobs(limit: int = 50, offset: int = 0):
    """Returns paginated ingestion job history with document metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    _ensure_ingest_jobs_table(cursor)
    cursor.execute("""
        SELECT
            j.id, j.document_id, j.original_filename, j.file_type, j.file_size,
            CASE WHEN j.sha256_hash IS NOT NULL THEN substr(j.sha256_hash, 1, 16) || '...' ELSE NULL END as sha256_preview,
            j.status, j.duplicate_of, j.error_message, j.pages_processed, j.chunks_indexed,
            j.created_at,
            d.title, d.provenance_type, d.verification_status, d.ocr_status
        FROM ingest_jobs j
        LEFT JOIN documents d ON j.document_id = d.id
        ORDER BY j.created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    jobs = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) as cnt FROM ingest_jobs")
    total = cursor.fetchone()["cnt"]
    conn.close()
    return {"total": total, "jobs": jobs}


# ─────────────────────────────────────────────────────────────
# Phase II: Document Ingestion Table
# ─────────────────────────────────────────────────────────────
@api_router.get("/admin/documents")
def get_admin_documents(limit: int = 100, offset: int = 0):
    """Returns the document ingestion table for the admin dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            d.id, d.title, d.type, d.original_filename, d.file_type,
            d.provenance_type, d.verification_status, d.ocr_status,
            d.created_at, d.page_count,
            CASE WHEN d.sha256_hash IS NOT NULL THEN substr(d.sha256_hash, 1, 16) || '...' ELSE NULL END as sha256_preview,
            (SELECT COUNT(*) FROM chunks WHERE document_id = d.id) as chunk_count
        FROM documents d
        ORDER BY d.created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    docs = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT COUNT(*) as cnt FROM documents")
    total = cursor.fetchone()["cnt"]
    conn.close()
    return {"total": total, "documents": docs}


# ─────────────────────────────────────────────────────────────
# Phase II: OCR Revision History Audit Trail
# ─────────────────────────────────────────────────────────────
@api_router.get("/admin/ocr-revisions")
def get_ocr_revisions(document_id: Optional[str] = None, ocr_id: Optional[str] = None, limit: int = 50):
    """Returns OCR revisions audit trail."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if ocr_id:
        cursor.execute("SELECT * FROM ocr_revisions WHERE ocr_id = ? ORDER BY created_at DESC LIMIT ?", (ocr_id, limit))
    elif document_id:
        cursor.execute("SELECT * FROM ocr_revisions WHERE document_id = ? ORDER BY created_at DESC LIMIT ?", (document_id, limit))
    else:
        cursor.execute("SELECT * FROM ocr_revisions ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"count": len(rows), "revisions": rows}


# ─────────────────────────────────────────────────────────────
# Phase II: Index Consistency Validation
# ─────────────────────────────────────────────────────────────
@api_router.get("/admin/index-consistency")
def get_index_consistency_endpoint():
    """Returns the live consistency validation check across SQLite, FTS5, and FAISS."""
    from backend.services.index_validator import check_index_consistency
    return check_index_consistency()

