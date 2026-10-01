import sqlite3
import json
import logging
from pathlib import Path
from backend.config import DB_PATH

logger = logging.getLogger("daic.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        type TEXT NOT NULL,              -- Book, Speech, Manuscript, CAD, Photograph, Letter, Newspaper, Audio, Video
        year INTEGER,
        date_str TEXT,
        collection TEXT NOT NULL,
        author TEXT NOT NULL,
        language TEXT DEFAULT 'en',
        source_institution TEXT NOT NULL,
        source_url TEXT,
        page_count INTEGER DEFAULT 1,
        digitization_method TEXT,
        ocr_status TEXT DEFAULT 'verified', -- pending_review, archivist_reviewed, verified
        verification_status TEXT DEFAULT 'VERIFIED SOURCE', -- VERIFIED SOURCE, DEMO DATA, UNVERIFIED (NEW INGESTION)
        provenance_type TEXT DEFAULT 'DEMO DATA', -- DEMO DATA, REAL ARCHIVAL DATA, USER-UPLOADED DATA
        summary TEXT,
        original_filename TEXT,
        file_path TEXT,
        file_type TEXT,
        file_size INTEGER,
        sha256_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Check and add missing columns to documents table for schema compatibility
    cursor.execute("PRAGMA table_info(documents)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_type in [
        ("original_filename", "TEXT"),
        ("file_path", "TEXT"),
        ("file_type", "TEXT"),
        ("file_size", "INTEGER"),
        ("sha256_hash", "TEXT"),
        ("edition", "TEXT"),
        ("volume", "TEXT"),
        ("rights", "TEXT"),
        ("upload_timestamp", "TIMESTAMP"),
    ]:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type};")

    # 2. Document Chunks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        page INTEGER NOT NULL,
        section_title TEXT,
        content TEXT NOT NULL,
        char_count INTEGER,
        word_count INTEGER,
        provenance_type TEXT DEFAULT 'DEMO DATA',
        FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
    );
    """)

    # 3. FTS5 Virtual Table for BM25 Lexical Retrieval
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS archive_fts USING fts5(
        chunk_id UNINDEXED,
        document_id UNINDEXED,
        title,
        content,
        collection,
        author,
        section_title,
        tokenize = 'unicode61'
    );
    """)

    # 4. Sources Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        institution TEXT NOT NULL,
        collection_name TEXT NOT NULL,
        description TEXT,
        url TEXT,
        verified BOOLEAN DEFAULT 1,
        provenance_type TEXT DEFAULT 'DEMO DATA'
    );
    """)

    # 5. Media Assets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        type TEXT NOT NULL,              -- audio, video, photo, documentary, interview
        date TEXT,
        duration TEXT,
        collection TEXT,
        description TEXT,
        thumbnail_url TEXT,
        media_url TEXT,
        transcript TEXT,
        audio_narration_text TEXT,
        provenance_type TEXT DEFAULT 'DEMO DATA'
    );
    """)

    # 6. Timeline Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timeline_events (
        id TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        date_str TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,          -- Life, Education, Social movements, Constitution, Politics, Economics, Writings
        description TEXT NOT NULL,
        related_documents TEXT,          -- JSON list of document IDs
        related_people TEXT,             -- JSON list of names
        related_media TEXT,              -- JSON list of media IDs
        quote TEXT,
        provenance_type TEXT DEFAULT 'DEMO DATA'
    );
    """)

    # 7. Knowledge Graph Entities & Relationships
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_entities (
        id TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        category TEXT NOT NULL,          -- Person, Idea, Document, Event, Institution, Place
        description TEXT,
        archival_ref TEXT,
        document_id TEXT,
        provenance_type TEXT DEFAULT 'DEMO DATA'
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_relations (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,
        relation TEXT NOT NULL,
        description TEXT,
        citation_id TEXT,
        FOREIGN KEY (source_id) REFERENCES knowledge_entities (id),
        FOREIGN KEY (target_id) REFERENCES knowledge_entities (id)
    );
    """)

    # 8. Digital Heritage Stories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stories (
        id TEXT PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        subtitle TEXT,
        cover_image TEXT,
        excerpt TEXT,
        timeline_year TEXT,
        content_json TEXT NOT NULL,       -- List of chapters with citations
        sources_json TEXT NOT NULL,       -- List of document/chunk references
        provenance_type TEXT DEFAULT 'DEMO DATA'
    );
    """)

    # 9. Research Collections & Items (User notebook)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS research_collections (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS research_items (
        id TEXT PRIMARY KEY,
        collection_id TEXT NOT NULL,
        document_id TEXT,
        chunk_id TEXT,
        title TEXT NOT NULL,
        quote TEXT,
        page INTEGER,
        source_title TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (collection_id) REFERENCES research_collections (id) ON DELETE CASCADE
    );
    """)

    # 10. OCR Processing & Review Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ocr_results (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page INTEGER NOT NULL,
        image_path TEXT,
        recognized_text TEXT NOT NULL,
        confidence REAL,
        bounding_boxes_json TEXT,
        archivist_status TEXT DEFAULT 'pending_review', -- pending_review, archivist_reviewed, verified
        reviewed_by TEXT,
        notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
    );
    """)

    # 11. Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        user TEXT DEFAULT 'archivist',
        details TEXT
    );
    """)

    # 12. Ingest Jobs — batch ingestion state tracking
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
    );
    """)

    # 13. OCR Revision History Audit Trail
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ocr_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ocr_id TEXT,
        document_id TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        old_text TEXT,
        new_text TEXT,
        changed_by TEXT DEFAULT 'archivist',
        action TEXT DEFAULT 'EDIT',
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")
