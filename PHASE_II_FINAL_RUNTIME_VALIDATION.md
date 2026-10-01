# PHASE II — FINAL RUNTIME VALIDATION REPORT
## Dr. B. R. Ambedkar Digital Archive & Intelligence Corpus (DAIC)

**Generated:** 2026-09-25  
**Report Class:** Phase II.1 — Runtime Consistency & OCR Validation  
**Status:** ✅ ALL INVARIANTS SATISFIED — PHASE II COMPLETE

---

## 1. INDEX CONSISTENCY INVARIANT

The following invariant is **SATISFIED**:

```
SQLite verified chunks == FTS5 entries == FAISS metadata == FAISS ntotal
```

| Store                 | Count | Status |
|-----------------------|-------|--------|
| SQLite verified chunks | **28** | ✅ |
| FTS5 (archive_fts)    | **28** | ✅ |
| FAISS metadata        | **28** | ✅ |
| FAISS ntotal          | **28** | ✅ |

**FAISS index dimension:** 1024  
**Embedding model:** `BAAI/bge-m3` (sentence-transformers)  
**FAISS index type:** IndexFlatIP (Inner Product — cosine similarity)

---

## 2. DATABASE STATISTICS

### Documents

| Verification Status   | Count |
|----------------------|-------|
| DEMO DATA            | 5     |
| VERIFIED SOURCE      | 4     |
| **Total**            | **9** |

### Chunks

| Provenance Type      | Count |
|----------------------|-------|
| DEMO DATA            | 10    |
| USER-UPLOADED DATA   | 18    |
| REAL ARCHIVAL DATA   | 0     |
| **Total**            | **28** |

### Audit Trail Tables

| Table          | Row Count | Notes |
|----------------|-----------|-------|
| `ingest_jobs`  | 0         | ADL-MS-0001..0004 were ingested prior to the audit trail middleware wiring in Phase II |
| `ocr_results`  | 7         | OCR result records from all reviewed ingestion sessions |
| `ocr_revisions`| 0         | No archivist text corrections have been applied post-review |

> **Note:** The `ingest_jobs` count is 0 because the 4 ADL-MS documents were uploaded and verified
> during Phase I, before the `ingest_jobs` table middleware was active. New documents uploaded via the
> current admin dashboard will create `ingest_jobs` rows correctly. The `ocr_revisions` table
> records will populate when an archivist uses the Revision Station to edit OCR text.

---

## 3. REAL ARCHIVAL DOCUMENTS (ADL-MS-0001 through ADL-MS-0004)

| Document ID   | Title                            | Pages | SQLite Chunks | FTS5 Chunks | FAISS Vectors | Verification      | Provenance          |
|---------------|----------------------------------|-------|---------------|-------------|---------------|-------------------|---------------------|
| ADL-MS-0001   | States and Minorities (1947)     | 1     | 6             | 6           | 6             | VERIFIED SOURCE   | USER-UPLOADED DATA  |
| ADL-MS-0002   | Round Table Conference (1930)    | 2     | 4             | 4           | 4             | VERIFIED SOURCE   | USER-UPLOADED DATA  |
| ADL-MS-0003   | Southborough Committee (1919)    | 2     | 4             | 4           | 4             | VERIFIED SOURCE   | USER-UPLOADED DATA  |
| ADL-MS-0004   | Annihilation of Caste (1936)     | 2     | 4             | 4           | 4             | VERIFIED SOURCE   | USER-UPLOADED DATA  |

**Per-document invariant:** For each ADL-MS document: `SQLite chunks == FTS5 chunks == FAISS vectors` ✅

---

## 4. FAISS VECTOR DISTRIBUTION (ALL INDEXED DOCUMENTS)

| Document ID               | FAISS Vectors |
|---------------------------|---------------|
| ADL-MS-0001               | 6             |
| ADL-MS-0002               | 4             |
| ADL-MS-0003               | 4             |
| ADL-MS-0004               | 4             |
| BAWS_VOL_05_PROVIDENCE    | 2             |
| BAWS_VOL_10_LABOUR        | 3             |
| CAD_FINAL_SPEECH_1949     | 2             |
| CAD_VOL_07_ART17          | 2             |
| MAHAD_SATYAGRAHA_1927     | 1             |
| **Total**                 | **28**        |

---

## 5. OCR ENGINE STATUS

| Property               | Value                            |
|------------------------|----------------------------------|
| OCR Engine Requested   | PaddleOCR                        |
| PaddleOCR Installed    | ❌ NO — `import paddleocr` raises `ModuleNotFoundError` |
| Reported Engine        | `OCR_ENGINE_UNAVAILABLE`         |
| Embedded Text Fallback | ✅ PyMuPDF (for PDFs with embedded text) |
| Confidence Fabrication | ❌ NEVER — confidence is `null` when PaddleOCR is absent |
| OCR Result Records     | 7 (from all completed review sessions) |

**OCR behavior by file type:**

| Input Type           | Engine Used                          | Confidence Reported |
|----------------------|--------------------------------------|---------------------|
| PDF with embedded text | PyMuPDF (Embedded Text)            | `null` (N/A for embedded) |
| PDF scanned pages    | OCR_ENGINE_UNAVAILABLE               | `null` |
| PNG / JPG / TIFF     | OCR_ENGINE_UNAVAILABLE               | `null` |

---

## 6. RETRIEVAL VALIDATION — 8/8 QUERIES PASS

All 8 queries were run through the full pipeline: FTS5 → FAISS → RRF → Reranker → Evidence Gate.

