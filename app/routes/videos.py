"""Video loading and management routes."""

import logging
import os
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.state import video_cache, temp_dir
from src.fetcher import get_video_info, download_audio, FFMPEG_BIN
from src.transcriber import transcribe_audio
from src.chunker import chunk_transcript
from src.audio_slicer import slice_audio_by_paragraphs

router = APIRouter()


class LoadRequest(BaseModel):
    url: str


class VideoStatus(BaseModel):
    video_id: str
    title: str
    status: str  # "processing", "ready", "error"
    progress: Optional[str] = None
    paragraph_count: Optional[int] = None
    error: Optional[str] = None


@router.post("/load")
async def load_video(req: LoadRequest):
    """Start processing a YouTube video: download, transcribe, chunk, slice audio."""
    url = req.url.strip()

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Extract video ID from URL for cache key
    video_id = _extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Could not extract video ID from URL")

    if video_id in video_cache and video_cache[video_id].get("status") == "ready":
        return {
            "video_id": video_id,
            "title": video_cache[video_id]["title"],
            "status": "ready",
            "paragraph_count": video_cache[video_id]["paragraph_count"],
        }

    # Start processing in background thread
    video_cache[video_id] = {
        "video_id": video_id,
        "title": "Loading...",
        "status": "processing",
        "progress": "Fetching video info...",
        "url": url,
    }

    thread = threading.Thread(target=_process_video, args=(video_id, url), daemon=True)
    thread.start()

    return {
        "video_id": video_id,
        "title": "Processing...",
        "status": "processing",
    }


@router.get("/videos/{video_id}")
async def get_video(video_id: str):
    """Get video status and paragraph data."""
    if video_id not in video_cache:
        raise HTTPException(status_code=404, detail="Video not found")

    data = video_cache[video_id]

    if data["status"] == "processing":
        return {
            "video_id": video_id,
            "title": data.get("title", "Processing..."),
            "status": "processing",
            "progress": data.get("progress", "Working..."),
        }

    if data["status"] == "error":
        return {
            "video_id": video_id,
            "title": data.get("title", ""),
            "status": "error",
            "error": data.get("error", "Unknown error"),
        }

    # Ready — return paragraph data
    return {
        "video_id": video_id,
        "title": data["title"],
        "status": "ready",
        "paragraph_count": data["paragraph_count"],
        "paragraphs": data["paragraphs"],
    }


@router.get("/videos/{video_id}/status")
async def get_video_status(video_id: str):
    """Get just the processing status of a video."""
    if video_id not in video_cache:
        raise HTTPException(status_code=404, detail="Video not found")

    data = video_cache[video_id]
    return {
        "video_id": video_id,
        "status": data["status"],
        "progress": data.get("progress"),
        "error": data.get("error"),
    }


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    import re

    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def _process_video(video_id: str, url: str):
    """Process a video in a background thread."""
    try:
        cache = video_cache[video_id]
        cache["progress"] = "Fetching video info..."

        # Step 1: Get video info
        video_info = get_video_info(url)
        cache["title"] = video_info["title"]
        cache["progress"] = "Downloading audio..."

        # Ensure ffmpeg is in PATH
        if FFMPEG_BIN not in os.environ.get('PATH', ''):
            os.environ['PATH'] = FFMPEG_BIN + os.pathsep + os.environ.get('PATH', '')

        # Step 2: Download audio
        audio_dir = str(temp_dir / video_id)
        audio_path = download_audio(url, output_dir=audio_dir)
        cache["progress"] = "Transcribing audio..."

        # Step 3: Transcribe with word timestamps
        result = transcribe_audio(audio_path, word_timestamps=True)
        full_transcript = result["text"]
        words = result["words"]
        cache["progress"] = "Chunking transcript..."

        # Step 4: Chunk into paragraphs
        paragraphs = chunk_transcript(full_transcript)
        cache["progress"] = "Slicing audio segments..."

        # Step 5: Slice audio per paragraph
        segment_dir = str(Path(audio_dir) / "segments")
        segments = slice_audio_by_paragraphs(audio_path, paragraphs, words, segment_dir)

        # Store results
        cache["paragraphs"] = []
        for i, para in enumerate(paragraphs):
            cache["paragraphs"].append({
                "index": i,
                "text": para,
                "audio_available": segments[i] is not None,
            })

        cache["paragraph_count"] = len(paragraphs)
        cache["status"] = "ready"
        cache["audio_dir"] = audio_dir
        cache["segment_dir"] = segment_dir
        cache["audio_path"] = audio_path

        logging.info(f"Video {video_id} processed: {len(paragraphs)} paragraphs")

    except Exception as e:
        logging.exception(f"Error processing video {video_id}")
        cache = video_cache.get(video_id, {})
        cache["status"] = "error"
        cache["error"] = str(e)
        video_cache[video_id] = cache
