#!/usr/bin/env python3
"""
Daily Digest CLI Tool
Fetches the latest Pivot Talk YouTube video, transcribes the audio,
summarizes it in Japanese, and emails the result via Resend.
"""

import logging
import logging.handlers
import os
import sys
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

import dotenv
import yt_dlp
import whisper
from openai import OpenAI
import resend


def setup_logging():
    """Configure logging to write to both stdout and a rotating file."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # Rotating file handler (5 MB per file, 3 backups)
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


LAST_VIDEO_ID_FILE = Path(__file__).parent / ".last_video_id"


def get_last_video_id():
    """Read the last processed video ID from file."""
    if LAST_VIDEO_ID_FILE.exists():
        return LAST_VIDEO_ID_FILE.read_text().strip()
    return None


def save_last_video_id(video_id):
    """Save the processed video ID to file."""
    LAST_VIDEO_ID_FILE.write_text(video_id)


def get_cookie_opts():
    """Get yt-dlp cookie options based on YT_COOKIES_FILE env var."""
    cookies_file = os.getenv('YT_COOKIES_FILE')
    if cookies_file and os.path.isfile(cookies_file):
        return {'cookiefile': cookies_file}
    return {}


def get_latest_video_info():
    """Fetch the latest video from the Pivot Talk channel."""
    logging.info("Fetching latest video from Pivot Talk channel...")
    
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 1,
        'quiet': True,
        'extractor_args': {'youtube': {'skip': ['hls', 'dash']}},
    }
    ydl_opts.update(get_cookie_opts())
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info('https://www.youtube.com/@pivot00/videos', download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                video_id = video.get('id')
                
                if not video_id:
                    logging.error("Could not extract video ID from the latest video")
                    sys.exit(1)
                
                video_info = {
                    'title': video.get('title'),
                    'id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'upload_date': video.get('upload_date')
                }
                
                # Convert upload date to readable format
                if video_info['upload_date']:
                    dt = datetime.strptime(video_info['upload_date'], '%Y%m%d')
                    video_info['formatted_date'] = dt.strftime('%Y-%m-%d')
                else:
                    video_info['formatted_date'] = 'Unknown'
                
                logging.info(f"Found video: {video_info['title']}")
                return video_info
            else:
                logging.error("No videos found in the channel")
                sys.exit(1)
                
    except Exception as e:
        logging.exception(f"Error fetching video info: {str(e)}")
        sys.exit(1)


def download_audio(video_url):
    """Download audio from the video URL using yt-dlp."""
    logging.info("Downloading audio...")
    
    with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_audio:
        temp_path = temp_audio.name
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'postprocessor_args': [
                '-ar', '16000'
            ],
            'prefer_ffmpeg': True,
            'audioquality': '0',
            'extractaudio': True,
            'audioformat': 'm4a',
            'outtmpl': temp_path.replace('.m4a', ''),
            'quiet': True,
        }
        ydl_opts.update(get_cookie_opts())
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Check if the file was created successfully
        if not os.path.exists(temp_path):
            # Try with different extension if the original didn't work
            alt_path = temp_path.replace('.m4a', '.%(ext)s')
            # Find the actual downloaded file
            base_name = temp_path.rsplit('.', 1)[0]
            for ext in ['.m4a', '.mp3', '.m4a.mp3']:  # Common extensions
                alt_path = base_name + ext
                if os.path.exists(alt_path):
                    temp_path = alt_path
                    break
        
        if not os.path.exists(temp_path):
            logging.error("Failed to download audio")
            sys.exit(1)
        
        logging.info(f"Audio downloaded to temporary file: {temp_path}")
        return temp_path
        
    except Exception as e:
        logging.exception(f"Error downloading audio: {str(e)}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        sys.exit(1)


def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using local Whisper model."""
    logging.info("Loading Whisper model...")
    model = whisper.load_model("turbo")
    logging.info("Transcribing audio (this may take a few minutes)...")
    result = model.transcribe(audio_path, language="ja")
    transcript = result["text"]
    
    if not transcript.strip():
        logging.error("Transcription returned empty result")
        sys.exit(1)
    
    logging.info("Audio transcription completed")
    return transcript


