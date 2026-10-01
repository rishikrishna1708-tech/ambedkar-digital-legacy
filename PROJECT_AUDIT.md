# PROJECT AUDIT: AMBEDKAR DIGITAL LEGACY (DAIC ARCHIVE)
**Audit Date:** 2026-09-23  
**Status:** Comprehensive Codebase & Architecture Inspection Completed  
**Execution Directive:** Read-only inspection and documentation (No modifications or implementations performed).

---

## Executive Summary

The project is an existing, functional full-stack digital heritage archive platform dedicated to Dr. B. R. Ambedkar. It combines a lightweight **Vanilla JS + HTML5 + Tailwind CSS** frontend with a **FastAPI + SQLite (FTS5) + FAISS (BGE-M3 dense vectors) + Evidence Gate** backend. The system operates under the core archival principle:

$$\text{PRESERVE} \longrightarrow \text{DISCOVER} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{VERIFY} \longrightarrow \text{LEARN}$$

The project is configured to run in **DEMO MODE (Offline Verified)** by default, using an authenticated demo dataset with strict provenance guarantees, while maintaining the exact data pipeline required for real archival datasets.

---

## 1. Complete Inspection of the 17 Checklist Items

### 1. Frontend Framework & Files
- **Framework:** Vanilla JavaScript (ES6+), HTML5, Tailwind CSS (via CDN script), and custom CSS (`frontend/css/styles.css`). No build steps, Node/Webpack/Vite tooling, or heavyweight frontend frameworks are required.
- **HTML Pages (10 Views):**
  - `frontend/index.html`: Institutional landing page, hero search, featured document, milestone highlights, principle banner.
  - `frontend/ask.html`: 3-column AI research assistant with step-by-step retrieval animation, grounded answer card, audio narration player, voice input, and explainability/debug trace.
  - `frontend/archive.html`: Faceted archival catalogue browser with collection, document type, era/year, and language filters.
  - `frontend/manuscripts.html`: Dual-pane manuscript viewer (original historical facsimile on the left, OCR recognized transcript on the right) with zoom and comparison.
  - `frontend/timeline.html`: Interactive vertical chronological timeline (1891–1956) with category filters.
  - `frontend/knowledge.html`: Interactive SVG network graph linking People, Ideas, Documents, Events, and Institutions with an archival entity dossier side panel.
  - `frontend/media.html`: Responsive media repository (audio speeches, historical photographs, documentary video clips) with audio narration player.
  - `frontend/stories.html`: Curated digital heritage narrative journeys anchored to primary citations.
  - `frontend/visitor.html`: 1080p touch-optimized memorial kiosk interface with touch actions and voice inquiry.
  - `frontend/admin.html`: Archivist ingestion portal (file upload, layout extraction, OCR execution, chunking, indexing) and OCR human-review queue.
- **JavaScript Controllers (10 Scripts):**
  - `frontend/js/app.js`: Global application controller (header, footer, research drawer, about modal, speech synthesis/recognition, i18n triggers).
  - `frontend/js/i18n.js`: Multilingual matrix dictionary covering English (`en`), Hindi (`hi`), Marathi (`mr`), Kannada (`kn`), and Tamil (`ta`).
  - `frontend/js/api.js`: Client HTTP wrapper for all FastAPI backend endpoints.
  - `frontend/js/ask.js`: Controller for research queries, retrieval animations, and audio playback.
  - `frontend/js/archive.js`: Controller for catalogue filtering and card rendering.
  - `frontend/js/manuscripts.js`: Controller for facsimile rendering, zoom, and OCR side-by-side comparison.
  - `frontend/js/media.js`: Controller for media grid rendering, category filters, and narration audio.
  - `frontend/js/timeline.js`: Controller for chronological milestone loading and filtering.
  - `frontend/js/stories.js`: Controller for story chapters and cited source lookups.
  - `frontend/js/knowledge.js`: Controller for SVG force-directed/radial network graph and entity dossiers.
  - `frontend/js/visitor.js`: Controller for kiosk touch interactions and localized voice inquiry.
  - `frontend/js/admin.js`: Controller for ingestion upload progress and archivist OCR reviews.
