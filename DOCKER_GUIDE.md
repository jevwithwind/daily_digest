# Docker & Project Guide

This is your personal reference for Docker setup, the Kageyomi project, and how to manage it across machines.

---

## Part 1: What is Docker and Why You Need It

### What Docker Is

Docker packages an application and **all its dependencies** into a **container** — a self-contained, portable unit that runs identically on any machine. Think of it as a pre-configured virtual environment that includes the OS-level tools (Python, FFmpeg, Node.js), your code, and the exact versions of every library.

### What Docker Is Good At

| Strength | Explanation |
|---|---|
| **Reproducibility** | Same container runs on your Windows PC, MacBook, and remote Linux server — zero differences |
| **Dependency isolation** | No more "it works on my machine" — FFmpeg version, Python version, library versions are all locked |
| **One-command setup** | `docker compose up` replaces installing 5+ system packages and managing virtual environments |
| **Clean teardown** | `docker compose down` removes everything. No leftover packages cluttering your system |
| **Volume persistence** | Heavy downloads (Whisper model ~1.5GB) survive container rebuilds via named volumes |

### Why This Project Needs Docker

Shadow depends on:
- Python 3.11+ with CUDA-capable PyTorch (optional but recommended)
- FFmpeg (system binary, not a Python package)
- Node.js (required by yt-dlp for YouTube's JS challenge)
- openai-whisper (downloads a ~1.5GB model on first run)
- fastapi + uvicorn (web server)
- Plus: yt-dlp, openai, resend, python-dotenv, python-multipart

Without Docker, you'd need to manually install and version-match all of these on **every machine** you use. With Docker, the `Dockerfile` defines the exact environment once, and `docker compose up` reproduces it everywhere.

**Note:** Docker is completely isolated from your local Python setup. If you use conda environments (e.g. `localdb`) for development, Docker does not interact with them in any way. Your conda environments remain untouched and fully usable alongside Docker.

---

## Part 2: What Changed in This Session

### Before (v0.1.0 — Email Digest CLI)

- Single-file `main.py` (387 lines) — hardcoded to Pivot Talk YouTube channel
- Linear pipeline: fetch → download → transcribe → summarize → email via Resend
- Naive transcript chunking at ~500 chars near punctuation (often broke mid-sentence)
- No interactive UI — purely batch/cron operation
- No way to practice shadowing

### After (v0.2.0 — Shadow Web App + Legacy CLI)

**New architecture:**
- `src/` — 8 modular backend files extracted from the monolith
- `app/` — FastAPI web server with Whisper model preloading
- `app/static/` — Single-page web app (HTML/CSS/JS, zero frameworks)

**New features:**
- **Any YouTube URL** input (not hardcoded to one channel)
- **Semantic chunking** — LLM breaks transcript into ~120-word sentence-complete paragraphs
- **Per-paragraph audio slicing** — ffmpeg extracts native audio segments using Whisper word timestamps
- **Browser microphone recording** — MediaRecorder API captures your voice
- **Word-by-word diff feedback** — LLM compares your speech against reference, returns color-coded inline diff with accuracy score
- **Keyboard shortcuts** — Space (listen), R (record), arrows (navigate), Esc (close feedback)
- **Session persistence** — localStorage remembers your last video and position
- **Dark minimalistic UI** — GitHub-dark color palette, no JS frameworks

**Preserved:**
- **Legacy email digest** — `src/cli.py` (or `python main.py`) works identically to before, including `--force` flag and cron compatibility
- All existing environment variables and cookie handling
- Whisper turbo model, Qwen API, Resend email — same services, same keys

**Files added:**
```
src/__init__.py, src/fetcher.py, src/transcriber.py, src/chunker.py,
src/comparator.py, src/audio_slicer.py, src/summarizer.py, src/mailer.py, src/cli.py
app/__init__.py, app/state.py, app/main.py
app/routes/videos.py, app/routes/practice.py, app/routes/audio.py
app/static/index.html, app/static/style.css, app/static/app.js
Dockerfile, Dockerfile.lean, docker-compose.yml, DOCKER_GUIDE.md
run.ps1, run.sh
```

**Files modified:**
```
main.py → now a thin wrapper that delegates to src.cli
pyproject.toml → added fastapi, uvicorn, python-multipart; updated entry point
README.md → full rewrite covering both shadowing and legacy modes
```

---

## Part 3: Docker Setup on All Your Machines

### Windows (Primary Machine)

#### Install Docker Desktop

1. Go to https://www.docker.com/products/docker-desktop/
2. Download **Docker Desktop for Windows**
3. Run the installer:
   - Leave default options (WSL 2 backend is recommended)
   - If prompted, enable WSL 2 — Docker will guide you through this
4. **Restart your computer** if prompted
5. Open **Docker Desktop** from the Start menu and wait for it to start (whale icon in system tray stops animating)

#### Verify

```powershell
docker --version
docker compose version
```

You should see `Docker version 27.x.x` and `Docker Compose version v2.x.x`.

#### Run Shadow

```powershell
# From E:\daily_digest
docker compose up --build
```

Open http://localhost:8000

---

### macOS (MacBook)

#### Install Docker Desktop

1. Go to https://www.docker.com/products/docker-desktop/
2. Download **Docker Desktop for Mac** (choose your chip: Intel or Apple Silicon)
3. Open the `.dmg` file and drag Docker to Applications
4. Open Docker from Applications. It will ask for your password to install helper tools — allow it
5. Wait for the whale icon in the menu bar to stop animating

#### Verify

```bash
docker --version
docker compose version
```

#### Run Shadow

```bash
# Clone or copy the project to your Mac
cd /path/to/daily_digest

# Create .env if you haven't
cp .env.example .env
# Edit .env with your API keys

docker compose up --build
```

Open http://localhost:8000

**Apple Silicon (M1/M2/M3) note:** The Docker image uses `python:3.11-slim` which has native ARM64 builds. FFmpeg and all dependencies install natively. No Rosetta emulation needed — it runs at native speed.

---

### Remote Linux Workstation

#### Install Docker Engine (no GUI)

On Ubuntu/Debian:

```bash
# Remove conflicting packages if any
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
    sudo apt-get remove -y $pkg
done

# Install prerequisites
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key and repo
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group (no sudo needed)
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

#### Verify

```bash
docker --version
docker compose version
```

#### Run Shadow

```bash
cd /path/to/daily_digest

cp .env.example .env
# Edit .env with your API keys

docker compose up --build
```

#### Access from Your Local Machine

If the Linux box is remote, you need to access the web UI from your local browser. Two options:

**Option A: SSH port forwarding** (recommended for personal use):
```bash
# From your local machine (Windows/Mac)
ssh -L 8000:localhost:8000 user@your-linux-server

# Then open http://localhost:8000 in your local browser
```

**Option B: Expose the port** (if the server has a public/private IP you can reach):
```yaml
# In docker-compose.yml, the ports mapping already exposes it:
ports:
  - "8000:8000"
```
Then open `http://<server-ip>:8000` from your local browser.

#### Run as a Background Service (Optional)

For a persistent shadowing server on the Linux box:

```bash
docker compose up -d
```

To auto-start on boot:

```bash
# Create a systemd service
sudo tee /etc/systemd/system/shadow.service > /dev/null << 'EOF'
[Unit]
Description=Shadow Language Practice Tool
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/daily_digest
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable shadow
sudo systemctl start shadow
```

---

## Part 4: Common Docker Commands (All Platforms)

| Command | What it does |
|---|---|
| `docker compose up --build` | Build image and start containers |
| `docker compose up -d` | Start in background (detached) |
| `docker compose down` | Stop and remove containers |
| `docker compose logs -f` | Follow live logs |
| `docker compose ps` | Show running containers |
| `docker compose exec shadow bash` | Open a shell inside the container |
| `docker compose exec shadow python -m src.cli` | Run legacy email digest |
| `docker compose down --rmi all --volumes` | Nuclear option: remove everything |

---

## Part 5: How Docker Volumes Work Here

The `docker-compose.yml` mounts these volumes:

| Volume | Purpose |
|---|---|
| `whisper-cache` | Named volume. Persists the Whisper model (~1.5GB) across rebuilds |
| `./logs:/app/logs` | Bind mount. Saves server logs to your local `logs/` folder |
| `./.env:/app/.env:ro` | Bind mount (read-only). Passes your `.env` into the container |
| `./cookies.txt:/app/cookies.txt:ro` | Bind mount (read-only). Passes YouTube cookies into the container |

**Key concept:** Named volumes (`whisper-cache`) are managed by Docker and survive `docker compose down`. Bind mounts (`./logs`) map directly to your local filesystem.

---

## Part 6: GitHub — What to Push and What to Ignore

### Branch Strategy

**Use `main` branch.** This is a personal project with a single contributor. No need for feature branches unless you start collaborating. The old email digest code is preserved in `src/cli.py`, so there's nothing to lose by pushing the new code to `main`.

### What to Push

| File/Directory | Push? | Reason |
|---|---|---|
| `src/` | Yes | All backend modules |
| `app/` | Yes | All web app code + static files |
| `main.py` | Yes | Thin wrapper for backward compatibility |
| `pyproject.toml` | Yes | Dependency definitions |
| `Dockerfile` / `docker-compose.yml` | Yes | Container definitions |
| `DOCKER_GUIDE.md` / `README.md` | Yes | Documentation |
| `run.ps1` / `run.sh` | Yes | Launcher scripts |
| `.gitignore` | Yes | Ignore rules |
| `.env.example` | Yes | Template for others (or your future self) |

### What to Keep in `.gitignore` (Never Push)

| File/Pattern | Reason |
|---|---|
| `.env` | Contains API keys — **never commit** |
| `cookies.txt` | Contains your YouTube session cookies — security risk |
| `.last_video_id` | Local state, machine-specific |
| `logs/` | Runtime logs, regenerated on every run |
| `__pycache__/` | Python bytecode, platform-specific |
| `*.pyc` | Same |
| `venv/` / `env/` | Virtual environments, reproducible via `pyproject.toml` |
| `.vscode/` / `.idea/` | IDE settings, personal preference |
| `*.egg-info/` | Build artifacts |
| `uv.lock` | **Debatable** — lock files ensure reproducible installs. For a personal project, you can commit it. For a multi-platform project (Windows + Mac + Linux), the lock file may have platform-specific entries. **Recommendation: add it to `.gitignore`** since Docker handles reproducibility. |

### Current `.gitignore` — Review

Your existing `.gitignore` covers all the essentials. The only addition to consider:

```
# Add these if not already present:
uv.lock
*.m4a
*.mp3
*.webm
```

The audio file patterns prevent accidentally committing temporary audio files if they ever end up in the repo directory.

### Recommended First Commit

```bash
git add -A
git status          # review what will be committed
git commit -m "Refactor to Shadow web app with semantic chunking and interactive shadowing

- Extract monolithic main.py into modular src/ package
- Add FastAPI web server with Whisper model preloading
- Implement LLM-based semantic transcript chunking (~120 words)
- Add per-paragraph audio slicing via ffmpeg + Whisper timestamps
- Build dark minimalistic single-page web app
- Add word-by-word diff feedback via LLM comparison
- Preserve legacy email digest in src/cli.py
- Add Docker support with multi-platform setup guide"
git push origin main
```

---

## Part 7: Troubleshooting

### "Docker Desktop is not running"
- Open Docker Desktop and wait for the whale icon to stop animating
- On Mac: check the menu bar whale icon
- On Linux: `sudo systemctl status docker`

### "Port 8000 is already in use"
Change the port in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"
```
Then access at `http://localhost:8001`

### "Build failed" or "Package installation error"
```bash
docker compose down --rmi all
docker compose up --build
```

### "Whisper model download takes forever"
First run downloads ~1.5GB. It's cached in the `whisper-cache` volume and won't re-download. Just wait.

### "Microphone doesn't work"
Recording happens in your **browser**, not in Docker. Make sure your browser has microphone permissions for `http://localhost:8000`.

### "yt-dlp fails to download video"
- Cookies may have expired. Re-export `cookies.txt`
- Or try without cookies (some videos work without them)

### "Container uses too much disk space"
```bash
# Clean up unused Docker resources
docker system prune -a --volumes
# Then rebuild
docker compose up --build
```

---

## Part 8: Docker vs. Native

| Aspect | Docker | Native |
|---|---|---|
| Setup | One command | Install Python, FFmpeg, Node.js, manage env |
| Portability | Identical on Windows/Mac/Linux | Depends on each system |
| Disk usage | ~2GB (image + model cache) | ~3-4GB (Python + deps + model) |
| Code changes | Requires `--build` | Immediate (just restart server) |
| Development | Slightly slower iteration | Faster iteration |
| Multi-machine sync | `git clone` + `docker compose up` | Re-install everything on each machine |

**Recommendation:** Use Docker for regular use across all three machines. Use native setup only for active development on your primary Windows machine.

---

## Part 9: Quick Reference

### Starting Shadow

| Machine | Command |
|---|---|
| Windows | `docker compose up --build` (or `.\run.ps1` for native) |
| Mac | `docker compose up --build` (or `./run.sh` for native) |
| Linux | `docker compose up --build` (or `./run.sh` for native) |

### URLs

| Service | URL |
|---|---|
| Shadow web app | http://localhost:8000 |
| API health check | http://localhost:8000/api/health |
| API docs (auto-generated) | http://localhost:8000/docs |

### Keyboard Shortcuts (In the App)

| Key | Action |
|---|---|
| `Space` | Play/Pause native audio |
| `R` | Start/Stop recording |
| `←` | Previous paragraph |
| `→` | Next paragraph |
| `Esc` | Close feedback panel |

### Legacy Email Digest

```bash
# Docker
docker compose exec shadow python -m src.cli
docker compose exec shadow python -m src.cli --force

# Native
python main.py
python main.py --force
```
