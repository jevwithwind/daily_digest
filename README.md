# Daily Digest

A Python CLI tool that fetches the latest Pivot Talk YouTube video, transcribes the audio, summarizes it in Japanese, and emails the result via Resend.

## Features

- Fetches the latest video from the Pivot Talk YouTube channel (@pivot00)
- Downloads audio and transcribes it to Japanese using a local Whisper model
- Summarizes the transcript in Japanese using Qwen Coding Plan API
- Sends the video link, summary, and full transcript via email using Resend
- Skips processing if no new video has been uploaded since the last run

## Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
QWEN_CODING_API_KEY=sk-xxx
QWEN_CODING_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
RESEND_API_KEY=re_xxx
EMAIL_FROM=you@yourdomain.com
EMAIL_TO=you@example.com
YT_COOKIES_FILE=./cookies.txt  # Optional: path to YouTube cookies.txt
```

## Setup — Windows

`main.py` runs natively on Windows. No shell wrapper scripts are needed.

### Prerequisites

- Python 3.10+
- [Anaconda](https://www.anaconda.com/) (recommended for managing envs)
- FFmpeg — install via [winget](https://winget.run/pkg/Gyan/FFmpeg) or download from https://ffmpeg.org/download.html, then add the `bin/` folder to your PATH
- Node.js — install from https://nodejs.org/; required by yt-dlp for YouTube JS challenge solving

### Install dependencies

For best GPU-accelerated Whisper performance, install PyTorch with CUDA **before** the other packages:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Then install the project dependencies:

```bash
pip install "yt-dlp[default]" openai-whisper resend openai python-dotenv
```

Or with uv:

```bash
uv sync
```

### YouTube cookies (optional but recommended)

Install the **"Get cookies.txt LOCALLY"** Chrome extension, log into YouTube, then export `cookies.txt` and place it in the project directory. Set `YT_COOKIES_FILE=./cookies.txt` in your `.env`. Cookies expire after weeks to months and will need periodic re-export.

### Run

```bash
conda activate localdb
cd E:\daily_digest
python main.py
```

### Force reprocess (skip dedup)

Pass `--force` to reprocess the latest video even if it was already processed. Useful for testing:

```bash
python main.py --force
```

---

## Setup — Linux / macOS

### Prerequisites

- Python 3.10+
- FFmpeg:
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
- Node.js:
  - macOS: `brew install node`
  - Ubuntu/Debian: `sudo apt install nodejs`
- [uv](https://github.com/astral-sh/uv) package manager (recommended):
  ```bash
  pip install uv
  ```

### Install dependencies

```bash
uv sync
```

Or with pip:

```bash
pip install "yt-dlp[default]" openai-whisper resend openai python-dotenv
```

### YouTube cookies (optional but recommended)

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt <any-youtube-url>
```

Or use the **"Get cookies.txt LOCALLY"** Chrome extension. Place the resulting `cookies.txt` in the project directory and set `YT_COOKIES_FILE=./cookies.txt` in `.env`.

### Run

```bash
python main.py
```

### Force reprocess (skip dedup)

```bash
python main.py --force
```

---

## Automation with cron (Linux)

`run_on_linux.sh` is a production cron wrapper that:
- Runs `main.py` via `uv run`
- Prepends ISO 8601 timestamps to every output line
- Appends all output to `logs/cron.log`
- Preserves the script's exit code so cron can detect failures

To schedule it:

1. Make the script executable:
   ```bash
   chmod +x run_on_linux.sh
   ```

2. Open your crontab:
   ```bash
   crontab -e
   ```

3. Add an entry (adjust the path):
   ```
   0 9 * * * /path/to/daily_digest/run_on_linux.sh
   ```

**Logs:**
- `logs/daily_digest.log` — application log (rotating, 5 MB per file, 3 backups)
- `logs/cron.log` — cron wrapper log with timestamps (append-only)

The script exits with code 0 when no new video is found, so cron won't report false failures.

---

## How It Works

1. **Fetch Video** — gets the latest video from https://www.youtube.com/@pivot00
2. **Download Audio** — extracts audio in M4A format at 16 kHz using yt-dlp
3. **Transcribe** — converts audio to Japanese text using a local Whisper turbo model
4. **Summarize** — generates a Japanese summary using Qwen Coding Plan API
5. **Email** — sends the video link, summary, and full transcript via Resend

The first run downloads the Whisper turbo model (~1.5 GB); subsequent runs use the cached model.

---

## Error Handling

- If any stage fails, the script stops with an error message and exits with code 1
- The video ID is only saved after a successful email send, so a failed run will retry the same video next time
- Temporary audio files are always cleaned up, even on error

---

## Dependencies

- `yt-dlp` — YouTube audio downloading
- `openai-whisper` — local speech-to-text
- `openai` — Qwen API client (OpenAI-compatible)
- `resend` — email delivery
- `python-dotenv` — `.env` file loading
- `ffmpeg` — audio processing (system dependency, not a Python package)