- **Styling & Assets:**
  - `frontend/css/styles.css`: Institutional styling, archival color palettes (Deep Navy `#141F39`, Gold `#D7A940`, Parchment `#F8F4E8`, Emerald `#3B7558`), typography classes, animations.
  - `frontend/assets/`: Archival photograph stills and story cover assets (`media_ambedkar_cad.jpg`, `media_labour.jpg`, `media_mahad.jpg`, `story_constitution.jpg`, `story_labour.jpg`, `story_mahad.jpg`).

---

### 2. Backend Framework & Files
- **Framework:** Python 3.11, FastAPI (`fastapi>=0.110.0`), Uvicorn ASGI server (`uvicorn>=0.28.0`), Pydantic v2 (`pydantic>=2.6.0`), SQLite3 (native standard library with FTS5), FAISS (`faiss-cpu>=1.8.0`), NumPy (`numpy>=1.25.0`), HTTPX (`httpx>=0.27.0`).
- **Backend Files:**
  - `backend/main.py`: ASGI application entry point, static asset mounts, HTML page routes, and lifecycle events.
  - `backend/config.py`: Centralized environment configurations, file paths, thresholds, and operational flags.
  - `backend/api/routes.py`: Comprehensive REST API router (`/api/*`).
  - `backend/database/db.py`: SQLite schema initialization, table definitions, foreign keys, and FTS5 virtual table setup.
  - `backend/database/seed_data.py`: Initial seed data script for documents, chunks, timeline events, knowledge graph nodes/edges, media, and stories.
  - `backend/services/retrieval.py`: Hybrid search pipeline orchestrator (Lexical FTS5 + Dense FAISS + RRF + Reranker + Evidence Gate + Synthesis).
  - `backend/services/fts_service.py`: SQLite FTS5 query builder, token sanitization, and BM25 search service.
  - `backend/services/faiss_service.py`: FAISS `IndexFlatIP` dense vector indexing and cosine similarity search.
  - `backend/services/embeddings.py`: Vector embedding generator (SentenceTransformers with deterministic normalized projection fallback).
  - `backend/services/rrf.py`: Reciprocal Rank Fusion ($k=60$) rank merge algorithm.
  - `backend/services/reranker.py`: Contextual re-ranking module based on query term density and title alignment.
  - `backend/services/evidence_gate.py`: Strict safeguard gate verifying candidate relevance scores ($\ge 0.005$) and primary database document/page presence.
  - `backend/services/gemini_service.py`: Institutional synthesis module (Google Gemini 1.5 Flash API with strict prompt instructions + deterministic grounded synthesis fallback supporting English, Hindi, Marathi, Kannada, and Tamil).
  - `backend/services/ocr_service.py`: Document ingestion OCR pipeline (PyMuPDF layout extraction + PaddleOCR text block recognition simulation/execution).
  - `backend/tests/test_pipeline.py`: Unit and integration test suite covering database, FTS5, FAISS, RRF, reranker, Evidence Gate, and end-to-end query answering.

---

### 3. Current Routing
- **Page Serving Routes (`backend/main.py`):**
  - `GET /` $\rightarrow$ `frontend/index.html`
  - `GET /ask` $\rightarrow$ `frontend/ask.html`
  - `GET /archive-view` & `GET /archive.view` $\rightarrow$ `frontend/archive.html`
  - `GET /manuscripts` $\rightarrow$ `frontend/manuscripts.html`
  - `GET /timeline-view` & `GET /timeline.view` $\rightarrow$ `frontend/timeline.html`
  - `GET /knowledge-view` & `GET /knowledge.view` $\rightarrow$ `frontend/knowledge.html`
  - `GET /media-view` & `GET /media.view` $\rightarrow$ `frontend/media.html`
  - `GET /stories-view` & `GET /stories.view` $\rightarrow$ `frontend/stories.html`
  - `GET /visitor` $\rightarrow$ `frontend/visitor.html`
  - `GET /admin` $\rightarrow$ `frontend/admin.html`
