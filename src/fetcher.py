"""Video fetching and audio downloading via yt-dlp."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yt_dlp

LAST_VIDEO_ID_FILE = Path(__file__).parent.parent / ".last_video_id"

FFMPEG_BIN = r'C:\Users\kevin2\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin'


def get_cookie_opts():
    """Get yt-dlp cookie options based on YT_COOKIES_FILE env var."""
    cookies_file = os.getenv('YT_COOKIES_FILE')
    if cookies_file and os.path.isfile(cookies_file):
        return {'cookiefile': cookies_file}
    return {}


def get_last_video_id():
    """Read the last processed video ID from file."""
    if LAST_VIDEO_ID_FILE.exists():
        return LAST_VIDEO_ID_FILE.read_text().strip()
    return None


def save_last_video_id(video_id):
    """Save the processed video ID to file."""
    LAST_VIDEO_ID_FILE.write_text(video_id)


def get_channel_latest_video(channel_url):
    """Fetch the latest video from a YouTube channel."""
    logging.info(f"Fetching latest video from {channel_url}...")

    ydl_opts = {
        'extract_flat': True,
        'playlistend': 1,
        'quiet': True,
        'extractor_args': {'youtube': {'skip': ['hls', 'dash']}},
        'js_runtimes': {'node': {'path': 'C:/Program Files/nodejs/node.exe'}},
    }
    ydl_opts.update(get_cookie_opts())

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)

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


def get_video_info(video_url):
    """Fetch metadata for a specific YouTube video URL."""
    logging.info(f"Fetching video info for {video_url}...")

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'extractor_args': {'youtube': {'skip': ['hls', 'dash']}},
        'js_runtimes': {'node': {'path': 'C:/Program Files/nodejs/node.exe'}},
    }
    ydl_opts.update(get_cookie_opts())

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            video_id = info.get('id')
            if not video_id:
                logging.error("Could not extract video ID")
                sys.exit(1)

            video_info = {
                'title': info.get('title'),
                'id': video_id,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'upload_date': info.get('upload_date')
            }

            if video_info['upload_date']:
                dt = datetime.strptime(video_info['upload_date'], '%Y%m%d')
                video_info['formatted_date'] = dt.strftime('%Y-%m-%d')
            else:
                video_info['formatted_date'] = 'Unknown'

            logging.info(f"Found video: {video_info['title']}")
            return video_info

    except Exception as e:
        logging.exception(f"Error fetching video info: {str(e)}")
        sys.exit(1)


def download_audio(video_url, output_dir=None):
    """Download audio from the video URL using yt-dlp. Returns path to downloaded file."""
    import tempfile

    logging.info("Downloading audio...")

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        outtmpl = str(Path(output_dir) / "%(id)s.%(ext)s")
    else:
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_audio:
            outtmpl = temp_audio.name.replace('.m4a', '')

    temp_path = None

    try:
        ydl_opts = {
            'format': 'bestaudio*',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'postprocessor_args': ['-ar', '16000'],
            'prefer_ffmpeg': True,
            'audioquality': '0',
            'extractaudio': True,
            'audioformat': 'm4a',
            'outtmpl': outtmpl,
            'quiet': True,
            'js_runtimes': {'node': {'path': 'C:/Program Files/nodejs/node.exe'}},
            'ffmpeg_location': FFMPEG_BIN,
        }
        ydl_opts.update(get_cookie_opts())

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Find the downloaded file
        if output_dir:
            base = str(Path(output_dir) / ydl_opts.get('outtmpl', '').split('%')[0])
            for ext in ['.m4a', '.mp3']:
                candidate = base + ext
                if os.path.exists(candidate):
                    temp_path = candidate
                    break
        else:
            for ext in ['.m4a', '.mp3', '.m4a.mp3']:
                candidate = outtmpl + ext
                if os.path.exists(candidate):
                    temp_path = candidate
                    break

        if not temp_path or not os.path.exists(temp_path):
            logging.error("Failed to download audio")
            sys.exit(1)

        logging.info(f"Audio downloaded to: {temp_path}")
        return temp_path

    except Exception as e:
        logging.exception(f"Error downloading audio: {str(e)}")
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        sys.exit(1)
