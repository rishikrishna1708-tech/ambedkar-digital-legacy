import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INDEXES_DIR = BASE_DIR / "indexes"
FAISS_DIR = INDEXES_DIR / "faiss"
DB_PATH = DATA_DIR / "daic_archive.db"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Configuration from environment
DATA_MODE = os.getenv("DATA_MODE", "demo").lower()  # "demo" or "real"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
IS_DEMO_MODE = (DATA_MODE == "demo") or not GEMINI_API_KEY

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# RRF Configuration
RRF_K = int(os.getenv("RRF_K", 60))

# Evidence Gate Configuration
MIN_EVIDENCE_SCORE = float(os.getenv("MIN_EVIDENCE_SCORE", 0.60))  # Calibrated for BGE-M3 (1024-dim): supported queries score 0.675-0.886; unrelated queries score <0.60
MIN_SUPPORTING_SOURCES = int(os.getenv("MIN_SUPPORTING_SOURCES", 1))

# Embedding model config
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024  # BAAI/bge-m3 official dense dimension
