"""Audio serving routes for paragraph segments."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.state import video_cache

router = APIRouter()


@router.get("/audio/{video_id}/{paragraph_index}")
async def get_audio_segment(video_id: str, paragraph_index: int):
    """Serve the pre-sliced audio segment for a specific paragraph."""
    if video_id not in video_cache:
        raise HTTPException(status_code=404, detail="Video not found")

    video_data = video_cache[video_id]

    if video_data.get("status") != "ready":
        raise HTTPException(status_code=400, detail="Video audio is not ready")

    segment_dir = video_data.get("segment_dir")
    if not segment_dir:
        raise HTTPException(status_code=404, detail="Audio segments not found")

    segment_path = Path(segment_dir) / f"segment_{paragraph_index:03d}.m4a"

    if not segment_path.exists():
        raise HTTPException(status_code=404, detail="Audio segment not found")

    return FileResponse(
        str(segment_path),
        media_type="audio/m4a",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )
