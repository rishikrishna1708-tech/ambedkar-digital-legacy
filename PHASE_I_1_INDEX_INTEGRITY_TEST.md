# PHASE I.1 — INDEX INTEGRITY TEST REPORT

**Generated:** 2026-09-24T14:19:00+05:30  
**Status:** ✅ ALL CHECKS PASS

---

## ROOT CAUSE ANALYSIS

The post-repair investigation identified **two separate gaps** in the ingestion pipeline:

| Gap | Cause | Impact |
|-----|-------|--------|
| FTS5 zero ADL-MS entries | `archive_fts` was never populated after ADL-MS chunks were inserted into `chunks` table during Phase I ingestion | BM25 lexical retrieval returned 0 results for real documents |
| FAISS zero ADL-MS vectors | `faiss_service.add_chunks()` was never called for ADL-MS documents after ingestion | Dense vector retrieval returned 0 results for real documents |
| Health endpoint false model name | `/api/health` hardcoded `"BAAI/bge-m3"` unconditionally regardless of `embedding_service.is_real_model` flag | Misleading status when fallback was active |

> [!NOTE]
> The **embedding model (BAAI/bge-m3) IS available** at runtime and loads successfully from local HuggingFace cache (dim=1024). The gap was purely an indexing omission — the chunks existed in SQLite but were never routed through the embedding + index pipeline.

---

## INDEX STATE: PRE-REPAIR vs POST-REPAIR

| Metric | Pre-Repair | Post-Repair | Status |
|--------|-----------|-------------|--------|
| SQLite total chunks | 28 | 28 | — |
| SQLite ADL-MS chunks | 18 | 18 | — |
| FTS5 total entries | 10 | 28 | ✅ REPAIRED |
| FTS5 ADL-MS entries | 0 | 18 | ✅ REPAIRED |
| FAISS metadata count | 10 | 28 | ✅ REPAIRED |
| FAISS index ntotal | 10 | 28 | ✅ REPAIRED |
| FAISS ADL-MS vectors | 0 | 18 | ✅ REPAIRED |
| FAISS dim | 1024 | 1024 | ✅ UNCHANGED |
| Metadata/index sync | 10 == 10 | 28 == 28 | ✅ IN SYNC |
| DEMO DATA preserved | 10 | 10 | ✅ PRESERVED |

---

## EMBEDDING MODEL TRUTHFULNESS

| Field | Before Fix | After Fix |
|-------|-----------|-----------|
| `/api/health` `embedding_model` | Always `"BAAI/bge-m3"` (hardcoded) | `"BAAI/bge-m3"` if real, `"deterministic-fallback (BAAI/bge-m3 unavailable)"` if not |
| `/api/health` `embedding_status` | _(not present)_ | `"real-model-loaded"` or `"fallback-projection"` |
| `/api/health` `embedding_dim` | _(not present)_ | `1024` (actual runtime dimension) |

**Actual runtime state (verified):**
```
embedding_service.is_real_model = True
embedding_service.dim           = 1024
Model loaded:  BAAI/bge-m3 (SentenceTransformer, XLMRoberta backbone, CLS pooling)
```

---

## TEST 5 — REAL DOCUMENT RETRIEVAL (ADL-MS-0004)

**Query:** `"What is my ideal of a society?"`  
**Target document:** `ADL-MS-0004` — *Annihilation of Caste: With a Reply to Mahatma Gandhi (1936)*

### Pipeline trace:

| Stage | Result |
|-------|--------|
| FTS5 candidates | 2 (both ADL-MS-0004) |
| FAISS dense candidates | 15 (ADL-MS-0004-C003 = rank 1, score=0.7154) |
| RRF fused | 15 (ADL-MS-0004-C003 = rank 1, rrf_score=0.0328) |
| Reranked top | ADL-MS-0004-C003 = rerank_score **1.0000** |
| Evidence Gate | ✅ PASSED — "Archival evidence verified successfully." |
| Verified chunks | 2 (ADL-MS-0004-C003, ADL-MS-0004-C004) |

### Retrieved chunk detail:

```
chunk_id:            ADL-MS-0004-C003
document_id:         ADL-MS-0004
page:                2
section_title:       Annihilation of Caste (1936) (Page 2)
verification_status: VERIFIED SOURCE
provenance_type:     USER-UPLOADED DATA
rerank_score:        1.0000
db_verified:         true
```

**Content excerpt from verified OCR:**
> *"SECTION II: THE IDEAL OF AN ASSOCIATED SOCIETY — What is my ideal of a society? If you ask me, my ideal would be a society based on Liberty, Equality, and Fraternity... Democracy is not merely a form of government; it is primarily a mode of associated living, of conjoint communicated experience. It is essentially an attitude of respect and reverence towards fellow men."*

---

## TEST 6 — ASK API PIPELINE (ADL-MS-0004)

**Question:** `"What is my ideal of a society?"`  
**Endpoint:** `POST /api/ask`

| Field | Value |
|-------|-------|
| Evidence Gate | ✅ PASSED |
| Reason | "Archival evidence verified successfully." |
| document_id cited | **ADL-MS-0004** |
| title | Annihilation of Caste: With a Reply to Mahatma Gandhi (1936) |
| page | **2** |
| verification_status | **VERIFIED SOURCE** |
| provenance_type | **USER-UPLOADED DATA** |
| relevance% | **100%** |
| Demo data substitution | ❌ NONE — real document correctly preferred |

