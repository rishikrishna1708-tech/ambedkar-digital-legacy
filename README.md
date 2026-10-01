# Ambedkar Digital Legacy

Ambedkar Digital Legacy is a digital archive for preserving and exploring documents and historical resources related to Dr. B. R. Ambedkar. It provides search across historical speeches, writings, and constitutional debates, along with tools for document ingestion, OCR transcript verification, and interactive exploration.

## Features

- **Archive and Document Search:** Filter and search through historical speeches, writings, debates, and manuscripts.
- **AI Research Assistant:** Search pipeline combining BM25 keyword search and FAISS vector search with Reciprocal Rank Fusion (RRF) and evidence verification before generating answers.
- **Manuscript and OCR Viewing:** Side-by-side viewer to inspect original document facsimiles alongside OCR text.
- **Historical Timeline:** Interactive chronological milestones from 1891 to 1956 linked to archive records.
- **Knowledge Graph:** Visual network graph showing connections between people, events, concepts, and documents.
- **Media Archive:** Historic audio speeches, Constituent Assembly photographs, and media recordings.
- **Archivist Dashboard:** Ingestion interface for uploading PDFs/images, extracting pages, reviewing OCR text, and publishing to search indexes.
- **Visitor / Kiosk Interface:** Simplified touch-friendly interface suitable for display screens and kiosks.

## Tech Stack

- **Frontend:** HTML, CSS, JavaScript, Tailwind CSS
- **Backend:** Python, FastAPI, Uvicorn, Pydantic
- **Database:** SQLite with FTS5 for full-text search
- **Search & Retrieval:** FAISS, BM25 (FTS5), Reciprocal Rank Fusion (RRF), BAAI/bge-m3 embeddings
- **Document Processing:** PyMuPDF (`fitz`)
- **AI:** Google Gemini API (`gemini-1.5-flash`) with deterministic offline fallback

## Project Structure

```
daic-archive/
├── backend/
│   ├── api/routes.py              # REST API endpoints
│   ├── database/                  # SQLite schema and seed scripts
│   ├── services/                  # Retrieval, FAISS, FTS5, RRF, OCR, Gemini
│   ├── tests/                     # Test suites
│   ├── config.py                  # Application settings
│   └── main.py                    # FastAPI app entry point
├── frontend/
│   ├── assets/                    # Images and SVG assets
│   ├── css/                       # Stylesheets
│   ├── js/                        # Frontend JavaScript logic
│   └── *.html                     # Web pages
├── data/                          # SQLite database and uploaded files
├── indexes/faiss/                 # FAISS vector index and metadata
├── .env.example                   # Environment variable template
├── .gitignore                     # Git ignore rules
└── requirements.txt               # Python dependencies
```

## Running Locally

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Setup Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration (Optional)
Copy `.env.example` to create a local `.env` file:
```powershell
cp .env.example .env
```

If you want to use the live Gemini API instead of the offline fallback, add your API key inside `.env`:
```ini
GEMINI_API_KEY=your_api_key_here
DATA_MODE=real
```

### 4. Initialize Database & Seed Data
```powershell
python -m backend.database.seed_data
```

### 5. Start the Server
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Once started, open your browser and navigate to:
- **Main Portal:** http://127.0.0.1:8000
- **AI Assistant:** http://127.0.0.1:8000/ask
- **Archivist Dashboard:** http://127.0.0.1:8000/admin
- **API Documentation:** http://127.0.0.1:8000/docs

### 6. Running Tests
```powershell
python -m unittest backend/tests/test_pipeline.py
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATA_MODE` | Mode of operation (`demo` or `real`) | `demo` |
| `GEMINI_API_KEY` | Google Gemini API key (optional for offline demo mode) | None |
| `HOST` | Server host address | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `ENVIRONMENT` | Environment name | `development` |
| `RRF_K` | Reciprocal Rank Fusion constant | `60` |
| `MIN_EVIDENCE_SCORE` | Minimum similarity score required by evidence gate | `0.60` |
| `MIN_SUPPORTING_SOURCES` | Minimum number of citations required | `1` |

## Project Status

The project includes the core retrieval pipeline, FastAPI backend, SQLite FTS5 search, FAISS vector index, and frontend interfaces, with an offline demo mode and optional Gemini API integration.
