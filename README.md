# Shadow

> A Japanese language shadowing practice tool. Paste a YouTube URL, get an interactive paragraph-by-paragraph interface with real-time pronunciation feedback.

Also includes a legacy email digest mode for automated daily summaries.

---

## Quick Start

### Docker (Recommended)

See [DOCKER_GUIDE.md](DOCKER_GUIDE.md) for a full walkthrough.

```
docker compose up --build          # build & start
# open http://localhost:8000
```

### Native

**Prerequisites** — Python 3.11+, FFmpeg, Node.js

```
# GPU-accelerated Whisper (optional but recommended)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# install dependencies
uv sync

# start the server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

---

## What You Can Do

| Feature | Description |
|---|---|
| **Any YouTube URL** | Paste any video link — not limited to one channel |
| **Auto transcription** | Local Whisper model transcribes audio to Japanese text |
| **Smart chunking** | ~120-word paragraphs split at sentence boundaries (not arbitrary character counts) |
| **Native audio per paragraph** | Listen to each segment with the original speaker's voice |
| **Record your voice** | Shadow directly in the browser via microphone |
| **Word-by-word feedback** | See exactly what you got right, wrong, or missed — with an accuracy score |
| **Keyboard shortcuts** | Hands-free practice: Space, R, arrow keys |
| **Auto-save progress** | Close the tab, reopen it — you're right where you left off |

---

## How to Use the App

**1.** Open `http://localhost:8000`

**2.** Paste a YouTube URL → click **Load**

**3.** Wait for processing (download → transcribe → chunk → slice audio)

**4.** Practice paragraph by paragraph:

| Step | Action | Shortcut |
|---|---|---|
| Listen | Play the native audio | `Space` |
| Record | Shadow with your microphone | `R` |
| Review | See word-by-word diff feedback | — |
| Navigate | Move to prev/next paragraph | `←` / `→` |
| Close | Dismiss feedback panel | `Esc` |

---

## Legacy Email Digest

The original CLI workflow is preserved for cron automation. It fetches the latest Pivot Talk video, transcribes, summarizes, and emails the result.

```
python -m src.cli              # normal run (skips if no new video)
python -m src.cli --force      # reprocess latest video
daily-digest                   # same, via entry point
daily-digest --force
```

---

## How It Works

### Shadowing Flow

```
YouTube URL → yt-dlp downloads audio
            → Whisper transcribes (with word timestamps)
            → Qwen chunks into ~120-word paragraphs
            → ffmpeg slices audio per paragraph
            → Browser plays native audio + records your voice
            → Whisper transcribes your recording
            → Qwen generates word-by-word diff
```

### Email Digest Flow (Legacy)

```
Pivot Talk channel → yt-dlp downloads latest video
                   → Whisper transcribes
                   → Qwen summarizes in Japanese
                   → Resend sends email with link + summary + transcript
```

---

## Setup Details

### Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```env
QWEN_CODING_API_KEY=sk-xxx
QWEN_CODING_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
RESEND_API_KEY=re_xxx
EMAIL_FROM=you@yourdomain.com
EMAIL_TO=you@example.com
YT_COOKIES_FILE=./cookies.txt
```

### YouTube Cookies (Optional but Recommended)

Install the **"Get cookies.txt LOCALLY"** Chrome extension → log into YouTube → export `cookies.txt` → place it in the project directory → set `YT_COOKIES_FILE=./cookies.txt` in `.env`.

Cookies expire after weeks to months and will need periodic re-export.

---

## Project Structure

```
daily_digest/
├── src/                    Backend modules
│   ├── fetcher.py          yt-dlp: video fetching & audio download
│   ├── transcriber.py      Whisper: transcription with word timestamps
│   ├── chunker.py          Qwen: semantic paragraph chunking
│   ├── comparator.py       Qwen: word-by-word diff comparison
│   ├── audio_slicer.py     ffmpeg: per-paragraph audio extraction
│   ├── summarizer.py       Qwen: summarization (legacy)
│   ├── mailer.py           Resend: email sending (legacy)
│   └── cli.py              Legacy CLI entry point
│
├── app/                    Web application
│   ├── main.py             FastAPI server + Whisper preload
│   ├── state.py            Shared state (avoids circular imports)
│   ├── routes/
│   │   ├── videos.py       Video loading & status endpoints
│   │   ├── practice.py     Recording comparison endpoint
│   │   └── audio.py        Audio segment serving
│   └── static/
│       ├── index.html      Single-page app
│       ├── style.css       Dark minimalistic stylesheet
│       └── app.js          Frontend logic + keyboard shortcuts
│
├── Dockerfile              Container definition
├── docker-compose.yml      Multi-container orchestration
├── DOCKER_GUIDE.md         Docker setup guide (Windows/Mac/Linux)
├── LICENSE                 MIT License
├── run.ps1 / run.sh        Launcher scripts
├── pyproject.toml          Dependencies & project metadata
└── main.py                 Backward-compatible wrapper → src.cli
```

---

## Dependencies

### Python Packages

| Package | Purpose |
|---|---|
| `yt-dlp` | YouTube audio downloading |
| `openai-whisper` | Local speech-to-text |
| `openai` | Qwen API client (OpenAI-compatible) |
| `resend` | Email delivery (legacy) |
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload handling |
| `python-dotenv` | `.env` file loading |

### System Dependencies

| Tool | Purpose |
|---|---|
| `ffmpeg` | Audio processing & segment extraction |
| `nodejs` | Required by yt-dlp for YouTube JS challenge solving |

---

## Error Handling

- Processing errors are shown directly in the UI
- Temporary audio files are always cleaned up, even on failure
- Whisper model is preloaded on server startup — no cold-start delay on first recording
- Session state persists to localStorage for tab-close recovery