- **Static Asset Mounts (`backend/main.py`):**
  - `/css` $\rightarrow$ `frontend/css/`
  - `/js` $\rightarrow$ `frontend/js/`
  - `/assets` $\rightarrow$ `frontend/assets/`
  - `/uploads` $\rightarrow$ `data/uploads/`

---

### 4. Current Database & Storage
- **Database Engine:** SQLite 3 with FTS5 extension enabled (`PRAGMA foreign_keys = ON;`).
- **Physical File Location:** `data/daic_archive.db` (208 KB).
- **Tables Defined in `backend/database/db.py`:**
  1. `documents`: Metadata for all catalogued publications, debates, and manuscripts.
  2. `chunks`: Text passages segmented by page and section with character and word counts.
  3. `archive_fts`: SQLite FTS5 virtual table for BM25 lexical full-text indexing.
  4. `sources`: Historical partner institutions and source collections.
  5. `media`: Audio, video, and photograph metadata with speech narration scripts.
  6. `timeline_events`: Chronologically sequenced milestones (1891–1956) with related entities.
  7. `knowledge_entities`: Network graph nodes (Person, Idea, Document, Event, Institution, Place).
  8. `knowledge_relations`: Directed graph edges with citations.
  9. `stories`: Long-form narrative journeys structured into chapters.
  10. `research_collections`: User research notebook collections.
  11. `research_items`: Bookmarked citations, quotes, page references, and personal notes.
  12. `ocr_results`: Page-by-page OCR text, confidence ratings, bounding boxes, and archivist review states.
  13. `audit_logs`: Timestamped system and user action trails.

---

### 5. Current Sample / Archive Data
- **Data Mode:** Configured as `DATA_MODE = "demo"` (`IS_DEMO_MODE = True`). All records are explicitly tagged with `provenance_type = "DEMO DATA"`.
- **Primary Archival Documents Seeded (`backend/database/seed_data.py`):**
  1. `BAWS_VOL_10_LABOUR`: *Dr. Babasaheb Ambedkar: Writings and Speeches, Vol. 10* (1942–1946), 560 pages, 3 chunks (8-hour work day, tripartite consultations, maternity benefits).
  2. `BAWS_VOL_05_PROVIDENCE`: *Dr. Babasaheb Ambedkar: Writings and Speeches, Vol. 5* (1945), 482 pages, 2 chunks (sociological analysis, civic equality guarantees).
  3. `CAD_VOL_07_ART17`: *Constituent Assembly Debates, Vol. VII* (29 Nov 1948), 820 pages, 2 chunks (Draft Article 11 / Article 17, abolition of untouchability).
  4. `CAD_FINAL_SPEECH_1949`: *Closing Address to the Constituent Assembly: Social Democracy* (25 Nov 1949), 24 pages, 2 chunks (definition of social democracy, "entering a life of contradictions").
  5. `MAHAD_SATYAGRAHA_1927`: *Declaration of the Mahad Satyagraha and Chavdar Tale Conference* (1927), 18 pages, 1 chunk (Chavdar Tale human equality declaration).
- **Auxiliary Data Seeded:**
  - 8 Timeline Events (1891 birth to 1956 Deekshabhoomi).
  - 10 Knowledge Entities and 8 Knowledge Relations.
  - 3 Media items (Constituent Assembly address photo, Mahad speech audio, Labour conference video).
  - 3 Curated Stories (*Making of the Constitution*, *Mahad Satyagraha*, *Labour Rights*).

---

