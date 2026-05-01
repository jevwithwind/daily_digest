"""Shared application state to avoid circular imports."""

import tempfile
from pathlib import Path

video_cache: dict = {}
whisper_model = None
temp_dir = Path(tempfile.gettempdir()) / "shadow_audio"
