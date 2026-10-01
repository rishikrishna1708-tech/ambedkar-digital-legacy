import os
import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.config import FAISS_DIR
from backend.services.embeddings import embedding_service

logger = logging.getLogger("daic.faiss")

# Try importing faiss
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.warning("faiss package not found. Using high-performance NumPy vector index fallback.")

INDEX_FILE = FAISS_DIR / "archive.index"
METADATA_FILE = FAISS_DIR / "metadata.json"

class FAISSService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FAISSService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.dim = embedding_service.dim
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self.numpy_vectors = None
        self._init_index()
        self._initialized = True

    def _init_index(self):
        if INDEX_FILE.exists() and METADATA_FILE.exists():
            try:
                self.load_index()
                return
            except Exception as e:
                logger.error(f"Error loading existing index: {e}. Reinitializing empty.")

        self._create_empty_index()

    def _create_empty_index(self):
        self.dim = embedding_service.dim
        if HAS_FAISS:
            self.index = faiss.IndexFlatIP(self.dim)
        else:
            self.index = None
            self.numpy_vectors = np.empty((0, self.dim), dtype=np.float32)
        self.metadata = []

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Takes chunk dicts with keys: chunk_id, document_id, page, title, content, collection, author.
        Deduplicates by chunk_id. Validates that FAISS index and metadata remain in sync after add.
        """
        if not chunks:
            return

        existing_ids = {m["chunk_id"] for m in self.metadata}
        chunks_to_add = [c for c in chunks if c.get("chunk_id") and c["chunk_id"] not in existing_ids]
        if not chunks_to_add:
            logger.info("add_chunks: all chunks already indexed, skipping.")
            return

        # Validate that the chunk exists in SQLite to strictly prevent orphan vectors
        from backend.database.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        valid_chunks = []
        for c in chunks_to_add:
            cur.execute("SELECT id, document_id, page FROM chunks WHERE id = ?", (c["chunk_id"],))
            db_chunk = cur.fetchone()
            if db_chunk:
                valid_chunks.append(c)
            else:
                logger.warning(f"add_chunks: Skipped orphan vector candidate for unpersisted chunk '{c.get('chunk_id')}'.")
        conn.close()

        chunks_to_add = valid_chunks
        if not chunks_to_add:
            return

        texts = [c["content"] for c in chunks_to_add]
        embeddings = embedding_service.embed_batch(texts)

        if HAS_FAISS:
            if self.index is None:
                self.dim = embeddings.shape[1]
                self.index = faiss.IndexFlatIP(self.dim)
            elif self.index.d != embeddings.shape[1]:
                # Dimension mismatch — rebuild all from metadata + new chunks
                logger.warning(
                    f"FAISS dimension mismatch (index.d={self.index.d}, "
                    f"new embeddings dim={embeddings.shape[1]}). Rebuilding index."
                )
                self.dim = embeddings.shape[1]
                self.index = faiss.IndexFlatIP(self.dim)
                if self.metadata:
                    existing_texts = [m.get("content", "") for m in self.metadata]
                    existing_embs = embedding_service.embed_batch(existing_texts)
                    self.index.add(existing_embs)
            self.index.add(embeddings)
        else:
            if self.numpy_vectors is None or self.numpy_vectors.size == 0:
                self.dim = embeddings.shape[1]
                self.numpy_vectors = embeddings
            elif self.numpy_vectors.shape[1] != embeddings.shape[1]:
                logger.warning("NumPy dim mismatch — reinitializing with new embeddings only.")
                self.dim = embeddings.shape[1]
                self.numpy_vectors = embeddings
            else:
                self.numpy_vectors = np.vstack([self.numpy_vectors, embeddings])

        for idx, c in enumerate(chunks_to_add):
            v_id = len(self.metadata)
            self.metadata.append({
                "vector_id": v_id,
                "chunk_id": c["chunk_id"],
                "document_id": c["document_id"],
                "page": c.get("page", 1),
                "page_number": c.get("page", 1),
                "section_title": c.get("section_title", ""),
                "title": c.get("title", ""),
                "collection": c.get("collection", ""),
                "author": c.get("author", ""),
                "content": c.get("content", ""),
                "provenance_type": c.get("provenance_type", "DEMO DATA"),
                "verification_status": c.get("verification_status", "VERIFIED SOURCE")
            })

        self.save_index()
        logger.info(f"Indexed {len(chunks_to_add)} chunks into FAISS/Vector index. Total: {len(self.metadata)}.")

    def remove_chunks_by_ids(self, chunk_ids_to_remove: List[str]):
        """Remove specific chunk IDs from FAISS index and metadata without losing existing vectors."""
        to_remove = set(chunk_ids_to_remove)
        if not any(m["chunk_id"] in to_remove for m in self.metadata):
            return
        new_metadata = [m for m in self.metadata if m["chunk_id"] not in to_remove]
        for idx, m in enumerate(new_metadata):
            m["vector_id"] = idx
        self.metadata = new_metadata
        self._rebuild_from_metadata()

    def search(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        if len(self.metadata) == 0:
            return []

        q_emb = embedding_service.embed_text(query).reshape(1, -1)
        actual_k = min(top_k, len(self.metadata))

        results = []
        if HAS_FAISS and self.index is not None and self.index.ntotal > 0:
            scores, indices = self.index.search(q_emb, actual_k)
            for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= 0 and idx < len(self.metadata):
                    meta = self.metadata[idx].copy()
                    meta["score"] = float(score)
                    meta["dense_rank"] = rank + 1
                    results.append(meta)
        else:
            if self.numpy_vectors is not None and len(self.numpy_vectors) > 0:
                # Dot product since vectors are L2-normalized
                scores = np.dot(self.numpy_vectors, q_emb.T).flatten()
                top_indices = np.argsort(scores)[::-1][:actual_k]
                for rank, idx in enumerate(top_indices):
                    meta = self.metadata[idx].copy()
                    meta["score"] = float(scores[idx])
                    meta["dense_rank"] = rank + 1
                    results.append(meta)

        return results

    def save_index(self):
        """Save both FAISS index and metadata atomically. Guards against sync mismatch."""
        FAISS_DIR.mkdir(parents=True, exist_ok=True)
        expected_vec_count = len(self.metadata)

        if HAS_FAISS and self.index is not None:
            if self.index.ntotal != expected_vec_count:
                logger.error(
                    f"FAISS index/metadata count mismatch before save: "
                    f"index.ntotal={self.index.ntotal}, metadata={expected_vec_count}. "
                    "Skipping save to avoid corruption."
                )
                return
            faiss.write_index(self.index, str(INDEX_FILE))
        elif self.numpy_vectors is not None:
            if len(self.numpy_vectors) != expected_vec_count:
                logger.error(
                    f"NumPy vectors/metadata count mismatch before save: "
                    f"vectors={len(self.numpy_vectors)}, metadata={expected_vec_count}. "
                    "Skipping save to avoid corruption."
                )
                return
            np.save(str(INDEX_FILE) + ".npy", self.numpy_vectors)

        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved vector index ({expected_vec_count} entries) to disk.")

    def load_index(self):
        """Load FAISS index and metadata from disk. Detects and repairs sync mismatch."""
        loaded_vec_count = 0
        if HAS_FAISS and INDEX_FILE.exists():
            self.index = faiss.read_index(str(INDEX_FILE))
            self.dim = self.index.d
            loaded_vec_count = self.index.ntotal
        elif (Path(str(INDEX_FILE) + ".npy")).exists():
            self.numpy_vectors = np.load(str(INDEX_FILE) + ".npy")
            self.dim = self.numpy_vectors.shape[1]
            loaded_vec_count = len(self.numpy_vectors)

        if METADATA_FILE.exists():
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

        meta_count = len(self.metadata)
        if loaded_vec_count != meta_count:
            logger.error(
                f"Loaded index/metadata count mismatch: vectors={loaded_vec_count}, "
                f"metadata={meta_count}. Rebuilding clean index from metadata only."
            )
            # Rebuild the vector index from scratch to match metadata
            self._rebuild_from_metadata()
        else:
            logger.info(f"Loaded vector index with {meta_count} items (in sync).")

    def _rebuild_from_metadata(self):
        """Re-embed all chunks from metadata to rebuild a sync'd FAISS index."""
        logger.info(f"Rebuilding vector index for {len(self.metadata)} metadata entries...")
        if not self.metadata:
            self._create_empty_index()
            return
        texts = [m.get("content", "") for m in self.metadata]
        embeddings = embedding_service.embed_batch(texts)
        if HAS_FAISS:
            self.dim = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(self.dim)
            self.index.add(embeddings)
        else:
            self.dim = embeddings.shape[1]
            self.numpy_vectors = embeddings
        # Persist the now-sync'd index
        self.save_index()
        logger.info(f"Vector index rebuilt and saved ({len(self.metadata)} entries).")

    def rebuild(self):
        self._create_empty_index()
        if INDEX_FILE.exists():
            INDEX_FILE.unlink()
        if (Path(str(INDEX_FILE) + ".npy")).exists():
            Path(str(INDEX_FILE) + ".npy").unlink()
        if METADATA_FILE.exists():
            METADATA_FILE.unlink()

faiss_service = FAISSService()