### 6. Current Manuscripts Page (`frontend/manuscripts.html` & `js/manuscripts.js`)
- **Features Present:**
  - Preserved manuscript catalog cards showing Collection, Title, Date, Language, OCR status, Verification status, and Source institution.
  - Dual-pane layout: High-resolution historical facsimile artifact on the left; OCR recognized transcript on the right.
  - Preset switcher: Supports switching between Mahad Satyagraha (1927), Draft Article 17 (1948), and Labour Proceedings (1942).
  - Interactive zoom controls (`-`, `+`, Reset) for facsimile inspection.
  - "Compare Original / OCR" overlay toggle.
  - 5-stage digitization pipeline indicator (PDF Loaded $\rightarrow$ PyMuPDF Extraction $\rightarrow$ PaddleOCR Engine $\rightarrow$ Text Indexed $\rightarrow$ Archivist Review).
  - Provenance dossier footer (Source Institution, Collection, Document ID, Digitization Standard).

---

### 7. Current Archive Page (`frontend/archive.html` & `js/archive.js`)
- **Features Present:**
  - Real-time search query box by title, topic, or volume.
  - Multi-faceted filter bar:
    - Collection (All, Writings & Speeches, CAD Archive, Historical Manuscripts).
    - Document Type (All, Book, Speech, Constitutional Debate, Manuscript, Photograph, Audio, Video).
    - Year Period (All, 1916–1929, 1930–1939, 1940–1946, 1947–1950, 1951–1956).
    - Language (All, English, Marathi, Hindi, Kannada, Tamil).
  - Live result counter (`results-count-badge`).
  - Provenance cards showing Title, Year, Collection, Document Type, Page Count, Provenance badge, Summary, "Open Original" button, and "Ask AI" direct query button.

---

### 8. Current Ask / AI Page (`frontend/ask.html` & `js/ask.js`)
- **Features Present:**
  - 3-column archival research assistant layout.
  - Query input form with curated preset query suggestions.
  - Step-by-step visual retrieval pipeline animation (FTS5 $\rightarrow$ FAISS $\rightarrow$ RRF $\rightarrow$ Re-ranking $\rightarrow$ Evidence Gate $\rightarrow$ Grounded Answer).
  - Grounded answer presentation with strict citation grounding badge.
  - Audio narration player with Play, Pause, Stop, and Speed controls ($0.75\times$, $1\times$, $1.25\times$, $1.5\times$).
  - Multilingual voice input banner showing active language and live transcript.
  - Primary source citation cards with Document Title, Collection, Page, and direct Evidence Quote.
  - "+ Add to Research" notebook integration.
  - Expandable **Archival Retrieval Trace (RRF / FAISS / FTS5)** explainability panel.
  - Safeguard refusal handling for ungrounded or out-of-scope inquiries.

---

