FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        nodejs \
        npm \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir uv && \
    uv pip install --system \
        yt-dlp \
        openai \
        resend \
        python-dotenv \
        openai-whisper \
        fastapi \
        "uvicorn[standard]" \
        python-multipart

COPY . .

RUN mkdir -p /root/.cache/whisper

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
