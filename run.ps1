@echo off
echo Starting Shadow...
echo.

:: Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found. Copy .env.example to .env and fill in your API keys.
    echo.
    pause
    exit /b 1
)

:: Start the server and open browser
start http://localhost:8000
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
