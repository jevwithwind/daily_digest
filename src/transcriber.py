"""Audio transcription using local Whisper model."""

import logging
import sys

import whisper


def transcribe_audio(audio_path: str, language: str = "ja", word_timestamps: bool = False) -> dict:
    """Transcribe audio using local Whisper model.

    Args:
        audio_path: Path to audio file
        language: Language code (default: Japanese)
        word_timestamps: Whether to return word-level timestamps

    Returns:
        dict with keys:
            - text: Full transcript string
            - segments: List of segment dicts with timestamps
            - words: List of word dicts with timestamps (if word_timestamps=True)
    """
    logging.info("Loading Whisper model...")
    model = whisper.load_model("turbo")
    logging.info("Transcribing audio (this may take a few minutes)...")

    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=word_timestamps,
    )

    transcript = result["text"]

    if not transcript.strip():
        logging.error("Transcription returned empty result")
        sys.exit(1)

    logging.info("Audio transcription completed")

    return {
        "text": transcript,
        "segments": result.get("segments", []),
        "words": result.get("words", []) if word_timestamps else [],
    }
