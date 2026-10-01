import logging
import hashlib
import math
import numpy as np
from typing import List
from backend.config import EMBEDDING_MODEL_NAME, EMBEDDING_DIM

logger = logging.getLogger("daic.embeddings")

class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.model = None
        self.is_real_model = False
        self.dim = EMBEDDING_DIM
        self._try_load_model()
        self._initialized = True

    def _try_load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
            self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            self.is_real_model = True
            get_dim_fn = getattr(self.model, "get_embedding_dimension", getattr(self.model, "get_sentence_embedding_dimension", None))
            self.dim = get_dim_fn() if get_dim_fn else EMBEDDING_DIM
            logger.info(f"Real model {EMBEDDING_MODEL_NAME} loaded with dimension {self.dim}")
        except Exception as e:
            logger.warning(f"SentenceTransformer not available ({e}). Using robust semantic dense vector projection fallback (dim={self.dim}).")
            self.model = None
            self.is_real_model = False

    def embed_text(self, text: str) -> np.ndarray:
        if self.is_real_model and self.model is not None:
            emb = self.model.encode(text, normalize_embeddings=True)
            return np.array(emb, dtype=np.float32)
        
        return self._semantic_dense_projection(text)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        if self.is_real_model and self.model is not None:
            embs = self.model.encode(texts, normalize_embeddings=True)
            return np.array(embs, dtype=np.float32)
        
        return np.array([self._semantic_dense_projection(t) for t in texts], dtype=np.float32)

    def _semantic_dense_projection(self, text: str) -> np.ndarray:
        """
        Deterministic, high-quality pseudo-semantic projection for offline/demo operation.
        Uses multi-hash n-gram and subword pooling with L2 normalization.
        """
        vec = np.zeros(self.dim, dtype=np.float32)
        if not text:
            return vec

        words = text.lower().strip().split()
        for w_idx, word in enumerate(words):
            # Positional & semantic multi-hash projection
            h1 = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16)
            h2 = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            
            idx1 = h1 % self.dim
            idx2 = h2 % self.dim
            
            weight = 1.0 / (1.0 + math.log1p(w_idx + 1))
            vec[idx1] += np.float32(1.0 + (h1 % 7) * 0.1) * np.float32(weight)
            vec[idx2] += np.float32(0.8 + (h2 % 5) * 0.1) * np.float32(weight)

            # Character 3-grams
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    tri = word[i:i+3]
                    htri = int(hashlib.sha256(tri.encode('utf-8')).hexdigest(), 16)
                    vec[htri % self.dim] += np.float32(0.2)

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec

embedding_service = EmbeddingService()
