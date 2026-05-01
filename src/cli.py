"""Legacy CLI entry point — fetch, transcribe, summarize, email digest."""

import argparse
import logging
import logging.handlers
import os
import sys
from pathlib import Path

import dotenv

from src.fetcher import (
    FFMPEG_BIN,
    get_channel_latest_video,
    download_audio,
    get_last_video_id,
    save_last_video_id,
)
from src.transcriber import transcribe_audio
from src.summarizer import summarize_text
from src.mailer import send_email


def setup_logging():
    """Configure logging to write to both stdout and a rotating file."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(
        stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
    )
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "daily_digest.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(file_handler)


def load_env():
    """Load environment variables from .env file."""
    dotenv.load_dotenv()

    required_vars = [
        'QWEN_CODING_API_KEY',
        'QWEN_CODING_BASE_URL',
        'RESEND_API_KEY',
        'EMAIL_FROM',
        'EMAIL_TO'
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logging.error("Please check your .env file against .env.example")
        sys.exit(1)


def main():
    """Main function to orchestrate the entire email digest process."""
    parser = argparse.ArgumentParser(description="Daily Digest — fetch, transcribe, summarize, email")
    parser.add_argument("--force", action="store_true", help="Skip dedup check and reprocess the latest video")
    args = parser.parse_args()

    if FFMPEG_BIN not in os.environ.get('PATH', ''):
        os.environ['PATH'] = FFMPEG_BIN + os.pathsep + os.environ.get('PATH', '')

    setup_logging()
    logging.info("Starting Daily Digest process...")

    load_env()

    # Step 1: Fetch latest video from Pivot Talk channel
    video_info = get_channel_latest_video('https://www.youtube.com/@pivot00/videos')

    # Check if this video was already processed
    if not args.force:
        last_video_id = get_last_video_id()
        if video_info['id'] == last_video_id:
            logging.info("No new video since last run, skipping")
            sys.exit(0)

    # Step 2: Download audio
    audio_path = None
    try:
        audio_path = download_audio(video_info['url'])

        # Step 3: Transcribe audio
        transcript_result = transcribe_audio(audio_path)
        transcript = transcript_result["text"]

        # Step 4: Summarize transcript
        summary = summarize_text(transcript)

        # Step 5: Send email
        send_email(video_info, summary, transcript)

        # Only save the video ID after successful email send
        save_last_video_id(video_info['id'])

        logging.info("Process completed successfully!")

    finally:
        # Clean up temporary audio file
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)


if __name__ == "__main__":
    main()
