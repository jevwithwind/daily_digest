#!/usr/bin/env bash
set -euo pipefail

echo "Starting Shadow..."
echo ""

if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and fill in your API keys."
    exit 1
fi

# Open browser in background
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000 &
elif command -v open &> /dev/null; then
    open http://localhost:8000 &
fi

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