### 9. Current Media Page (`frontend/media.html` & `js/media.js`)
- **Features Present:**
  - Filter tabs: All, Audio, Photographs, Documentaries.
  - Dedicated narration player banner with synchronized Web Speech synthesis.
  - Responsive grid layout: 3 cards per row on desktop, 2 on tablet, 1 on mobile (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`).
  - Strict metadata hierarchy on every media card: `TYPE` $\rightarrow$ `TITLE` $\rightarrow$ `DATE` $\rightarrow$ `COLLECTION` $\rightarrow$ `DESCRIPTION` $\rightarrow$ `SOURCE` $\rightarrow$ `ACTION`.
  - Actions: Audio playback, modal full-resolution image inspection, and primary citation linking.

---

### 10. Existing OCR Implementation (`backend/services/ocr_service.py`)
- **Architecture:**
  - Encapsulated in `OCRService.process_document(file_path, doc_id, title)`.
  - Integration logic: Checks for `fitz` (PyMuPDF) to extract layout and text blocks. If not installed or if processing an image, generates structured block data with bounding box coordinates `[x0, y0, x1, y1]` and confidence scores (e.g., $91.2\% - 96\%$).
  - Results stored in SQLite table `ocr_results` with `archivist_status = 'pending_review'`.
  - API endpoint `POST /api/admin/ocr-review` allows human archivists to inspect, edit recognized text, and mark status as `'archivist_reviewed'`.
  - Ingestion pipeline: When an archivist uploads a document via `POST /api/admin/upload`, `ocr_service` processes the file, writes extracted text into chunks, indexes them into `archive_fts`, and adds vectors to FAISS.

---

### 11. Existing Search Implementation
- **Pipeline Components:**
  1. **Lexical Search (`backend/services/fts_service.py`):** Queries SQLite `archive_fts` using FTS5 `MATCH` with BM25 ranking, phrase extraction, stopword filtering, and prefix matching.
  2. **Dense Vector Search (`backend/services/faiss_service.py`):** Uses FAISS `IndexFlatIP` with normalized 384-dimensional embeddings for cosine similarity retrieval.
  3. **Reciprocal Rank Fusion (`backend/services/rrf.py`):** Merges lexical and dense rankings using:
     $$RRF(d) = \sum_{m \in \{FTS, FAISS\}} \frac{1}{k + r_m(d)} \quad (k=60)$$
  4. **Contextual Re-Ranking (`backend/services/reranker.py`):** Re-scores candidates using query term density, exact phrase matching, and title alignment bonuses.
  5. **Evidence Gate (`backend/services/evidence_gate.py`):** Validates relevance score ($\ge 0.005$), checks physical document and page existence in SQLite, and refuses ungrounded queries.
  6. **Pipeline Orchestrator (`backend/services/retrieval.py`):** Coordinates end-to-end execution and compiles intermediate debug trace metadata.

---

### 12. Existing API Endpoints
All API endpoints are defined in `backend/api/routes.py` with the `/api` prefix:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check, service status, data mode, Gemini configuration |
| `POST` | `/api/ask` | Full end-to-end grounded query synthesis and citation retrieval |
| `POST` | `/api/retrieve` | Intermediate hybrid retrieval debug trace (FTS5 + FAISS + RRF + Rerank) |
| `POST` | `/api/verify` | Evidence gate verification of chunk IDs and documents |
| `GET` | `/api/archive` | Filterable catalogue search (query, type, year, collection, language) |
| `GET` | `/api/archive/{doc_id}` | Detailed document metadata, chunks, and OCR records |
| `GET` | `/api/timeline` | Milestone events (1891–1956) filterable by category |
| `GET` | `/api/knowledge` | Knowledge graph nodes and directed relationship edges |
| `GET` | `/api/media` | Media repository records filterable by type (audio, photo, documentary) |
| `GET` | `/api/stories` | Summary listing of curated digital heritage stories |
| `GET` | `/api/stories/{slug}` | Detailed story chapters and linked archival source documents |
| `GET` | `/api/research` | Current saved citations in user research collection |
| `POST` | `/api/research/save` | Add citation, page, and note to research collection |
| `DELETE` | `/api/research/{item_id}`| Remove citation from research collection |
| `POST` | `/api/feedback` | Record user feedback and rating in audit logs |
| `GET` | `/api/admin/stats` | Document counts, OCR review queue status, and recent audit logs |
| `POST` | `/api/admin/upload` | End-to-end document ingestion (Upload $\rightarrow$ OCR $\rightarrow$ FTS5 $\rightarrow$ FAISS) |
| `POST` | `/api/admin/ocr-review` | Archivist verification and text correction of OCR records |

---

### 13. Where Archival Documents Are Currently Stored
- **Database:** SQLite file at `data/daic_archive.db` storing structured document metadata, chunks, OCR transcriptions, and relational links.
- **Physical Ingestion Uploads:** File storage directory at `data/uploads/`.
- **Pre-seeded Records:** Programmatic definitions in `backend/database/seed_data.py`.
- **Vector Embeddings Index:** Binary FAISS index at `indexes/faiss/archive.index` and metadata mapping at `indexes/faiss/metadata.json`.
- **Static Frontend Media:** Local images at `frontend/assets/`.

---

### 14. Whether SQLite / FTS5 Already Exists
- **Status:** **YES, FULLY OPERATIONAL.**
- Virtual table `archive_fts` is created in `backend/database/db.py` using `fts5(chunk_id UNINDEXED, document_id UNINDEXED, title, content, collection, author, section_title, tokenize = 'unicode61')`.
- Verified and queried via `backend/services/fts_service.py` using BM25 ranking.

---

### 15. Whether FAISS Already Exists
- **Status:** **YES, FULLY OPERATIONAL.**
- Implemented in `backend/services/faiss_service.py` using `faiss.IndexFlatIP(384)`.
- Fallback to NumPy inner-product vector matrix if native FAISS is unavailable in the environment.
- Persistent index binary saved at `indexes/faiss/archive.index` with metadata at `indexes/faiss/metadata.json`.

---

### 16. Existing Gemini Integration
- **Implementation File:** `backend/services/gemini_service.py`.
- **Behavior:**
  - Checks `GEMINI_API_KEY` and `IS_DEMO_MODE`.
  - When live API key is present: Dispatches request to `gemini-1.5-flash:generateContent` with strict system instructions prohibiting fabrication and requiring explicit source citations.
  - When in Demo / Offline mode: Deterministic grounded synthesis extracts exact textual quotes and citations from verified chunks without hallucination.
  - Multilingual synthesis supported for English, Hindi, Marathi, Kannada, and Tamil.

---

### 17. Existing Metadata / Provenance Implementation
- **Schema Columns:**
  - `provenance_type`: Enforces explicit tracking (`REAL ARCHIVAL DATA`, `DEMO DATA`, `USER-UPLOADED DATA`).
  - `verification_status`: Tracks authenticity (`VERIFIED SOURCE`, `DEMO DATA`, `UNVERIFIED (NEW INGESTION)`).
  - `source_institution`: Cites originating institution (e.g., *Dr. Ambedkar Foundation*, *Parliament Library of India*, *Maharashtra State Archives*).
  - `digitization_method`: Preserves technical capture metadata (e.g., *600 DPI Flatbed*, *Microfilm to TIFF*).
  - `ocr_status`: Records verification state (`pending_review`, `archivist_reviewed`, `verified`).
- **Safeguard Enforcement:** `backend/services/evidence_gate.py` rejects any chunk that cannot be cross-referenced to a verified document and valid page number in the SQLite database.

---

## 2. Current Architecture Diagram

```
[ Frontend: Vanilla JS + HTML5 + Tailwind CSS ]
  ├── 10 Dedicated Pages (Index, Ask, Archive, Manuscripts, Timeline, Knowledge, Media, Stories, Visitor, Admin)
  ├── Multilingual Translation Matrix (i18n.js - EN, HI, MR, KN, TA)
  └── Global App Controller (Header, Footer, Research Drawer, Audio Narration, Voice Recognition)
            │
            │ HTTP REST Calls (api.js)
            ▼
[ Backend: FastAPI (main.py + routes.py) ]
  ├── Static File Mounts (/css, /js, /assets, /uploads)
  └── REST API Endpoints (/api/ask, /api/archive, /api/retrieve, /api/admin/*)
            │
            ▼
[ Archival Retrieval Pipeline (retrieval.py) ]
  ├── Step 1: Lexical Search (fts_service.py -> SQLite FTS5 BM25)
  ├── Step 2: Dense Semantic Search (faiss_service.py -> FAISS IndexFlatIP)
  ├── Step 3: Rank Merging (rrf.py -> Reciprocal Rank Fusion, k=60)
  ├── Step 4: Re-Ranking (reranker.py -> Contextual Term Density)
  ├── Step 5: Evidence Gate (evidence_gate.py -> DB Verification & Score Threshold >= 0.005)
  └── Step 6: Grounded Synthesis (gemini_service.py -> Gemini 1.5 Flash / Grounded Fallback)
            │
            ▼
[ Storage Layer ]
  ├── SQLite Database: data/daic_archive.db (13 Relational & FTS Tables)
  ├── FAISS Vector Store: indexes/faiss/archive.index (384-dim embeddings)
  └── Ingestion Store: data/uploads/
```

---

## 3. Current Folder Structure

```
daic-archive/
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git ignore file
├── README.md                        # Documentation and architecture guide
├── requirements.txt                 # Python dependencies
├── backend/
│   ├── __init__.py
│   ├── config.py                    # App configuration, paths, thresholds
│   ├── main.py                      # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                # REST API routes (/api/*)
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py                    # SQLite connection & schema initialization
│   │   └── seed_data.py             # Pre-seeded archival records & entities
│   ├── services/
│   │   ├── __init__.py
│   │   ├── embeddings.py            # Vector embedding generation
│   │   ├── evidence_gate.py         # Evidence verification safeguard
│   │   ├── faiss_service.py         # FAISS IndexFlatIP vector service
│   │   ├── fts_service.py           # SQLite FTS5 lexical BM25 service
│   │   ├── gemini_service.py        # Gemini API & grounded synthesis
│   │   ├── ocr_service.py           # PyMuPDF + PaddleOCR extraction pipeline
│   │   ├── reranker.py              # Contextual re-ranking module
│   │   ├── retrieval.py             # Hybrid search orchestrator
│   │   └── rrf.py                   # Reciprocal Rank Fusion algorithm
│   └── tests/
│       ├── __init__.py
│       └── test_pipeline.py         # Automated unit & integration tests
├── data/
│   ├── daic_archive.db              # SQLite relational & FTS database
│   └── uploads/                     # Ingested PDF and image files
├── frontend/
│   ├── admin.html                   # Archivist ingestion & review dashboard
│   ├── archive.html                 # Faceted archival catalogue browser
│   ├── ask.html                     # AI research assistant & evidence explorer
│   ├── index.html                   # Institutional home page
│   ├── knowledge.html               # Archival knowledge graph network
│   ├── manuscripts.html             # Dual-pane manuscript facsimile & OCR viewer
│   ├── media.html                   # Audio-visual media repository
│   ├── stories.html                 # Curated digital heritage narratives
│   ├── timeline.html                # Chronological milestone explorer
│   ├── visitor.html                 # 1080p touch memorial kiosk interface
│   ├── assets/                      # Curated image stills and story covers
│   ├── css/
│   │   └── styles.css               # Institutional design system styles
│   └── js/
│       ├── admin.js                 # Ingestion & OCR review client logic
│       ├── api.js                   # API client service
│       ├── app.js                   # Global header, footer, drawer, voice & audio
│       ├── archive.js               # Catalogue filtering client logic
│       ├── ask.js                   # Ask page retrieval & audio controls
│       ├── i18n.js                  # Multilingual translation dictionary
│       ├── knowledge.js             # SVG knowledge graph renderer
│       ├── manuscripts.js           # Facsimile zoom & OCR comparison logic
│       ├── media.js                 # Media grid & narration player logic
│       ├── stories.js               # Story reading & citation client logic
│       ├── timeline.js              # Chronological milestone renderer
│       └── visitor.js               # Kiosk touch & localized voice input logic
└── indexes/
    └── faiss/
        ├── archive.index            # FAISS binary vector index file
        └── metadata.json            # Chunk metadata mapping file
```

---

## 4. Existing Features Summary

1. **Hybrid Retrieval System:** Combines exact term BM25 matching (SQLite FTS5) with dense semantic search (FAISS) using Reciprocal Rank Fusion ($k=60$) and contextual re-ranking.
2. **Evidence Gate Safeguard:** Validates every retrieved chunk against the database before synthesis, completely blocking hallucinated claims for out-of-scope inquiries.
3. **Multilingual i18n System:** Client-side dynamic DOM translation supporting English, Hindi, Marathi, Kannada, and Tamil across all navigation elements, search inputs, principles, and footers.
4. **Voice Accessibility:**
   - **Voice Input:** Web Speech Recognition mapped strictly to locale BCP-47 codes (`en-IN`, `hi-IN`, `mr-IN`, `kn-IN`, `ta-IN`) with live status feedback.
   - **Voice Output:** Web Speech Synthesis with Play, Pause, Stop, and Speed controls ($0.75\times$ to $1.5\times$).
5. **Dual-Pane Manuscript Inspector:** Side-by-side comparison of 600 DPI original facsimile with OCR transcript, confidence ratings, and zoom controls.
6. **Archival Catalogue Browser:** Multi-faceted filtering by collection, type, year, language, and search terms.
7. **Interactive Knowledge Graph:** SVG network graph mapping People, Documents, Ideas, Events, and Institutions with contextual dossiers.
8. **Chronological Milestone Timeline:** 1891–1956 milestone explorer with category filtering.
9. **Curated Digital Heritage Stories:** Narrative journeys with chapter citations linked to primary source records.
10. **Touch-friendly Visitor Kiosk:** 1080p touch interface with large typography and simplified voice inquiry.
11. **Archivist Ingestion Portal:** End-to-end upload pipeline (PDF/Image $\rightarrow$ OCR $\rightarrow$ Chunks $\rightarrow$ FTS5 $\rightarrow$ FAISS) and human-in-the-loop OCR review station.
12. **Persistent Research Notebook:** Global slide-out drawer allowing users to save citations with export to Markdown and JSON.

---

## 5. Missing Features & Potential Gaps

1. **Real Physical Dataset Ingestion:** Currently populated with a representative demo dataset (5 primary volumes/speeches). Full authentic physical volumes (BAWS Vols. 1–22, complete CAD proceedings) must be ingested via the existing admin pipeline once raw source files are provided.
2. **User Authentication & Role Management:** The archivist admin portal (`/admin`) is currently open without JWT/OAuth2 session-based login controls.
3. **Automated PDF Bounding Box Coordinates:** Bounding boxes in demo OCR records are simulated templates; live PaddleOCR execution on real multi-page TIFF/PDF files requires optional PaddleOCR and PyMuPDF installations in the target Python environment.
4. **Persistent Annotation Layer:** While users can bookmark citations to their research notebook, custom highlights and inline margin annotations on facsimiles are not yet persisted to SQLite.

---

## 6. Files That Should Be Modified (When Implementing Future Tasks)

- **`backend/database/seed_data.py`** or **`backend/api/routes.py`**: When real archival datasets (BAWS Vols. 1–22 or CAD volumes) are physically imported.
- **`backend/config.py`**: When switching `IS_DEMO_MODE` to `False` or adding production database credentials.
- **`frontend/js/i18n.js`**: When adding additional languages (e.g., Telugu, Bengali, Gujarati) or expanding localized terminology.

---

## 7. Files That Should NOT Be Modified

To preserve platform stability, UI design integrity, and core retrieval guarantees, the following files should **NOT** be modified:
- **`frontend/css/styles.css`**: Contains the institutional design system, color tokens, and layout spacing.
- **`frontend/*.html`** (All 10 HTML files): Page structures, responsive grid hierarchies, and accessibility anchors are finalized and working.
- **`backend/services/evidence_gate.py`**: Contains the core zero-hallucination verification logic required for archival integrity.
- **`backend/services/rrf.py`**: Standard Reciprocal Rank Fusion calculation algorithm.
- **`backend/services/reranker.py`**: Multi-factor re-ranking logic.
- **`backend/services/fts_service.py`**: SQLite FTS5 query builder and stopword sanitization.
- **`backend/services/faiss_service.py`**: Vector indexing and cosine similarity math.
- **`backend/database/db.py`**: Database schema and FTS5 virtual table definition.
- **`backend/tests/test_pipeline.py`**: Core regression test suite ensuring all components function properly.
