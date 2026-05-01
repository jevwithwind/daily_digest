"""Practice routes: compare user recordings against reference paragraphs."""

import logging
import os
import tempfile
from pathlib import Path

import whisper
from fastapi import APIRouter, HTTPException, UploadFile

from app.state import video_cache, whisper_model
from src.comparator import compare_transcripts

router = APIRouter()


@router.post("/videos/{video_id}/paragraphs/{paragraph_index}/compare")
async def compare_paragraph(
    video_id: str,
    paragraph_index: int,
    audio: UploadFile,
):
    """Compare a user's recording against the reference paragraph.

    Accepts audio file (webm/wav/mp3), transcribes with Whisper,
    then compares against reference using LLM.
    """
    if video_id not in video_cache:
        raise HTTPException(status_code=404, detail="Video not found")

    video_data = video_cache[video_id]

    if video_data.get("status") != "ready":
        raise HTTPException(status_code=400, detail="Video is not ready for practice")

    paragraphs = video_data.get("paragraphs", [])
    if paragraph_index < 0 or paragraph_index >= len(paragraphs):
        raise HTTPException(status_code=404, detail="Paragraph not found")

    reference = paragraphs[paragraph_index]["text"]

    # Save uploaded audio to temp file
    suffix = Path(audio.filename).suffix if audio.filename else ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await audio.read()
        tmp.write(content)
        audio_path = tmp.name

    try:
        # Transcribe user's audio
        logging.info(f"Transcribing user audio for paragraph {paragraph_index}...")
        result = whisper_model.transcribe(audio_path, language="ja")
        user_transcript = result["text"].strip()

        if not user_transcript:
            return {
                "paragraph_index": paragraph_index,
                "user_transcript": "",
                "diffs": [],
                "accuracy": 0,
                "missing": [],
                "extras": [],
                "message": "No speech detected in the recording",
            }

        # Compare against reference
        diff_result = compare_transcripts(reference, user_transcript)

        return {
            "paragraph_index": paragraph_index,
            "user_transcript": user_transcript,
            "diffs": diff_result.get("diffs", []),
            "accuracy": diff_result.get("accuracy", 0),
            "missing": diff_result.get("missing", []),
            "extras": diff_result.get("extras", []),
        }

    finally:
        # Clean up temp audio
        if os.path.exists(audio_path):
            os.unlink(audio_path)
