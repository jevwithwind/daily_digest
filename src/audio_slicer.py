"""Audio segment extraction using ffmpeg based on word-level timestamps."""

import logging
import os
import subprocess
import sys
from pathlib import Path


def slice_audio_by_paragraphs(
    audio_path: str,
    paragraphs: list[str],
    words: list[dict],
    output_dir: str,
    padding_ms: float = 200.0,
) -> list[str]:
    """Extract audio segments for each paragraph using word timestamps.

    Args:
        audio_path: Path to the full source audio file
        paragraphs: List of paragraph texts
        words: List of word dicts from Whisper with 'start', 'end', 'word' keys
        output_dir: Directory to save sliced segments
        padding_ms: Milliseconds of padding to add before/after each segment

    Returns:
        List of paths to sliced audio segment files
    """
    logging.info(f"Slicing audio into {len(paragraphs)} segments...")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    segments = []

    for i, paragraph in enumerate(paragraphs):
        # Find the word range that matches this paragraph
        start_time, end_time = _find_paragraph_timestamps(paragraph, words, i, paragraphs)

        if start_time is None or end_time is None:
            logging.warning(f"Could not find timestamps for paragraph {i+1}, skipping audio slice")
            segments.append(None)
            continue

        # Apply padding
        padding_s = padding_ms / 1000.0
        start_time = max(0, start_time - padding_s)
        end_time = end_time + padding_s

        duration = end_time - start_time

        output_path = str(Path(output_dir) / f"segment_{i:03d}.m4a")

        try:
            _run_ffmpeg_slice(audio_path, start_time, duration, output_path)
            segments.append(output_path)
            logging.debug(f"Sliced paragraph {i+1}: {start_time:.1f}s - {end_time:.1f}s")
        except Exception as e:
            logging.exception(f"Error slicing paragraph {i+1}: {str(e)}")
            segments.append(None)

    logging.info(f"Audio slicing complete: {sum(1 for s in segments if s)}/{len(paragraphs)} segments")
    return segments


def _find_paragraph_timestamps(
    paragraph: str,
    words: list[dict],
    paragraph_index: int,
    all_paragraphs: list[str],
) -> tuple[float | None, float | None]:
    """Find the start and end timestamps for a paragraph by matching text.

    Strategy: find the first word of the paragraph in the word list,
    and the last word, then use their timestamps.
    """
    if not words:
        return None, None

    # Clean paragraph text for matching
    clean_para = paragraph.strip().replace('\n', ' ')

    # Find first meaningful word from paragraph in the word list
    first_word = _extract_first_word(clean_para)
    last_word = _extract_last_word(clean_para)

    if not first_word or not last_word:
        return None, None

    # Search for first word in word list
    start_time = None
    end_time = None

    for w in words:
        w_text = w.get('word', '').strip()
        if not w_text:
            continue

        # Check if this word matches the start of our paragraph
        if _words_match(w_text, first_word) and start_time is None:
            start_time = w.get('start')

        # Check if this word matches the end of our paragraph
        if _words_match(w_text, last_word):
            end_time = w.get('end')

    # If we couldn't find exact matches, fall back to approximate matching
    if start_time is None or end_time is None:
        start_time, end_time = _fallback_timestamp_search(
            clean_para, words, paragraph_index, all_paragraphs
        )

    return start_time, end_time


def _extract_first_word(text: str) -> str:
    """Extract the first meaningful word from Japanese text."""
    # Skip leading punctuation
    for char in text:
        if char not in [' ', '　', '「', '」', '『', '』', '（', '）', '、', '。']:
            # Return first 1-3 characters as a "word" unit for Japanese
            idx = text.index(char)
            return text[idx:idx+3].strip()
    return ''


def _extract_last_word(text: str) -> str:
    """Extract the last meaningful word from Japanese text."""
    # Skip trailing punctuation
    for char in reversed(text):
        if char not in [' ', '　', '「', '」', '『', '』', '（', '）', '、', '。', '！', '？', '!', '?']:
            idx = text.rindex(char)
            return text[max(0, idx-2):idx+1].strip()
    return ''


def _words_match(word1: str, word2: str) -> bool:
    """Check if two Japanese word fragments match (allowing partial matches)."""
    w1 = word1.strip().lower()
    w2 = word2.strip().lower()

    if w1 == w2:
        return True

    # Partial match: one contains the other
    if len(w1) >= 2 and len(w2) >= 2:
        if w1 in w2 or w2 in w1:
            return True

    return False


def _fallback_timestamp_search(
    paragraph: str,
    words: list[dict],
    paragraph_index: int,
    all_paragraphs: list[str],
) -> tuple[float | None, float | None]:
    """Fallback: estimate timestamps based on paragraph position in full text."""
    # Reconstruct full transcript from words
    full_text = ''.join(w.get('word', '') for w in words)

    # Find paragraph position in full text
    clean_para = paragraph.strip().replace('\n', ' ')
    pos = full_text.find(clean_para[:20])  # Match first 20 chars

    if pos == -1:
        # Try shorter match
        pos = full_text.find(clean_para[:10])

    if pos == -1:
        return None, None

    # Find the word at this position
    char_count = 0
    start_time = None
    end_time = None

    for w in words:
        w_text = w.get('word', '')
        char_count += len(w_text)

        if char_count >= pos and start_time is None:
            start_time = w.get('start')

        if char_count >= pos + len(clean_para):
            end_time = w.get('end')
            break

    return start_time, end_time


def _run_ffmpeg_slice(audio_path: str, start: float, duration: float, output_path: str):
    """Run ffmpeg to extract an audio slice."""
    from src.fetcher import FFMPEG_BIN

    ffmpeg_path = os.path.join(FFMPEG_BIN, 'ffmpeg.exe')

    cmd = [
        ffmpeg_path,
        '-y',
        '-ss', str(start),
        '-t', str(duration),
        '-i', audio_path,
        '-c', 'copy',
        '-avoid_negative_ts', 'make_zero',
        output_path,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"ffmpeg produced empty output: {output_path}")
