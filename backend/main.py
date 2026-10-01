import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.config import BASE_DIR, DATA_DIR, HOST, PORT, ENVIRONMENT, IS_DEMO_MODE, DATA_MODE
from backend.api.routes import api_router
from backend.database.db import init_db

app = FastAPI(
    title="Ambedkar Digital Legacy: AI-Powered Heritage & Research Platform",
    description="Digital Heritage Archive • Ambedkar International Centre",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = DATA_DIR / "uploads"

# Ensure dirs exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "css").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "js").mkdir(parents=True, exist_ok=True)
(FRONTEND_DIR / "assets").mkdir(parents=True, exist_ok=True)

# Mount Static Directories
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include API Router
app.include_router(api_router)

# Page Serving Routes
@app.get("/", response_class=FileResponse)
def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/ask", response_class=FileResponse)
def serve_ask():
    return FileResponse(str(FRONTEND_DIR / "ask.html"))

@app.get("/archive.view", response_class=FileResponse)
@app.get("/archive-view", response_class=FileResponse)
def serve_archive():
    return FileResponse(str(FRONTEND_DIR / "archive.html"))

@app.get("/manuscripts", response_class=FileResponse)
def serve_manuscripts():
    return FileResponse(str(FRONTEND_DIR / "manuscripts.html"))

@app.get("/timeline.view", response_class=FileResponse)
@app.get("/timeline-view", response_class=FileResponse)
def serve_timeline():
    return FileResponse(str(FRONTEND_DIR / "timeline.html"))

@app.get("/knowledge.view", response_class=FileResponse)
@app.get("/knowledge-view", response_class=FileResponse)
def serve_knowledge():
    return FileResponse(str(FRONTEND_DIR / "knowledge.html"))

@app.get("/media.view", response_class=FileResponse)
@app.get("/media-view", response_class=FileResponse)
def serve_media():
    return FileResponse(str(FRONTEND_DIR / "media.html"))

@app.get("/stories.view", response_class=FileResponse)
@app.get("/stories-view", response_class=FileResponse)
def serve_stories():
    return FileResponse(str(FRONTEND_DIR / "stories.html"))

@app.get("/visitor", response_class=FileResponse)
def serve_visitor():
    return FileResponse(str(FRONTEND_DIR / "visitor.html"))

@app.get("/admin", response_class=FileResponse)
def serve_admin():
    return FileResponse(str(FRONTEND_DIR / "admin.html"))

@app.on_event("startup")
def on_startup():
    init_db()
    print("==================================================")
    print("  DAIC ARCHIVE: Digital Heritage Archive Platform")
    print(f"  Operational Mode : {'DEMO MODE (Offline Verified)' if IS_DEMO_MODE else 'LIVE MODE (Gemini API Active)'}")
    print(f"  Data Mode        : {DATA_MODE.upper()}")
    print("  Principle        : PRESERVE -> DISCOVER -> UNDERSTAND -> VERIFY -> LEARN")
    print("==================================================")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
