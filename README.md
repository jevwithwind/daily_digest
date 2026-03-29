# Daily Digest

A Python CLI tool that fetches the latest Pivot Talk YouTube video, transcribes the audio, summarizes it in Japanese, and emails the result via Resend.

## Features

- Fetches the latest video from the Pivot Talk YouTube channel (@pivot00)
- Downloads audio and transcribes it to Japanese using local Whisper model
- Summarizes the transcript in Japanese using Qwen Coding Plan API
- Sends the video link, summary, and full transcript via email using Resend

## Prerequisites

- Python 3.11+
- FFmpeg (for audio processing)
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

## Setup

1. Install uv (if not already installed):
   ```bash
   pip install uv
   ```

2. Install project dependencies:
   ```bash
   uv sync
   ```
   
   Or if you prefer pip:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment template and configure your API keys:
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` with your actual API keys and email settings.

4. Make sure FFmpeg is installed on your system:
   - On macOS: `brew install ffmpeg`
   - On Ubuntu/Debian: `sudo apt install ffmpeg`
   - On Windows: Download from https://ffmpeg.org/download.html

## Environment Variables

Create a `.env` file with the following variables:
```env
QWEN_CODING_API_KEY=sk-xxx
QWEN_CODING_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
RESEND_API_KEY=re_xxx
EMAIL_FROM=you@yourdomain.com
EMAIL_TO=you@example.com
YT_BROWSER=chrome  # Optional: Browser to use for YouTube cookies (chrome, safari, firefox, etc.)
YT_BROWSER=chrome
```

## Usage

Run the tool directly:
```bash
python main.py
```

Or if installed as a package:
```bash
daily-digest
```

## How It Works

1. **Fetch Video**: Gets the latest video from https://www.youtube.com/@pivot00
2. **Download Audio**: Extracts audio in M4A format using yt-dlp
3. **Transcribe**: Converts audio to text in Japanese using local Whisper model
4. **Summarize**: Creates a Japanese summary of the transcript using Qwen Coding Plan API
5. **Email**: Sends the results via email using Resend

## Error Handling

The tool handles errors gracefully at each stage:
- If video download fails, the process stops with an error message
- If transcription returns empty, the process stops with an error message
- If API calls fail, the process stops with an error message
- Temporary audio files are automatically cleaned up even if errors occur

## Architecture

- Single-file implementation in `main.py`
- Uses OpenAI SDK for Qwen Coding Plan API
- Uses Resend Python SDK for email delivery
- Automatic cleanup of temporary files using context managers
- Environment variables loaded from `.env` file

## Dependencies

- `yt-dlp`: For YouTube video/audio downloading
- `openai-whisper`: For local audio transcription
- `openai`: For interacting with Qwen APIs
- `resend`: For sending emails
- `python-dotenv`: For loading environment variables
- `ffmpeg`: For audio processing (must be installed separately)