def summarize_text(transcript):
    """Summarize the transcript in Japanese using Qwen Coding Plan API."""
    logging.info("Summarizing transcript...")
    
    coding_client = OpenAI(
        api_key=os.getenv('QWEN_CODING_API_KEY'),
        base_url=os.getenv('QWEN_CODING_BASE_URL')
    )
    
    try:
        response = coding_client.chat.completions.create(
            model="qwen3-coder-plus",  # Using an appropriate model
            messages=[
                {
                    "role": "system",
                    "content": "あなたはポッドキャストの要約アシスタントです。以下のトランスクリプトを日本語で簡潔に要約してください。箇条書きは使わず、1つの段落にまとめてください。"
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],
            max_tokens=1024
        )
        
        summary = response.choices[0].message.content
        
        if not summary.strip():
            logging.error("Summary generation returned empty result")
            sys.exit(1)
        
        logging.info("Summary generated")
        return summary
        
    except Exception as e:
        logging.exception(f"Error generating summary: {str(e)}")
        sys.exit(1)


def format_transcript_for_email(transcript):
    """Format the transcript with paragraph breaks every ~500 chars at nearest punctuation."""
    if len(transcript) <= 500:
        return transcript
    
    formatted = []
    start = 0
    
    while start < len(transcript):
        end = start + 500
        
        # If we're near the end of the transcript, take the remainder
        if end >= len(transcript):
            formatted.append(transcript[start:])
            break
        
        # Look for the nearest punctuation mark to break at
        segment = transcript[start:end]
        punct_positions = []
        
        # Find positions of Japanese punctuation marks
        for i, char in enumerate(segment):
            if char in ['。', '！', '？', '.', '!', '?']:
                punct_positions.append(i)
        
        # If we found punctuation, break after the last one
        if punct_positions:
            last_punct = punct_positions[-1]
            actual_end = start + last_punct + 1
            formatted.append(transcript[start:actual_end].strip())
            start = actual_end
        else:
            # If no punctuation found, break at 500 chars
            formatted.append(transcript[start:end].strip())
            start = end
    
    return '\n\n'.join(formatted)


def send_email(video_info, summary, transcript):
    """Send the email with video info, summary, and transcript."""
    logging.info("Sending email...")
    
    resend.api_key = os.getenv('RESEND_API_KEY')
    
    subject = f"[Pivot Talk] {video_info['title']} - {video_info['formatted_date']}"
    
    formatted_transcript = format_transcript_for_email(transcript)
    
    email_body = f"""🔗 動画リンク: {video_info['url']}

📝 要約:
{summary}

────────────────────────────

📖 トランスクリプト:

{formatted_transcript}
"""
    
    try:
        params = {
            "from": os.getenv('EMAIL_FROM'),
            "to": os.getenv('EMAIL_TO'),
            "subject": subject,
            "text": email_body,
        }
        
        email = resend.Emails.send(params)
        logging.info(f"Email sent successfully with ID: {email['id']}")
        
    except Exception as e:
        logging.exception(f"Error sending email: {str(e)}")
        sys.exit(1)


def main():
    """Main function to orchestrate the entire process."""
    setup_logging()
    logging.info("Starting Daily Digest process...")
    
    # Load environment variables
    load_env()
    
    # Step 1: Fetch latest video
    video_info = get_latest_video_info()
    
    # Check if this video was already processed
    last_video_id = get_last_video_id()
    if video_info['id'] == last_video_id:
        logging.info("No new video since last run, skipping")
        sys.exit(0)
    
    # Step 2: Download audio
    audio_path = None
    try:
        audio_path = download_audio(video_info['url'])
        
        # Step 3: Transcribe audio (Whisper handles m4a natively)
        transcript = transcribe_audio(audio_path)
        
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