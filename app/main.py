"""FastAPI application for the Shadow language practice tool."""

import logging
import os
import tempfile
from pathlib import Path

import dotenv
import whisper
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.state import video_cache, whisper_model
from app.routes import videos, practice, audio

dotenv.load_dotenv()

app = FastAPI(title="Shadow", description="Japanese language shadowing practice tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Preload Whisper model on startup to avoid cold-start delay."""
    import app.state as state
    logging.info("Preloading Whisper turbo model...")
    state.whisper_model = whisper.load_model("turbo")
    logging.info("Whisper model loaded")

    # Ensure temp directory for audio processing exists
    state.temp_dir.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    import app.state as state
    return {"status": "ok", "model_loaded": state.whisper_model is not None}


# Mount static files (must be after API routes)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

# Include routers
app.include_router(videos.router, prefix="/api")
app.include_router(practice.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
