#!/usr/bin/env python3
"""
Daily Digest CLI Tool
Fetches the latest Pivot Talk YouTube video, transcribes the audio,
summarizes it in Japanese, and emails the result via Resend.
"""

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
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file against .env.example")
        sys.exit(1)


def get_latest_video_info():
    """Fetch the latest video from the Pivot Talk channel."""
    print("Fetching latest video from Pivot Talk channel...")
    
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 1,
        'quiet': True,
        'extractor_args': {'youtube': {'skip': ['hls', 'dash']}}
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info('https://www.youtube.com/@pivot00/videos', download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                video_id = video.get('id')
                
                if not video_id:
                    print("Error: Could not extract video ID from the latest video")
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
                
                print(f"Found video: {video_info['title']}")
                return video_info
            else:
                print("Error: No videos found in the channel")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error fetching video info: {str(e)}")
        sys.exit(1)


def download_audio(video_url):
    """Download audio from the video URL using yt-dlp."""
    print("Downloading audio...")
    
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
            print("Error: Failed to download audio")
            sys.exit(1)
        
        print(f"Audio downloaded to temporary file: {temp_path}")
        return temp_path
        
    except Exception as e:
        print(f"Error downloading audio: {str(e)}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        sys.exit(1)


def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using local Whisper model."""
    print("Loading Whisper model...")
    model = whisper.load_model("turbo")
    print("Transcribing audio (this may take a few minutes)...")
    result = model.transcribe(audio_path, language="ja")
    transcript = result["text"]
    
    if not transcript.strip():
        print("Error: Transcription returned empty result")
        sys.exit(1)
    
    print("Audio transcription completed")
    return transcript


def summarize_text(transcript):
    """Summarize the transcript in Japanese using Qwen Coding Plan API."""
    print("Summarizing transcript...")
    
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
                    "content": "あなたはポッドキャストの要約アシスタントです。以下のトランスクリプトを日本語で簡潔に要約してください。箇条書きで主要なポイントを5〜8個にまとめてください。"
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
            print("Error: Summary generation returned empty result")
            sys.exit(1)
        
        print("Summary generated")
        return summary
        
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        sys.exit(1)


def send_email(video_info, summary, transcript):
    """Send the email with video info, summary, and transcript."""
    print("Sending email...")
    
    resend.api_key = os.getenv('RESEND_API_KEY')
    
    subject = f"[Pivot Talk] {video_info['title']} - {video_info['formatted_date']}"
    
    email_body = f"""{video_info['url']}

【要約】
{summary}

--------------------------------------------------
【全文文字起こし】
{transcript}
"""
    
    try:
        params = {
            "from": os.getenv('EMAIL_FROM'),
            "to": os.getenv('EMAIL_TO'),
            "subject": subject,
            "text": email_body,
        }
        
        email = resend.Emails.send(params)
        print(f"Email sent successfully with ID: {email['id']}")
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        sys.exit(1)


def main():
    """Main function to orchestrate the entire process."""
    print("Starting Daily Digest process...")
    
    # Load environment variables
    load_env()
    
    # Step 1: Fetch latest video
    video_info = get_latest_video_info()
    
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
        
        print("Process completed successfully!")
        
    finally:
        # Clean up temporary audio file
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)


if __name__ == "__main__":
    main()