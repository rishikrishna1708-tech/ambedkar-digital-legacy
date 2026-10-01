# PHASE II — PRE-IMPLEMENTATION AUDIT
**AMBEDKAR DIGITAL LEGACY — AI-Powered Heritage & Research Platform**

**Date of Audit:** 2026-09-24  
**Audited Location:** `c:\Users\USER\Downloads\new\daic-archive`  
**Operational Status:** Active prototype, Phase I Passed (16/16 tests)

---

## 1. Current Embedding Implementation

- **Location:** `backend/services/embeddings.py`
- **Class:** `EmbeddingService` (Singleton)
- **Primary Mechanism:** Tries to dynamically load `SentenceTransformer(EMBEDDING_MODEL_NAME)` where `EMBEDDING_MODEL_NAME = "BAAI/bge-m3"`.
- **Active Runtime State:** Since `sentence_transformers` is not present in the Python environment, the service catches the `ImportError` and activates the fallback method:
  `_semantic_dense_projection(text)`
- **Fallback Characteristics:** Deterministic multi-hash n-gram and subword pooling with SHA-256 and MD5 hashing, positional dampening, character 3-grams, and L2 normalization.
- **Flag `self.is_real_model`:** Currently evaluates to `False`.

---

## 2. Current Embedding Dimension

- **Configured Dimension (`backend/config.py`):** `EMBEDDING_DIM = 384`
- **Active Vector Output Dimension:** `384`
- **Note on BGE-M3 Target Dimension:** The official `BAAI/bge-m3` dense representation produces `1024` dimensions (unlike 384-dimensional MiniLM models or the 384-dimensional fallback projection).

---

## 3. Whether `sentence-transformers` is Installed

- **Status:** **NOT INSTALLED**
- **Runtime Check:** `import sentence_transformers` raises `ModuleNotFoundError: No module named 'sentence_transformers'`.
- **Underlying ML Libraries Status:**
  - `torch`: **NOT INSTALLED** (`No module named 'torch'`)
  - `transformers`: **NOT INSTALLED** (`No module named 'transformers'`)

---

## 4. Whether BGE-M3 is Installed

- **Status:** **NOT INSTALLED / NOT CACHED**
- **Model Target:** `BAAI/bge-m3`
- **Check Details:** Neither the weights nor the supporting execution framework (`torch`, `sentence-transformers`, `transformers`) are currently present in the Python 3.11 site-packages.

---

## 5. Current FAISS Dimension

- **FAISS Binary Index:** `indexes/faiss/archive.index`
- **Type:** `faiss.IndexFlatIP` (Inner Product on L2-normalized vectors)
- **Active Dimension (`index.d`):** `384`

---

## 6. Number of Existing Vectors

- **Vector Count in `indexes/faiss/archive.index` (`index.ntotal`):** `28`
  - 24 vectors from initial verified demo documents (`BAWS_VOL_10_LABOUR`, `BAWS_VOL_05_PROVIDENCE`, `CAD_VOL_07_ART17`, `CAD_FINAL_SPEECH_1949`, `MAHAD_SATYAGRAHA_1927`, `ADL-MS-0001`, `ADL-MS-0002`, `ADL-MS-0003`)
  - 4 vectors from Phase I verified real archival ingestion (`ADL-MS-0004` *Annihilation of Caste*)

---

## 7. Number of Metadata Records

- **Metadata File:** `indexes/faiss/metadata.json`
- **Record Count:** `28`
- **Sample Verified Records in Metadata:**
  - `ADL-MS-0004-C001` (Page 1)
  - `ADL-MS-0004-C002` (Page 1)
  - `ADL-MS-0004-C003` (Page 2)
  - `ADL-MS-0004-C004` (Page 2)

---

## 8. Whether Index and Metadata are Synchronized

- **Status:** **SYNCHRONIZED**
- **FAISS `index.ntotal`:** `28`
- **Metadata Record Count:** `28`
- **Count Difference:** `0` (Exact 1:1 match)
- **Mapping Integrity:** All vector indices `[0..27]` correspond directly to their respective JSON metadata chunk definitions.

---

## 9. Which Files Actually Require Modification

| File | Purpose of Modification | Expected Changes |
|------|------------------------|------------------|
| `requirements.txt` | Dependency declaration | Include `sentence-transformers`, `torch`, etc. if environment allows installation |
| `backend/config.py` | Embedding configuration | Update target dimension to 1024 if BGE-M3 is active; maintain 384 fallback compatibility |
| `backend/services/embeddings.py` | Model loader & device resolution | Robust BGE-M3 loader, device detection (CPU/CUDA), L2 normalization validation, non-faking reporting |
| `backend/services/faiss_service.py` | Index compatibility & migration | Controlled migration: index backup (`archive_384.index.bak`), dimension handling, safe rebuild procedure |
| `backend/services/ocr_service.py` | Production OCR validation | Validate PaddleOCR presence; preserve non-fabricated confidence handling (`NULL` / "Confidence unavailable") |
| `backend/api/routes.py` | Ingestion & indexing pipeline | Maintain dimension sync during online archivist verification |

---

## 10. Architectural Components That MUST REMAIN UNTOUCHED

To adhere strictly to platform preservation rules, the following core modules will **NOT** be replaced or redesigned:
- `backend/services/fts_service.py` (SQLite FTS5 / BM25 lexical engine)
- `backend/services/rrf.py` (Reciprocal Rank Fusion algorithm)
- `backend/services/reranker.py` (Multi-factor evidence scoring & thresholding)
- `backend/services/evidence_gate.py` (Constitutional hallucination prevention gate)
- `backend/database/db.py` (Schema & database integrity)
- `frontend/*` (All UI templates, styling, scripts, and visual designs)