> [!IMPORTANT]
> The pipeline does **not** answer from DEMO DATA when verified ADL-MS evidence is available. ADL-MS-0004 ranked #1 across FTS5, FAISS, RRF, and reranker stages, correctly dominating the citation.

---

## TEST 7 — REGRESSION TESTS

### 7a — DEMO DATA Query

**Query:** `"What did Ambedkar say about social democracy?"`

| Stage | Result |
|-------|--------|
| FTS5 top | `CAD_FIN_C01` (CAD_FINAL_SPEECH_1949, page=12, score=3.80) — DEMO DATA |
| FAISS top | `CAD_FIN_C01` (score=0.70) — DEMO DATA |
| Reranked top | `CAD_FIN_C01`, rerank_score=1.0 |
| Evidence Gate | ✅ PASSED |
| Verified chunks | 5 DEMO DATA chunks |

**Result:** DEMO DATA documents remain fully searchable. ✅

### 7b — USER-UPLOADED DATA Query

**Query:** `"What are the fundamental rights of citizens in the constitution?"`

| Stage | Result |
|-------|--------|
| FTS5 top | `ADL-MS-0001-C002` (ADL-MS-0001, page=1, score=3.62) — USER-UPLOADED |
| FAISS top | `ADL-MS-0001-C003` (score=0.65) — USER-UPLOADED |
| Reranked top | `ADL-MS-0001-C002`, rerank_score=1.0 |
| Evidence Gate | ✅ PASSED |
| Verified chunks | 5 (4× ADL-MS-0001 USER-UPLOADED + 1 DEMO DATA) |

**Result:** User-uploaded real archival documents retrievable through complete pipeline. ✅

---

## FINAL SUCCESS CONDITION CHAIN

```
ADL-MS-0004 (Annihilation of Caste — verified OCR)
        ↓
SQLite [chunks: ADL-MS-0004-C001..C004]          ✅ 4 chunks present
        ↓
FTS5 [archive_fts: 18 ADL-MS entries]            ✅ REPAIRED (was 0)
        ↓
FAISS [28 vectors, dim=1024, ADL-MS=18]          ✅ REPAIRED (was 0)
        ↓
RRF [ADL-MS-0004-C003 rank=1, rrf=0.0328]        ✅ Fused correctly
        ↓
Reranker [rerank_score=1.0000]                    ✅ Top-ranked
        ↓
Evidence Gate [PASSED]                            ✅ db_verified=True
        ↓
Ask API [citation: ADL-MS-0004, page=2, 100%]    ✅ Correct archival citation
        ↓
Correct real archival citation: VERIFIED SOURCE / USER-UPLOADED DATA
```

---

## FILES MODIFIED

| File | Change |
|------|--------|
| `backend/api/routes.py` | Fixed `/api/health` to report actual runtime embedding state; added `embedding_status` + `embedding_dim` fields |
| `indexes/faiss/archive.index` | Rebuilt: 28 vectors (10 DEMO + 18 ADL-MS), dim=1024, BGE-M3 embeddings |
| `indexes/faiss/metadata.json` | Now contains 28 entries with complete provenance metadata |
| `data/daic_archive.db` → `archive_fts` | Inserted 18 missing ADL-MS chunk entries into FTS5 virtual table |

## FILES NOT MODIFIED (by design)

| File | Status |
|------|--------|
| `backend/services/retrieval.py` | ✅ Unchanged |
| `backend/services/fts_service.py` | ✅ Unchanged |
| `backend/services/faiss_service.py` | ✅ Unchanged |
| `backend/services/embeddings.py` | ✅ Unchanged |
| `backend/services/evidence_gate.py` | ✅ Unchanged |
| `backend/services/rrf.py` | ✅ Unchanged |
| `backend/services/reranker.py` | ✅ Unchanged |
| All frontend files | ✅ Unchanged |

---

## VERDICT SUMMARY

| Check | Result |
|-------|--------|
| SQLite chunks == FTS5 entries | **28 == 28** ✅ PASS |
| FAISS metadata == FAISS ntotal | **28 == 28** ✅ PASS |
| ADL-MS vectors in FAISS | **18** ✅ PASS |
| ADL-MS entries in FTS5 | **18** ✅ PASS |
| DEMO DATA preserved in FAISS | **10** ✅ PASS |
| Embedding model truthfulness | **BAAI/bge-m3 (real-model-loaded)** ✅ PASS |
| ADL-MS-0004 retrievable (FTS5) | chunk=ADL-MS-0004-C003, score=11.42 ✅ PASS |
| ADL-MS-0004 retrievable (FAISS) | chunk=ADL-MS-0004-C003, score=0.7154 ✅ PASS |
| Evidence Gate for ADL-MS-0004 | PASSED ✅ PASS |
| Ask API cites ADL-MS-0004 | page=2, relevance=100% ✅ PASS |
| Demo regression | PASSED ✅ PASS |
| Real doc regression | PASSED ✅ PASS |

> [!IMPORTANT]
> **PHASE I.1 COMPLETE.** The full verified archival chain is demonstrated with ADL-MS-0004 at 100% relevance score. No retrieval architecture was redesigned. No UI was touched. No BM25/RRF/Evidence Gate logic was changed.