### Query Results

| Query                                                  | Mode    | Document Hit | Gate   | Verification      |
|--------------------------------------------------------|---------|--------------|--------|-------------------|
| "States and Minorities 1947"                           | Exact   | ADL-MS-0001  | PASS   | VERIFIED SOURCE   |
| "Ambedkar federal constitution minorities protection"  | Semantic| ADL-MS-0001  | PASS   | VERIFIED SOURCE   |
| "Round Table Conference 1930"                          | Exact   | ADL-MS-0002  | PASS   | VERIFIED SOURCE   |
| "franchise depressed classes representation London"    | Semantic| ADL-MS-0002  | PASS   | VERIFIED SOURCE   |
| "Southborough Committee 1919"                          | Exact   | ADL-MS-0003  | PASS   | VERIFIED SOURCE   |
| "separate electorates untouchables Ambedkar 1919"      | Semantic| ADL-MS-0003  | PASS   | VERIFIED SOURCE   |
| "Annihilation of Caste 1936"                           | Exact   | ADL-MS-0004  | PASS   | VERIFIED SOURCE   |
| "caste system Hindu social order reform"               | Semantic| ADL-MS-0004  | PASS   | VERIFIED SOURCE   |

**Result: 8 / 8 MATCH — Evidence Gate ACCEPTED — Verification: VERIFIED SOURCE**

---

## 7. METADATA INJECTION AUDIT

| Field              | Before Phase II      | After Phase II Fix   |
|--------------------|----------------------|----------------------|
| `author` default   | `"Dr. B. R. Ambedkar"` auto-filled | `NOT PROVIDED` (only if archivist supplies) |
| `source_institution` default | `"Institutional Digital Preservation Archive"` | `NOT PROVIDED` (only if archivist supplies) |
| Form pre-fill (admin.html) | All fields pre-filled | All fields blank — archivist must type |

---

## 8. CHUNK PROVENANCE BUG — RESOLVED

**Bug:** When `review_ocr_result` approved a chunk and wrote it to the `chunks` table,
it was setting `provenance_type = 'VERIFIED SOURCE'` — which is not a valid provenance category.

**Fix applied:** `provenance_type` now inherits from the parent document's `provenance_type`
(e.g., `USER-UPLOADED DATA`). `VERIFIED SOURCE` is only a `documents.verification_status` value.

**Impact:** All 18 USER-UPLOADED DATA chunks now carry the correct provenance type.

---

## 9. SEED_DATABASE FTS5 WIPE BUG — RESOLVED

**Bug:** `seed_database()` (called in `setUpClass` of every `pytest` run) contained:
```sql
DELETE FROM archive_fts;
```
Then only re-indexed demo data. This meant every test run wiped the 18 ADL-MS verified chunks
from FTS5 and their vectors from FAISS, breaking the index invariant after tests.

**Fix applied:** After inserting demo data, `seed_database()` now queries all verified
non-demo chunks from SQLite and re-indexes them into `archive_fts` and FAISS.

---

## 10. TEST SUITE — 9/9 PASSED

Run: `python -m pytest backend/tests/test_pipeline.py -v`

| Test                                        | Result | What It Validates |
|---------------------------------------------|--------|-------------------|
| `test_index_invariant`                      | ✅ PASS | SQLite=FTS5=FAISS meta=FAISS ntotal=28 |
| `test_database_and_fts5`                    | ✅ PASS | FTS5 BM25 search + chunk in SQLite |
| `test_faiss_dense_search`                   | ✅ PASS | FAISS returns dense matches; all chunks in SQLite |
| `test_rrf_fusion`                           | ✅ PASS | RRF fuses lexical+dense; rrf_score + matched_modes present |
| `test_reranker`                             | ✅ PASS | Reranker assigns rerank_score + relevance_label; page mapping correct |
| `test_evidence_gate_acceptance`             | ✅ PASS | Mahad Satyagraha query passes Evidence Gate; document mapping correct |
| `test_evidence_gate_rejection`              | ✅ PASS | Off-topic query rejected with 0 evidence chunks |
| `test_real_archival_document_retrieval`     | ✅ PASS | ADL-MS-0001..0004: SQLite chunks = FTS5 = FAISS for each document |
| `test_end_to_end_ask_pipeline`              | ✅ PASS | Labour rights query returns verified, grounded, BAWS-sourced answer |

**Total: 9 passed, 0 failed, 0 warnings — 59.79s**

---

## 11. STOP CONDITION — SATISFIED

The Phase II.1 stop condition has been met:

- ✅ `SQLite verified chunks (28) == FTS5 entries (28) == FAISS metadata (28) == FAISS ntotal (28)`
- ✅ ADL-MS-0001 through ADL-MS-0004 are retrievable from all three indexes
- ✅ All 8 retrieval queries (exact + semantic for each ADL-MS document) return Evidence Gate PASS
- ✅ OCR engine honestly reports `OCR_ENGINE_UNAVAILABLE` — no fabricated confidence
- ✅ No auto-injection of author or institution defaults
- ✅ Chunk provenance inherits from parent document
- ✅ `seed_database()` preserves verified chunks across test runs
- ✅ Test suite: 9/9 PASS, no pytest warnings

**PHASE II.1 IS COMPLETE. Phase III may begin.**

---

*DAIC Archive — Phase II Runtime Validation Report*  
*Validator: Automated pipeline — see `validate_retrieval.py` and `backend/services/index_validator.py`*
